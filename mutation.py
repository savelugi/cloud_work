import networkx as nx
import random
from utils import *
from network_graph import *
from visualization import *
from gurobi import *
import numpy as np
from functools import lru_cache

# #usa, germany, cost
# topology = "cost"

# #config_file = r"C:\Users\bbenc\OneDrive\Documents\aGraph\cloud_work\config.ini"
# config_file = '/Users/ebenbot/Documents/University/cloud_work/config.ini'

# config = read_configuration(config_file)

# topology_file = get_topology_filename(topology, config)
# save_dir = get_save_dir(config)
# seed_value = 42



# debug_prints, optimize, save, plot, active_models= get_toggles_from_config(config)

# # Adding server nodes
# network = NetworkGraph()
# network.load_topology(topology_file)

# # Getting server positions
# servers = list(network.graph.nodes)
# server_positions = network.get_server_positions()


# long_range, lat_range = get_lat_long_range(topology)
# num_players = 100

# players = generate_players(num_players, long_range, lat_range, seed_value)
# network.add_players(players)



# for player in players:
#     network.connect_player_to_server(players, player, server_positions)

# players = list(players)


def initial_population(players, servers, population_size):
    population = []
    for _ in range(population_size):
        chromosome = [random.choice(servers) for _ in range(len(players))]
        population.append(chromosome)
    return population

def enforce_max_players_per_server(chromosome, max_connected_players):
    server_counts = {server: 0 for server in set(chromosome)}
    for server in chromosome:
        server_counts[server] += 1

    for server, count in server_counts.items():
        if count > max_connected_players:
            # Find indices of players connected to this server
            indices = [i for i, s in enumerate(chromosome) if s == server]
            # Randomly shuffle the indices to randomize the selection
            random.shuffle(indices)
            # Take the first max_connected_players indices to keep
            drop_indices = indices[max_connected_players:]

            # Determine servers with the second most players
            sorted_counts = sorted(set(server_counts.values()), reverse=True)
            second_max_count = sorted_counts[1] if len(sorted_counts) > 1 else sorted_counts[0]
            second_max_player_servers = [srv for srv, cnt in server_counts.items() if cnt == second_max_count]

            # Move dropped players to servers with the fewest players
            for idx in drop_indices:
                for srv in second_max_player_servers:
                    if server_counts[srv] < max_connected_players:
                        chromosome[idx] = srv
                        server_counts[srv] += 1
                        server_counts[server] -=1
                        break

    return chromosome

def enforce_max_server_occurrences(chromosome, max_server_nr):
    server_counts = {}
    for server in set(chromosome):
        server_counts[server] = chromosome.count(server)

    # Ha kevesebb szerver van, mint a maximum megengedett, akkor nincs teendő
    if len(server_counts) <= max_server_nr:
        return chromosome

    # Túl sok szerver van, szükség van a csökkentésre
    servers = [server for server, count in server_counts.items() if count >= 1]
    random.shuffle(servers)

    # Csak az első max_server_nr szükséges
    servers_to_keep = servers[:max_server_nr]

    # Távolítsuk el azokat a szervereket, amelyek nem kellenek
    chromosome = [server if server in servers_to_keep else None for server in chromosome]

    # Távolítsuk el a None értékeket
    chromosome = [server if server is not None else random.choice(servers_to_keep) for server in chromosome]

    return chromosome

@lru_cache(maxsize=None)
def fitness_sum(network: NetworkGraph, chromosome, players):
    sum_delays = 0
    for i, server in enumerate(chromosome):
        player = players[i]
        sum_delays += network.get_shortest_path_delay(player, server)
    return sum_delays

@lru_cache(maxsize=None)
def fitness_ipd(network: NetworkGraph, chromosome, players):
    max_value = 0

    # Retrieve the selected servers and connected players
    connected_players_to_server = {}  
    for player_index, server_index in enumerate(chromosome):
        if server_index not in connected_players_to_server:
             connected_players_to_server[server_index] = []
        connected_players_to_server[server_index].append(f"P{player_index+1}")

    # Calculate interplayer delay for players connected to the same server
    for server, players_list in connected_players_to_server.items():
        for player1 in players_list:
            for player2 in players_list:
                if player1 != player2:
                    delay = network.get_shortest_path_delay(player1, server) + network.get_shortest_path_delay(player2, server)
                    if delay > max_value:
                        max_value = delay

    return max_value

@lru_cache(maxsize=None)
def fitness_sum_ipd(network: NetworkGraph, chromosome, players):
    sum_player_server_delay = 0
    min_sum_delay = float('inf')  
    max_sum_delay = 0

    for i, server in enumerate(chromosome):
        player = players[i]
        delay = network.get_shortest_path_delay(player, server)
        sum_player_server_delay += delay
        
        if delay < min_sum_delay:
            min_sum_delay = delay
        if delay > max_sum_delay:
            max_sum_delay = delay

    normalized_sum_delay = (sum_player_server_delay - min_sum_delay) / (max_sum_delay - min_sum_delay) if max_sum_delay != min_sum_delay else 0

    max_player_player_delay = 0
    min_interplayer_delay = float('inf')
    max_interplayer_delay = 0

    connected_players_to_server = {}  
    for player_index, server_index in enumerate(chromosome):
        if server_index not in connected_players_to_server:
            connected_players_to_server[server_index] = []
        connected_players_to_server[server_index].append(f"P{player_index+1}")

    for server, players_list in connected_players_to_server.items():
        for player1 in players_list:
            for player2 in players_list:
                if player1 != player2:
                    delay = network.get_shortest_path_delay(player1, server) + network.get_shortest_path_delay(player2, server)

                    if delay < min_interplayer_delay:
                        min_interplayer_delay = delay
                    if delay > max_interplayer_delay:
                        max_interplayer_delay = delay

                    if delay > max_player_player_delay:
                        max_player_player_delay = delay

    normalized_interplayer_delay = (max_player_player_delay - min_interplayer_delay) / (max_interplayer_delay - min_interplayer_delay) if max_interplayer_delay != min_interplayer_delay else 0

    # Visszaadjuk a súlyozott összfitnesszt
    return 0.7 * sum_player_server_delay +  13 * 0.3 *max_player_player_delay


def fitness(network: NetworkGraph, chromosome, players, method):
    # Az általános függvény, amely dönti el, hogy melyik fitness függvényt kell használni
    if method == 'ipd':
        return fitness_ipd(network, chromosome, players)
    elif method == 'sum':
        return fitness_sum(network, chromosome, players)
    elif method == 'sum_ipd':
        return fitness_sum_ipd(network, chromosome, players)
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
        if random.random() < 0.5:
            child1.append(gene1)
            child2.append(gene2)
        else:
            child1.append(gene2)
            child2.append(gene1)
    return child1, child2

def multi_point_crossover(parent1, parent2):
    num_points = random.randint(1, len(parent1) - 1)
    points = sorted(random.sample(range(1, len(parent1)), num_points))

    child1 = []
    child2 = []
    last_point = 0
    for point in points:
        print(points.index(point))
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

def mutate(chromosome, mutation_rate, servers):
    mutated_chromosome = chromosome[:]
    for i in range(len(mutated_chromosome)):
        if random.random() < mutation_rate:
            mutated_chromosome[i] = random.choice(servers)

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
    selected_parents_indices = random.choices(population, weights=selection_probabilities, k=len(population)//2)
    
    # Return selected parents
   # selected_parents = [population[idx] for idx in selected_parents_indices]
    return selected_parents_indices

def tournament_selection(population, fitness_values, tournament_size):
    # Perform tournament selection based on fitness values and tournament size
    selected_parents = []
    for _ in range(len(population) // 2):
        tournament_indices = list(np.random.choice(len(population), size=tournament_size, replace=False))
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
    selected_parents_indices = random.choices(sorted_indices, weights=inverted, k=len(population)//2)
    
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

def genetic_algorithm(network: NetworkGraph, players, servers, population_size, mutation_rate, generations, max_connected_players, max_server_nr, 
                      selection_strategy="rank_based", tournament_size=None, fitness_method='ipd'):
    
    best_fitnesses = []
    average_fitnesses = []
    cntr = 0

    population = initial_population(players, servers, population_size)

    for iter in range(generations):
        cntr += 1
        fitness_values = [fitness(network, tuple(chromosome), tuple(players), fitness_method) for chromosome in population]
        sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])  

        best_solution = sorted_pop[0]

        best_fitness = fitness_values[population.index(best_solution)]
        best_fitnesses.append(best_fitness)

        average_fitness = sum(fitness_values) / population_size
        average_fitnesses.append(average_fitness)

        if cntr >= 10:
            cntr = 0
            print("Fitness: ", best_fitness)

        parents = selection(population, fitness_values, selection_strategy, tournament_size)
        offspring = []
        while len(offspring) < population_size - len(parents):
            parent1, parent2 = random.sample(parents, 2)
            child1, child2 = crossover(parent1, parent2, method='single_point')
            child1 = mutate(child1, mutation_rate, servers)
            child2 = mutate(child2, mutation_rate, servers)

            # Enforce boundaries
            child1 = enforce_max_server_occurrences(child1, max_server_nr)
            child1 = enforce_max_players_per_server(child1, max_connected_players)
            child2 = enforce_max_server_occurrences(child2, max_server_nr)
            child2 = enforce_max_players_per_server(child2, max_connected_players)

            offspring.extend([child1, child2])

        population = parents + offspring

    # Retrieve the selected servers and connected players
    connected_players_to_server = {}  
    for player_index, server_index in enumerate(best_solution):
        if server_index not in connected_players_to_server:
             connected_players_to_server[server_index] = []

        connected_players_to_server[server_index].append(f"P{player_index+1}")
        network.graph.nodes[str(server_index)]['server']['game_server'] = 1
        network.graph.nodes[f"P{player_index+1}"]['connected_to_server'] = server_index


    player_server_paths = []
    for server_idx, connected_players_list in connected_players_to_server.items():
        if connected_players_list:
            for player in connected_players_list:
                path = network.get_shortest_path(player, server_idx)
                player_server_paths.append((player, server_idx, path))

    #return best_solution, best_fitnesses, average_fitnesses, connected_players_to_server, player_server_paths
    network.connected_players_info = connected_players_to_server
    network.player_server_paths = player_server_paths
    network.best_solution = best_solution

    return True

# population_size = 100
# mutation_rate = 0.01
# generations = 100
# max_connected_players = 20
# max_server_nr = 5


# best_solution, best_fitnesses, average_fitnesses, not_used1, not_used2 = genetic_algorithm(
#     network, players, servers, population_size, mutation_rate, generations, max_connected_players, max_server_nr,
#     selection_strategy="rank_based",
#     tournament_size=50,
#     fitness_method='sum')

# #Plotting the fitness over generations
# plt.plot(range(generations), best_fitnesses, label='Best Fitness')
# #print("Best fitness score:")
# #print(best_fitnesses[-1])
# plt.plot(range(generations), average_fitnesses, label='Average Fitness')
# plt.xlabel('Generation')
# plt.ylabel('Fitness')
# plt.title('Fitness over Generations')
# plt.legend()
# plt.show()