import os
from utils import *
from network_graph import *
from visualization import *
from gurobi import *
from datetime import datetime
from mutation import *
import globvars
from globvars import logger
import math
import matplotlib.pyplot as plt

dir_path = os.path.dirname(os.path.realpath(__file__))
save_dir = os.path.join(dir_path, "saves/dynamic/")
config_file = os.path.join(dir_path, "config.ini")
config = read_configuration(config_file)

timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Get current timestamp
topology = config['Topology']['topology']
save_path = save_dir + timestamp + '_' + topology
if not os.path.exists(save_path):
    os.makedirs(save_path)

csv_path = save_path + '/' + timestamp + '_' + topology + '.csv'
log_path = save_path + '/' + "log.txt"
logger.set_log_file(log_path)

debug_prints = True

INITIAL_PLAYER_NUMBER = 16
NR_OF_GAME_SERVERS = 7
MIN_PLAYERS_ON_SERVER = 2
MAX_PLAYERS_ON_SERVER = 4
MAX_ALLOWED_DELAY = 20
MAX_EDGE_SERVERS = 1
MAX_CORE_SERVERS = 2
MIGRATION_COST = 0

ADDING_PLAYERS = False
REMOVING_PLAYERS = False
MOVING_PLAYERS = True
GEN_OPT = True
GUROBI_OPT = False

network = NetworkGraph(modelname='ilp_sum', config=config, num_gen_players=INITIAL_PLAYER_NUMBER)

population_size = 250
last_pop = []

# -------------------- ÚJ FÜGGVÉNYEK KEZDETE -------------------- #

def constraints_are_met(chromosome, network, max_core_server_nr, max_edge_server_nr, max_connected_players, min_connected_players):
    # Ellenőrizzük a szerverek számát
    selected_core_servers = [srv for srv in set(chromosome) if srv != -1 and srv is not None and network.is_core_server(srv)]
    selected_edge_servers = [srv for srv in set(chromosome) if srv != -1 and srv is not None and network.is_edge_server(srv)]

    if len(selected_core_servers) > max_core_server_nr:
        return False
    if len(selected_edge_servers) > max_edge_server_nr:
        return False

    # Ellenőrizzük a játékosok számát szerverenként
    player_count_on_servers = {server:0 for server in network._only_servers}
    for srv in chromosome:
        if srv != -1 and srv is not None:
            player_count_on_servers[srv] += 1

    for srv, player_count in player_count_on_servers.items():
        if network.is_core_server(srv):
            max_player_nr = 2 * max_connected_players
        else:
            max_player_nr = max_connected_players

        if player_count > max_player_nr:
            return False
        if player_count < min_connected_players and player_count > 0:
            return False

    return True

def fitness_sum_with_penalties(network: NetworkGraph, chromosome, max_core_server_nr, max_edge_server_nr, max_connected_players, min_connected_players, generation, iteration, 
                               penalty_core_factor=1.0, penalty_edge_factor=1.0, penalty_players_factor=1.0, prev_chromosome=None):

    sum_delays = 0
    migration_cost = 0
    penalty = 0

    for player_index, server in enumerate(chromosome):
        if server != -1:
            if server is not None:
                sum_delays += network.get_shortest_path_delay(f"P{player_index+1}", server)
                if prev_chromosome:
                    migration_cost += network.calculate_migration_cost(prev_chromosome[player_index], server)
            else:
                # Large penalty for players not assigned
                sum_delays += 1000

    total_fitness = (sum_delays + migration_cost) / len(network.players)

    # Count selected servers
    selected_core_servers = []
    selected_edge_servers = []
    for srv in set(chromosome):
        if srv != -1 and srv is not None:
            if network.is_core_server(srv):
                selected_core_servers.append(srv)
            elif network.is_edge_server(srv):
                selected_edge_servers.append(srv)

    # Core/Edge servers penalty
    if len(selected_core_servers) > max_core_server_nr:
        penalty += (total_fitness * penalty_core_factor * (len(selected_core_servers) - max_core_server_nr))
    if len(selected_edge_servers) > max_edge_server_nr:
        penalty += (total_fitness * penalty_edge_factor * (len(selected_edge_servers) - max_edge_server_nr)) 

    # Player count per server penalty
    player_count_on_servers = {server: 0 for server in network._only_servers}
    for srv in chromosome:
        if srv != -1 and srv:
            player_count_on_servers[srv] += 1

    for srv, player_count in player_count_on_servers.items():
        if network.is_core_server(srv):
            max_player_nr = 2 * max_connected_players
        else:
            max_player_nr = max_connected_players

        if player_count > int(max_player_nr):
            penalty += (player_count - max_player_nr) * total_fitness * penalty_players_factor
        if player_count < min_connected_players and player_count > 0:
            penalty += (min_connected_players - player_count) * total_fitness * penalty_players_factor

    scale = iteration / generation
    fitness_value = (penalty * scale) + total_fitness
    return fitness_value

def simulate_penalties(network, population, max_core_server_nr, max_edge_server_nr, max_connected_players, min_connected_players, generations, iteration):
    penalty_factors = [0.5, 1.0, 2.0]  # Lehet szűkíteni a keresést
    results = {}

    for p_core in penalty_factors:
        for p_edge in penalty_factors:
            for p_players in penalty_factors:
                fitness_vals = [
                    fitness_sum_with_penalties(
                        network,
                        tuple(chrom),
                        max_core_server_nr,
                        max_edge_server_nr,
                        max_connected_players,
                        min_connected_players,
                        generation=generations,
                        iteration=iteration,
                        penalty_core_factor=p_core,
                        penalty_edge_factor=p_edge,
                        penalty_players_factor=p_players
                    )
                    for chrom in population
                ]

                # Számoljuk, hány megoldás felel meg a korlátoknak
                feasible_count = sum(
                    1 for chrom in population if constraints_are_met(chrom, network, max_core_server_nr, max_edge_server_nr, max_connected_players, min_connected_players)
                )
                feasibility_ratio = feasible_count / len(population)
                results[(p_core, p_edge, p_players)] = feasibility_ratio

    # Kiválasztjuk a legjobb faktorkombinációt
    best = max(results, key=results.get)
    print("Best penalty factors:", best, "Feasibility:", results[best])
    return best

# -------------------- ÚJ FÜGGVÉNYEK VÉGE -------------------- #

population = initial_population(network.players, network.core_servers, population_size)

generations = 1500
fitness_per_generation = []
counter = 0

# Kezdetben alapértelmezett büntetési tényezők
penalty_core_factor = [0.001, 0.01, 0.1, 1]
penalty_edge_factor = [0.001, 0.01, 0.1, 1]
penalty_players_factor = [0.001, 0.01, 0.1, 1]

for p_core in penalty_core_factor:
        for p_edge in penalty_edge_factor:
            for p_players in penalty_players_factor:

                for iter in range(int(generations)):
                    fitness_values = [
                    fitness_sum_with_penalties(
                        network,
                        tuple(chromosome),
                        max_core_server_nr=MAX_CORE_SERVERS,
                        max_edge_server_nr=MAX_EDGE_SERVERS,
                        max_connected_players=MAX_PLAYERS_ON_SERVER,
                        min_connected_players=MIN_PLAYERS_ON_SERVER,
                        generation=generations,
                        iteration=iter,
                        penalty_core_factor=p_core,
                        penalty_edge_factor=p_edge,
                        penalty_players_factor=p_players
                    )
                    for chromosome in population
                    ]

                    sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])  
                    best_solution = sorted_pop[0]
                    best_fitness = fitness_values[population.index(best_solution)]
                    fitness_per_generation.append(best_fitness)

                    selection_strategy = 'rank_based'
                    tournament_size = '10'
                    parents = selection(population, fitness_values, selection_strategy, tournament_size)
                    offspring = []
                    mutation_rate = 0.001
                    crossover_method = 'single_point'

                    while len(offspring) < population_size - len(parents):
                        parent1, parent2 = default_random.sample(parents, 2)
                        child1, child2 = crossover(parent1, parent2, method=crossover_method)

                        # Mutáció
                        child1 = mutate_players(network, child1, mutation_rate, network._only_servers)
                        child2 = mutate_players(network, child2, mutation_rate, network._only_servers)

                        offspring.extend([child1, child2])

                    population = parents + offspring
                    counter += 1

                    if counter % 100 == 0:
                        logger.log(f'Best fitness at {iter}: {best_fitness}', print_to_console=True)

                sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])
                last_pop = sorted_pop.copy()
                best_solution = sorted_pop[0]

                if constraints_are_met(best_solution, network, MAX_CORE_SERVERS, MAX_EDGE_SERVERS, MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER) is True:
                    print(f"Constraints are met: {p_core}, {p_edge}, {p_players}")
                    break
                else:
                    print(f"Constraints are not met at: {p_core}, {p_edge}, {p_players}")


logger.log('Genetic algorithm has found a solution with a fitness of ' + str(best_fitness), print_to_console=True)

network.set_player_server_metrics(best_solution)
network.calculate_delays("Genetic algorithm", debug_prints=True)
network.calculate_QoE_metrics()

network.color_graph()     
network.draw_graph(title=f"{len(network.players)}_{len(network.selected_core_servers)}_{len(network.selected_edge_servers)}", save=True, save_dir=save_path)