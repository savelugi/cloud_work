import networkx as nx
import random
from utils import *
from network_graph import *
from visualization import *
from gurobi import *
import numpy as np
from functools import lru_cache
from scipy.stats import sem
from globvars import logger

default_random = random.Random()
def initial_population(players, servers, population_size):
    population = []
    for _ in range(population_size):
        chromosome = [default_random.choice(servers) for _ in range(len(players))]
        population.append(chromosome)
    return population

def convert_ILP_to_chromosome(player_server_list):
    chromosome = []

    # int(x[0][1:]) is 'n' in 'Pn', i.e 12 in P12
    sorted_player_server_list = sorted(player_server_list, key=lambda x: int(x[0][1:]))

    previous_index = 0
    for player, server, _ in sorted_player_server_list:
        current_index = int(player[1:])

        while previous_index < current_index - 1:
            chromosome.append(-1)
            previous_index += 1

        chromosome.append(server)
        previous_index = current_index

    return chromosome
        
def chromosome_to_uniform_population(chromosome, population_size):
    population = []

    for _ in range(population_size):
        population.append(chromosome)

    return population

def enforce_min_max_players_per_server(network: NetworkGraph, chromosome, max_connected_players, min_connected_players, migrate_to_edge_servers=False):
    # TODO: currently only limits the max players
    player_count_on_servers = {server: 0 for server in network._only_servers}
    for server in chromosome:
        if server != -1 and server:
            player_count_on_servers[server] += 1

    for server, player_count in player_count_on_servers.items():
        if player_count > int(max_connected_players): #or player_count < int(min_connected_players):
            # Find indices of players connected to this server
            connected_players = [i for i, s in enumerate(chromosome) if s == server]

            # Sort connected players by shortest path delay
            sorted_connected_players = sorted(connected_players, key=lambda x: network.get_shortest_path_delay(f"P{x+1}", server))

            drop_connected_player_indices = sorted_connected_players[int(max_connected_players):]
            selected_servers = {srv:player_cnt for srv, player_cnt in player_count_on_servers.items() if player_cnt != 0 and srv != server}
            closest_selected_servers = sorted(selected_servers.keys(), key=lambda srv: network.get_shortest_path_delay(srv, server))

            
            #closest_servers = network.get_closest_servers(server)

            # if migrate_to_edge_servers:
            #     for srv in closest_servers:
            #         if not network.is_edge_server(srv):
            #             closest_servers.remove(srv)
            #     if not closest_servers:
            #         print(f"There are no edge servers near {server}, returning!")
            #         return

            # move the excess player to the closest selected server
            # if toggled prioritise edge servers if possible
            # if the server is already full try the next server
            iter = drop_connected_player_indices.copy()
            for idx in iter:
                for srv in closest_selected_servers:
                    if player_count_on_servers[srv] < int(max_connected_players):
                        chromosome[idx] = srv
                        player_count_on_servers[srv] += 1
                        player_count_on_servers[server] -=1
                        break
                drop_connected_player_indices.remove(idx)

            if len(drop_connected_player_indices) > 0:
                print("We shouldn't get here")

    for server, player_count in player_count_on_servers.items():
        if player_count < int(min_connected_players) and player_count > 0:

            connected_players = [i for i, s in enumerate(chromosome) if s == server]
            players_to_move = connected_players.copy()
            selected_servers = {srv:player_cnt for srv, player_cnt in player_count_on_servers.items() if player_cnt != 0 and srv != server}
            closest_selected_servers = sorted(selected_servers.keys(), key=lambda srv: network.get_shortest_path_delay(srv, server))
            for player in players_to_move:
                for closest_server in closest_selected_servers:
                    if player_count_on_servers[closest_server] + 1 >= int(min_connected_players) or player_count_on_servers[closest_server] + 1 <= int(max_connected_players):
                        chromosome[player] = closest_server
                        player_count_on_servers[server] -= 1
                        player_count_on_servers[closest_server] += 1
                        break
                players_to_move.remove(player)

    return chromosome

def enforce_max_server_occurrences(chromosome, max_server_nr):
    server_counts = {}
    for server in set(chromosome):
        if server != -1 and server:
            server_counts[server] = chromosome.count(server)

    if len(server_counts) <= int(max_server_nr):
        return chromosome

    servers = [server for server, count in server_counts.items() if count >= 1]
    default_random.shuffle(servers)

    servers_to_keep = servers[:int(max_server_nr)]

    updated_chromosome = []
    for server in chromosome:
        # player is not in the network so keep the server value (-1)
        if server == -1:
            updated_chromosome.append(server)
        elif server in servers_to_keep:
            updated_chromosome.append(server)
        else:
            updated_chromosome.append(default_random.choice(servers_to_keep))

    return updated_chromosome

@lru_cache(maxsize=None)
def fitness_sum(network: NetworkGraph, chromosome, prev_chromosome=None):
    sum_delays = 0
    migration_cost = 0

    for player_index, server in enumerate(chromosome):
        if server != -1:
            if server:
                sum_delays += network.get_shortest_path_delay(f"P{player_index+1}", server)
                migration_cost = network.calculate_migration_cost(prev_chromosome[player_index], server)
            else:
                # this is the case when a new player was added recently to the network, and it isn't connected to a server yet, increasing fitness significantly
                sum_delays += 1000

    total_fiteness = sum_delays + migration_cost
    return total_fiteness

@lru_cache(maxsize=None)
def fitness_ipd(network: NetworkGraph, chromosome):
    #TODO: this function might be broken since the addition of individual player addition and removal
    max_value = 0
    delay = 0

    # Retrieve the selected servers and connected players
    connected_players_to_server = {}  
    for player_index, server_index in enumerate(chromosome):
        if server_index not in connected_players_to_server and server_index is not None:
             connected_players_to_server[server_index] = []

        if server_index != -1 and server_index is not None:
            connected_players_to_server[server_index].append(f"P{player_index+1}")

    # Calculate interplayer delay for players connected to the same server
    for server, players_list in connected_players_to_server.items():
        for player1 in players_list:
            for player2 in players_list:
                if player1 != player2:
                    delay = network.get_shortest_path_delay(player1, server) + network.get_shortest_path_delay(player2, server)
                    if delay > max_value:
                        max_value = delay
                if len(players_list) == 1:
                    delay = network.get_shortest_path_delay(player1, server)
                    if delay > max_value:
                        max_value = delay
                
    return max_value

@lru_cache(maxsize=None)
def fitness_sum_ipd(network: NetworkGraph, chromosome, players, init_fitnesses, ratio):
    max_sum_fitness, max_ipd_fitness = init_fitnesses

    normalized_sum_delay = fitness_sum(network, chromosome) / max_sum_fitness
    normalized_max_ipd = fitness_ipd(network, chromosome) / max_ipd_fitness

    return ratio * 0.1 * normalized_sum_delay + (10 - ratio) * 0.1 * normalized_max_ipd


def fitness(network: NetworkGraph, chromosome, method, init_fitnesses=None, ratio=6, prev_chromosome=None):
    if method == 'ipd':
        return fitness_ipd(network, chromosome)
    elif method == 'sum':
        return fitness_sum(network, chromosome, prev_chromosome)
    elif method == 'sum_ipd':
        return fitness_sum_ipd(network, chromosome, init_fitnesses, ratio)
    else:
        raise ValueError("Invalid fitness method. Choose from 'sum', 'ipd', 'sum_ipd'.")

def single_point_crossover(parent1, parent2):
    crossover_point = random.randint(1, len(parent1) - 1)
    child1 = parent1[:crossover_point] + parent2[crossover_point:]
    child2 = parent2[:crossover_point] + parent1[crossover_point:]
    return child1, child2

def uniform_crossover(parent1, parent2):
    child1 = []
    child2 = []
    for gene1, gene2 in zip(parent1, parent2):
        if default_random.random() < 0.5:
            child1.append(gene1)
            child2.append(gene2)
        else:
            child1.append(gene2)
            child2.append(gene1)
    return child1, child2

def multi_point_crossover(parent1, parent2):
    num_points = default_random.randint(1, len(parent1) - 1)
    points = sorted(default_random.sample(range(1, len(parent1)), num_points))

    child1 = []
    child2 = []
    last_point = 0
    for point in points:
        if (points.index(point) + 1) % 2 == 0:
            child1.extend(parent1[last_point:point])
            child2.extend(parent2[last_point:point])
        else:
            child1.extend(parent2[last_point:point])
            child2.extend(parent1[last_point:point])
        last_point = point

    child1.extend(parent1[last_point:])
    child2.extend(parent2[last_point:])

    return child1, child2

def crossover(parent1, parent2, method='single_point'):
    if method == 'single_point':
        return single_point_crossover(parent1, parent2)
    elif method == 'uniform':
        return uniform_crossover(parent1, parent2)
    elif method == 'multi_point':
        return multi_point_crossover(parent1, parent2)
    else:
        raise ValueError("Invalid crossover method. Choose from 'single_point', 'uniform', or 'multi_point'.")

def mutate(network, chromosome, mutation_rate, servers, method='mut_servers'):
    if method == 'mut_servers':
        return mutate_servers(network, chromosome, mutation_rate, method='move_to_neighbours')
    elif method == 'mut_players':
        return mutate_players(chromosome, mutation_rate, servers)
    else:
        raise ValueError("Invalid mutation method. Choose from 'mut_servers', or 'mut_players'.")


def mutate_servers(network: NetworkGraph, chromosome, mutation_rate, method='move_to_neighbours'):
    if method == 'increment_or_decrement':

        mutated_chromosome = chromosome.copy()
        unique_servers = list(set(chromosome))

        for server in unique_servers:
            if default_random.random() < mutation_rate:
                if int(server) < (len(servers) - 1):
                    incr = str(int(server) + 1)
                else:
                    decr = str(int(server) - 1)
                    incr = decr
                if int(server) == 0:
                    decr = str(1)
                else:
                    decr = str(int(server) - 1)

                new_server = default_random.choice([incr, decr])

                for i in range(len(mutated_chromosome)):
                    if mutated_chromosome[i] == server:
                        mutated_chromosome[i] = new_server
        return mutated_chromosome
    
    elif method == 'move_to_neighbours':

        mutated_chromosome = chromosome.copy()
        unique_servers = list(set(chromosome))

        for server in unique_servers:
            if default_random.random() < mutation_rate:
                closest_servers = network.get_closest_servers(server)
                new_server = default_random.choice(closest_servers)

                for i in range(len(mutated_chromosome)):
                    if mutated_chromosome[i] == server:
                        mutated_chromosome[i] = new_server

        return mutated_chromosome

    else:
        print(f"Method type: {method} is not found!")

def mutate_edge_servers(network: NetworkGraph, chromosome, mutation_rate):
    mutated_chromosome = chromosome.copy()
    unique_servers = [server for server in set(chromosome) if server != -1]

    for server in unique_servers:
        if default_random.random() < mutation_rate:
            # in case the player isn't connected to a server yet, we connect it to a random one
            if server is None:
                new_server = default_random.choice(unique_servers)
                while new_server == None:
                    new_server = default_random.choice(unique_servers)
            else:
                # in other cases we try to migrate players to edge servers
                closest_edge_servers = network.get_closest_servers(server)
                for srv in closest_edge_servers:
                    if not network.is_edge_server(srv):
                        closest_edge_servers.remove(srv)
                if closest_edge_servers:
                    new_server = default_random.choice(closest_edge_servers)
                else:
                    # we can't move to an edge server so we return
                    return chromosome

            for i in range(len(mutated_chromosome)):
                if mutated_chromosome[i] == server:
                    mutated_chromosome[i] = new_server

    return mutated_chromosome

def mutate_players(chromosome, mutation_rate, servers):
    #TODO: this function might be broken since the addition of individual player addition and removal
    mutated_chromosome = chromosome[:]
    for i in range(len(mutated_chromosome)):
        if default_random.random() < mutation_rate:
            if mutated_chromosome[i] != -1:
                mutated_chromosome[i] = default_random.choice(servers)

    return mutated_chromosome

def roulette_wheel_selection(population, fitness_values):
    # Perform roulette wheel selection based on inverted fitness values
    total_fitness = sum(fitness_values)
    
    # Invert fitness values
    inverted_fitness_values = [total_fitness - fitness for fitness in fitness_values]
    
    # Calculate selection probabilities based on inverted fitness values
    selection_probabilities = [fitness / sum(inverted_fitness_values) for fitness in inverted_fitness_values]
    
    # Select parents using inverted probabilities
    #selected_parents_indices = np.random.choice(len(population), size=len(population)//2, p=selection_probabilities)
    selected_parents_indices = default_random.choices(population, weights=selection_probabilities, k=len(population)//2)
    
    # Return selected parents
   # selected_parents = [population[idx] for idx in selected_parents_indices]
    return selected_parents_indices

def tournament_selection(population, fitness_values, tournament_size):
    # Perform tournament selection based on fitness values and tournament size
    selected_parents = []
    for _ in range(len(population) // 2):
        tournament_indices = list(np.random.choice(len(population), size=int(tournament_size), replace=False))
        tournament_fitness = [fitness_values[idx] for idx in tournament_indices]
        winner_index = tournament_indices[np.argmin(tournament_fitness)]
        selected_parents.append(population[winner_index])
    return selected_parents

def rank_based_selection(population, fitness_values):
    # Sort population indices based on fitness values
    sorted_indices = sorted(range(len(fitness_values)), key=lambda i: fitness_values[i])
    
    # Calculate ranks
    ranks = list(range(1, len(population) + 1))
    
    # Normalize ranks to obtain selection probabilities
    total_rank = sum(ranks)
    selection_probabilities = [rank / total_rank for rank in ranks]

    inverted = [1/prob for prob in selection_probabilities]
    
    # Randomly select parents based on selection probabilities
    selected_parents_indices = default_random.choices(sorted_indices, weights=inverted, k=len(population)//2)
    
    # Return selected parents
    selected_parents = [population[idx] for idx in selected_parents_indices]
    return selected_parents

def selection(population, fitness_values, selection_strategy, tournament_size=None):
    if selection_strategy == "roulette_wheel":
        return roulette_wheel_selection(population, fitness_values)
    elif selection_strategy == "tournament":
        return tournament_selection(population, fitness_values, tournament_size)
    elif selection_strategy == "rank_based":
        return rank_based_selection(population, fitness_values)
    else:
        raise ValueError("Invalid selection strategy")

def calculate_init_fitness(network, players, init_population, method):

    fitness_values = [fitness(network, tuple(chromosome), tuple(players), method) for chromosome in init_population]
    init_pop_fitness = sorted(init_population, key=lambda x: fitness_values[init_population.index(x)])
    max_fitness = fitness_values[init_population.index(init_pop_fitness[-1])]

    return max_fitness

def genetic_algorithm(network: NetworkGraph, players, servers, population_size, mutation_rate, generations, min_connected_players, max_connected_players, max_server_nr, 
                      selection_strategy="tournament", tournament_size=None, fitness_method='ipd', crossover_method='uniform', ratio=6, debug_prints=True, initial_pop=None):
    
    if debug_prints:
        cntr = 0

    if initial_pop is None:
        if debug_prints:
            #print("Initial population wasn't passed, generating random population!")
            logger.log("Initial population wasn't passed, generating random population!")
        population = initial_population(players, servers, population_size)
    else:
        population = chromosome_to_uniform_population(initial_pop, population_size)

    if fitness_method == 'sum_ipd':
        # calculating maximums to normalize fitness functions
        init_sum_fitness = calculate_init_fitness(network, players, population, method='sum')
        init_ipd_fitness = calculate_init_fitness(network, players, population, method='ipd')
        init_fitnesses = (init_sum_fitness, init_ipd_fitness)

    for _ in range(int(generations)):
        if debug_prints:
            cntr += 1

        if fitness_method == 'sum_ipd':
            fitness_values = [fitness(network, tuple(chromosome), tuple(players), fitness_method, init_fitnesses, ratio) for chromosome in population]
        else:
            fitness_values = [fitness(network, tuple(chromosome), tuple(players), fitness_method) for chromosome in population]
        sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])  
        best_solution = sorted_pop[0]

        best_fitness = fitness_values[population.index(best_solution)]

        if debug_prints and cntr >= 10:
            cntr = 0
            print("Fitness: ", best_fitness)

        parents = selection(population, fitness_values, selection_strategy, tournament_size)
        offspring = []
        while len(offspring) < population_size - len(parents):
            parent1, parent2 = default_random.sample(parents, 2)
            child1, child2 = crossover(parent1, parent2, method=crossover_method)
            child1 = mutate(network, child1, mutation_rate, servers, method=default_random.choice(['mut_players', 'mut_servers']))
            child2 = mutate(network, child2, mutation_rate, servers, method=default_random.choice(['mut_players', 'mut_servers']))

            # Enforce boundaries
            child1 = enforce_max_server_occurrences(child1, max_server_nr)
            child1 = enforce_min_max_players_per_server(network, child1, max_connected_players, min_connected_players)
            child2 = enforce_max_server_occurrences(child2, max_server_nr)
            child2 = enforce_min_max_players_per_server(network, child2, max_connected_players, min_connected_players)

            offspring.extend([child1, child2])

        population = parents + offspring

    sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])  
    best_solution = sorted_pop[0]
    network.set_player_server_metrics(best_solution)

    return True

def plot_fitness_comparison(results, generations):
    plt.figure(figsize=(14, 8))
    for param_key, param_results in results.items():
        for key, fitness_stats in param_results.items():
            mean_fitness = fitness_stats['mean']
            std_err = fitness_stats['stderr']
            lower_bound = mean_fitness - 1.96 * std_err
            upper_bound = mean_fitness + 1.96 * std_err
            plt.plot(range(generations), mean_fitness, label=f'{param_key} {key}')
            plt.fill_between(range(generations), lower_bound, upper_bound, alpha=0.2)
    plt.xlabel('Generations')
    plt.ylabel('Fitness')
    plt.legend()
    plt.title('Fitness Comparison') #with Confidence Intervals
    plt.show()

def compare_fitness_methods(network, players, servers, mutation_rates, generation_counts, population_sizes, 
                            min_connected_players, max_connected_players, tournament_sizes, max_server_nr, ratio=6, runs=2):
    
    fitness_methods = ['sum']
    selection_strategies = ['tournament', 'rank_based'] #rank_based
    crossover_methods = ['multi_point', 'uniform']
    mutation_methods = ['mut_players', 'random_muts']
    results = {}

    for tournament_size in tournament_sizes:
        for mutation in mutation_methods:
            for mutation_rate in mutation_rates:
                for generations in generation_counts:
                    for population_size in population_sizes:
                        #param_key = f'pop_size_{population_size}_gen_{generations}_mut_{mutation_rate}'
                        param_key = f'{mutation}_{mutation_rate}'
                        results[param_key] = {}

                        for fitness_method in fitness_methods:
                            for selection_strategy in selection_strategies:
                                for crossover_method in crossover_methods:
                                    key = f'{fitness_method}_{selection_strategy}_{crossover_method}'
                                    all_fitness_histories = []

                                    for run in range(runs):
                                        population = initial_population(players, servers, population_size)
                                        fitness_history = []

                                        if fitness_method == 'sum_ipd':
                                            init_sum_fitness = calculate_init_fitness(network, players, population, 'sum')
                                            init_ipd_fitness = calculate_init_fitness(network, players, population, 'ipd')
                                            init_fitnesses = (init_sum_fitness, init_ipd_fitness)
                                        else:
                                            init_fitnesses = None

                                        for gen in range(generations):
                                            fitness_values = [
                                                fitness(network, tuple(chrom), tuple(players), fitness_method, init_fitnesses, ratio) 
                                                if fitness_method == 'sum_ipd' else 
                                                fitness(network, tuple(chrom), tuple(players), fitness_method)
                                                for chrom in population
                                            ]

                                            best_fitness = min(fitness_values)
                                            fitness_history.append(best_fitness)

                                            parents = selection(population, fitness_values, selection_strategy, tournament_size)
                                            offspring = []
                                            while len(offspring) < population_size - len(parents):
                                                parent1, parent2 = random.sample(parents, 2)
                                                child1, child2 = crossover(parent1, parent2, method=crossover_method)
                                                if mutation == 'random_muts':
                                                    child1 = mutate(child1, mutation_rate, servers, method=default_random.choice(['mut_servers', 'mut_players']))
                                                    child2 = mutate(child2, mutation_rate, servers, method=default_random.choice(['mut_servers', 'mut_players']))
                                                else:
                                                    child1 = mutate(child1, mutation_rate, servers, method=mutation)
                                                    child2 = mutate(child2, mutation_rate, servers, method=mutation) 
                                                child1 = enforce_min_max_players_per_server(enforce_max_server_occurrences(child1, max_server_nr), max_connected_players, min_connected_players)
                                                child2 = enforce_min_max_players_per_server(enforce_max_server_occurrences(child2, max_server_nr), max_connected_players, min_connected_players)
                                                offspring.extend([child1, child2])

                                            population = parents + offspring

                                        all_fitness_histories.append(fitness_history)

                                    mean_fitness = np.mean(all_fitness_histories, axis=0)
                                    stderr_fitness = sem(all_fitness_histories, axis=0)
                                    results[param_key][key] = {'mean': mean_fitness, 'stderr': stderr_fitness}

    plot_fitness_comparison(results, generations)

# Example usage
if __name__ == "__main__":
    config_file = "/Users/ebenbot/Documents/University/cloud_work/genconfig.ini"
    config = read_configuration(config_file)
    param_combinations = read_parameters_from_genconfig(config)
    num_players, nr_of_servers, max_players_connected, mutation_rate, generation_size, tournament_size = param_combinations[0]
    network = NetworkGraph(config=config, num_players=num_players)
    players = list(network.players)
    servers = network._only_servers
    min_connected_players = 4
    max_server_nr = nr_of_servers

    mutation_rates = [0.01]
    generation_counts = [2000]
    population_sizes = [100]
    tournament_sizes = [4]

    compare_fitness_methods(network, players, servers, mutation_rates, generation_counts, population_sizes, 
                            min_connected_players, max_players_connected, tournament_sizes, max_server_nr, ratio=10)