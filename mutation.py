import networkx as nx
import random
from utils import *
from network_graph import *
from visualization import *
from gurobi import *
import numpy as np
from functools import lru_cache

def initial_population(players, servers, population_size):
    population = []
    for _ in range(population_size):
        chromosome = [random.choice(servers) for _ in range(len(players))]
        population.append(chromosome)
    return population

def enforce_min_max_players_per_server(chromosome, max_connected_players, min_connected_players):
    server_counts = {server: 0 for server in set(chromosome)}
    for server in chromosome:
        server_counts[server] += 1

    for server, count in server_counts.items():
        if count > int(max_connected_players):
            # Find indices of players connected to this server
            indices = [i for i, s in enumerate(chromosome) if s == server]
            # Randomly shuffle the indices to randomize the selection
            random.shuffle(indices)
            # Take the first max_connected_players indices to keep
            drop_indices = indices[int(max_connected_players):]

            # Determine servers with the second most players
            sorted_counts = sorted(set(server_counts.values()), reverse=True)
            second_max_count = sorted_counts[1] if len(sorted_counts) > 1 else sorted_counts[0]
            second_max_player_servers = [srv for srv, cnt in server_counts.items() if cnt == second_max_count]

            # Move dropped players to servers with the fewest players
            for idx in drop_indices:
                for srv in second_max_player_servers:
                    if server_counts[srv] < int(max_connected_players):
                        chromosome[idx] = srv
                        server_counts[srv] += 1
                        server_counts[server] -=1
                        break

    # Ensure minimum number of players per server
    for server, count in server_counts.items():
        if count < int(min_connected_players):
            # Find indices of players connected to this server
            indices = [i for i, s in enumerate(chromosome) if s == server]
            # Randomly shuffle the indices to randomize the selection
            random.shuffle(indices)
            # Take the first min_connected_players indices to fill
            fill_indices = indices[:int(min_connected_players) - count]

            # Determine servers with the fewest players
            min_count = min(server_counts.values())
            min_player_servers = [srv for srv, cnt in server_counts.items() if cnt == min_count]

            # Move players from other servers to fill empty slots
            for idx in fill_indices:
                for srv in min_player_servers:
                    if server_counts[srv] < int(max_connected_players):
                        chromosome[idx] = srv
                        server_counts[srv] += 1
                        server_counts[server] -= 1
                        break

    return chromosome

def enforce_max_server_occurrences(chromosome, max_server_nr):
    server_counts = {}
    for server in set(chromosome):
        server_counts[server] = chromosome.count(server)

    # Ha kevesebb szerver van, mint a maximum megengedett, akkor nincs teendő
    if len(server_counts) <= int(max_server_nr):
        return chromosome

    # Túl sok szerver van, szükség van a csökkentésre
    servers = [server for server, count in server_counts.items() if count >= 1]
    random.shuffle(servers)

    # Csak az első max_server_nr szükséges
    servers_to_keep = servers[:int(max_server_nr)]

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
    delay = 0

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
                if len(players_list) == 1:
                    delay = network.get_shortest_path_delay(player1, server)
                    if delay > max_value:
                        max_value = delay
                
    return max_value

@lru_cache(maxsize=None)
def fitness_sum_ipd(network: NetworkGraph, chromosome, players, init_fitnesses, ratio):
    max_sum_fitness, max_ipd_fitness = init_fitnesses

    normalized_sum_delay = fitness_sum(network, chromosome, players) / max_sum_fitness
    normalized_max_ipd = fitness_ipd(network, chromosome, players) / max_ipd_fitness

    return ratio * 0.1 * normalized_sum_delay + (10 - ratio) * 0.1 * normalized_max_ipd


def fitness(network: NetworkGraph, chromosome, players, method, init_fitnesses=None, ratio=6):
    # Az általános függvény, amely dönti el, hogy melyik fitness függvényt kell használni
    if method == 'ipd':
        return fitness_ipd(network, chromosome, players)
    elif method == 'sum':
        return fitness_sum(network, chromosome, players)
    elif method == 'sum_ipd':
        return fitness_sum_ipd(network, chromosome, players, init_fitnesses, ratio)
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

def calculate_init_fitness(network, players, init_population, method):

    fitness_values = [fitness(network, tuple(chromosome), tuple(players), method) for chromosome in init_population]
    init_pop_fitness = sorted(init_population, key=lambda x: fitness_values[init_population.index(x)])
    max_fitness = fitness_values[init_population.index(init_pop_fitness[-1])]

    return max_fitness

def genetic_algorithm(network: NetworkGraph, players, servers, population_size, mutation_rate, generations, min_connected_players, max_connected_players, max_server_nr, 
                      selection_strategy="rank_based", tournament_size=None, fitness_method='ipd', crossover_method='single_point', ratio=6):
    
    best_fitnesses = []
    #average_fitnesses = []
    cntr = 0

    population = initial_population(players, servers, population_size)

    if fitness_method == 'sum_ipd':
        # calculating maximums to normalize fitness functions
        init_sum_fitness = calculate_init_fitness(network, players, population, method='sum')
        init_ipd_fitness = calculate_init_fitness(network, players, population, method='ipd')
        init_fitnesses = (init_sum_fitness, init_ipd_fitness)

    for _ in range(int(generations)):
        cntr += 1
        if fitness_method == 'sum_ipd':
            fitness_values = [fitness(network, tuple(chromosome), tuple(players), fitness_method, init_fitnesses, ratio) for chromosome in population]
        else:
            fitness_values = [fitness(network, tuple(chromosome), tuple(players), fitness_method) for chromosome in population]
        sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])  
        best_solution = sorted_pop[0]

        best_fitness = fitness_values[population.index(best_solution)]
        #best_fitnesses.append(best_fitness)

        #average_fitness = sum(fitness_values) / population_size
        #average_fitnesses.append(average_fitness)

        if cntr >= 10:
            cntr = 0
            print("Fitness: ", best_fitness)

        parents = selection(population, fitness_values, selection_strategy, tournament_size)
        offspring = []
        while len(offspring) < population_size - len(parents):
            parent1, parent2 = random.sample(parents, 2)
            child1, child2 = crossover(parent1, parent2, method=crossover_method)
            child1 = mutate(child1, mutation_rate, servers)
            child2 = mutate(child2, mutation_rate, servers)

            # Enforce boundaries
            child1 = enforce_max_server_occurrences(child1, max_server_nr)
            child1 = enforce_min_max_players_per_server(child1, max_connected_players, min_connected_players)
            child2 = enforce_max_server_occurrences(child2, max_server_nr)
            child2 = enforce_min_max_players_per_server(child2, max_connected_players, min_connected_players)

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