import networkx as nx
import random
from utils import *
from network_graph import *
from visualization import *
from gurobi import *

# #usa, germany, cost
# topology = "cost"

# config_file = r"C:\Users\bbenc\OneDrive\Documents\aGraph\cloud_work\config.ini"
# config = read_configuration(config_file)

# topology_file = get_topology_filename(topology, config)
# save_dir = get_save_dir(config)
# seed_value = 42



# debug_prints, optimize, save, plot, sum_model, ipd_model, gen_model = get_toggles_from_config(config)

# # Adding server nodes
# network = NetworkGraph()
# network.load_topology(topology_file)

# # Getting server positions
# servers = list(network.graph.nodes)
# server_positions = network.get_server_positions()


# long_range, lat_range = get_lat_long_range(topology)
# num_players = 30

# players = generate_players(num_players, long_range, lat_range, seed_value)
# network.add_players(players)



# for player in players:
#             network.connect_player_to_server(players, player, server_positions)

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
    extra_servers = [server for server, count in server_counts.items() if count >= 1]
    random.shuffle(extra_servers)

    # Csak az első max_server_nr szükséges
    servers_to_keep = extra_servers[:max_server_nr]

    # Távolítsuk el azokat a szervereket, amelyek nem kellenek
    chromosome = [server if server in servers_to_keep else None for server in chromosome]

    # Távolítsuk el a None értékeket
    chromosome = [server if server is not None else random.choice(servers_to_keep) for server in chromosome]

    return chromosome

def fitness(network: NetworkGraph, chromosome, players):
    sum_delay = 0
    for i, server in enumerate(chromosome):
        player = players[i]
        sum_delay += network.get_shortest_path_delay(player, server)
    return sum_delay

def crossover(parent1, parent2, max_connected_players, max_server_nr):
    crossover_point = random.randint(1, len(parent1) - 1)
    child1 = parent1[:crossover_point] + parent2[crossover_point:]
    child2 = parent2[:crossover_point] + parent1[crossover_point:]

    # Ensure maximum players per server

    child1 = enforce_max_server_occurrences(child1, max_server_nr)
    child2 = enforce_max_server_occurrences(child2, max_server_nr)

    child1 = enforce_max_players_per_server(child1, max_connected_players)
    child2 = enforce_max_players_per_server(child2, max_connected_players)

    return child1, child2

def mutate(chromosome, mutation_rate, servers, max_connected_players, max_server_nr):
    mutated_chromosome = chromosome[:]
    for i in range(len(mutated_chromosome)):
        if random.random() < mutation_rate:
            mutated_chromosome[i] = random.choice(servers)
    
    # Ensure maximums after mutation
    mutated_chromosome = enforce_max_server_occurrences(mutated_chromosome, max_server_nr)
    mutated_chromosome = enforce_max_players_per_server(mutated_chromosome, max_connected_players)

    return mutated_chromosome

def genetic_algorithm(network: NetworkGraph, players, servers, population_size, mutation_rate, generations, max_connected_players, max_server_nr):
    best_fitnesses = []
    average_fitnesses = []
    population = initial_population(players, servers, population_size)
    for iter in range(generations):
        if iter == 999:
            print('hi')

        population = sorted(population, key=lambda x: fitness(network, x, players))
        best_solution = population[0]
        best_fitness = fitness(network, best_solution, players)
        average_fitness = sum(fitness(network, chromosome, players) for chromosome in population) / population_size
        best_fitnesses.append(best_fitness)
        average_fitnesses.append(average_fitness)

        parents = population[:population_size // 2]
        offspring = []

        while len(offspring) < population_size - len(parents):
            parent1, parent2 = random.sample(parents, 2)
            child1, child2 = crossover(parent1, parent2, max_connected_players, max_server_nr)
            child1 = mutate(child1, mutation_rate, servers, max_connected_players, max_server_nr)
            child2 = mutate(child2, mutation_rate, servers, max_connected_players, max_server_nr)
            offspring.extend([child1, child2])

        population = parents + offspring

    # Retrieve the selected servers and connected players
    connected_players_to_server = {}  
    for player_index, server_index in enumerate(best_solution):
        if server_index not in connected_players_to_server:
             connected_players_to_server[server_index] = []

        connected_players_to_server[server_index].append(f"P{player_index+1}")

    player_server_paths = []
    for server_idx, connected_players_list in connected_players_to_server.items():
        if connected_players_list:
            for player in connected_players_list:
                path = network.get_shortest_path(player, server_idx)
                player_server_paths.append((player, server_idx, path))

    #return best_solution, best_fitnesses, average_fitnesses, connected_players_to_server, player_server_paths
    return best_solution, connected_players_to_server, player_server_paths

# population_size = 100
# mutation_rate = 0.1
# generations = 1000
# max_connected_players = 20
# max_server_nr = 5


# best_solution, best_fitnesses, average_fitnesses, not_used1, not_used2 = genetic_algorithm(network, players, servers, population_size, mutation_rate, generations, max_connected_players, max_server_nr)

# # Plotting the fitness over generations
# plt.plot(range(generations), best_fitnesses, label='Best Fitness')
# plt.plot(range(generations), average_fitnesses, label='Average Fitness')
# plt.xlabel('Generation')
# plt.ylabel('Fitness')
# plt.title('Fitness over Generations')
# plt.legend()
# plt.show()
