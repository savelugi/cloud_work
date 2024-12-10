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

population = initial_population(network.players, network.core_servers, population_size)

generations = 1500
fitness_per_generation = []
counter = 0
for iter in range(int(generations)):
    fitness_values = [fitness_sum(
                        network,
                        tuple(chromosome),
                        max_core_server_nr=MAX_CORE_SERVERS,
                        max_edge_server_nr=MAX_EDGE_SERVERS,
                        max_connected_players=MAX_PLAYERS_ON_SERVER,
                        min_connected_players=MIN_PLAYERS_ON_SERVER,
                        generation=generations,
                        iteration=iter)
                        for chromosome in population]            

    sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])  
    best_solution = sorted_pop[0]
    best_fitness = fitness_values[population.index(best_solution)]
    fitness_per_generation.append(best_fitness)

    selection_strategy = 'rank_based'
    tournament_size = '10'
    parents = selection(population, fitness_values, selection_strategy, tournament_size)
    offspring = []
    while len(offspring) < population_size - len(parents):
        parent1, parent2 = default_random.sample(parents, 2)
        crossover_method = 'single_point'
        child1, child2 = crossover(parent1, parent2, method=crossover_method)
        mutation_rate = 0.001

        # child1 = mutate_random_edges(network, child1, mutation_rate, max_edge_servers=MAX_EDGE_SERVERS, initial=False)
        # child2 = mutate_random_edges(network, child2, mutation_rate, max_edge_servers=MAX_EDGE_SERVERS, initial=False)
        child1 = mutate_players(network, child1, mutation_rate, network._only_servers)
        child2 = mutate_players(network, child2, mutation_rate, network._only_servers)
        #child1 = mutate_servers(network, child1, mutation_rate)
        #child2 = mutate_servers(network, child2, mutation_rate)

        #if iter % (iter+1)/2 == 0 or iter == generations:
        #child1 = enforce_max_server_occurrences(network, child1, MAX_CORE_SERVERS, MAX_EDGE_SERVERS)
        #child2 = enforce_max_server_occurrences(network, child1, MAX_CORE_SERVERS, MAX_EDGE_SERVERS)

        #child1 = enforce_min_max_players_per_server(network, child1, MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER)
        #child2 = enforce_min_max_players_per_server(network, child1, MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER)

        offspring.extend([child1, child2])

    population = parents + offspring
    counter += 1

    if counter % 100 == 0:
        logger.log(f'Best fitness at {iter}: {best_fitness}', print_to_console=True)

sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])
last_pop = sorted_pop.copy()
best_solution = sorted_pop[0]

logger.log('Genetic algorithm has found a solution with a fitness of ' + str(best_fitness), print_to_console=True)

# Plot fitness improvement over generations
# plt.figure(figsize=(10, 6))
# plt.plot(range(1, len(fitness_per_generation) + 1), fitness_per_generation, marker='o', linestyle='-')
# plt.title("Fitness Improvement Over Generations", fontsize=16)
# plt.xlabel("Generation", fontsize=14)
# plt.ylabel("Best Fitness Value", fontsize=14)
# plt.grid()
# plt.tight_layout()
# plt.show()

network.set_player_server_metrics(best_solution)
network.calculate_delays("Genetic algorithm", debug_prints=True)
network.calculate_QoE_metrics()

network.color_graph()     
network.draw_graph(title=f"{len(network.players)}_{len(network.selected_core_servers)}_{len(network.selected_edge_servers)}", save=True, save_dir=save_path)