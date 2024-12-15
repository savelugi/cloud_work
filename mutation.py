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
   
    max_index = max(int(player[1:]) for player in players)
    
    for _ in range(population_size):
        chromosome = []
        current_index = 0
        
        for player in players:
            player_index = int(player[1:])
            
           
            while current_index < player_index - 1:
                chromosome.append(-1)
                current_index += 1
            
            chromosome.append(default_random.choice(servers))
            current_index = player_index
        
        while current_index < max_index:
            chromosome.append(-1)
            current_index += 1
        
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


def constraints_are_met(network, chromosome, max_core_server_nr, max_edge_server_nr, max_connected_players, min_connected_players):
    selected_core_servers = [srv for srv in set(chromosome) if srv != -1 and srv is not None and network.is_core_server(srv)]
    selected_edge_servers = [srv for srv in set(chromosome) if srv != -1 and srv is not None and network.is_edge_server(srv)]

    if len(selected_core_servers) > max_core_server_nr:
        return 1
    if len(selected_edge_servers) > max_edge_server_nr:
        return 2

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
            return 3
        if player_count < min_connected_players and player_count > 0:
            return 4

    return 0


def enforce_min_max_players_per_serverr(network: NetworkGraph, chromosome, max_connected_players, min_connected_players, migrate_to_edge_servers=False):
    player_count_on_servers = {server: 0 for server in network._only_servers}
    for server in chromosome:
        if server != -1 and server:
            player_count_on_servers[server] += 1

    for server, player_count in player_count_on_servers.items():
        if network.is_core_server(server):
            max_players = 2 * max_connected_players
        else:
            max_players = max_connected_players

        if player_count > int(max_players):
            # Find indices of players connected to this server
            connected_players = [i for i, s in enumerate(chromosome) if s == server]

            # Sort connected players by shortest path delay
            sorted_connected_players = sorted(connected_players, key=lambda x: network.get_shortest_path_delay(f"P{x+1}", server))

            drop_connected_player_indices = sorted_connected_players[int(max_players):]
            selected_servers = {srv:player_cnt for srv, player_cnt in player_count_on_servers.items() if player_cnt != 0 and srv != server}
            closest_selected_servers = sorted(selected_servers.keys(), key=lambda srv: network.get_shortest_path_delay(srv, server))

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
                    if player_count_on_servers[srv] < int(max_players):
                        chromosome[idx] = srv
                        player_count_on_servers[srv] += 1
                        player_count_on_servers[server] -=1
                        drop_connected_player_indices.remove(idx)
                        break
            if len(drop_connected_player_indices) > 0:
            # this means that there are not enough selected servers
                closest_servers = network.get_closest_servers(server)
                iter = drop_connected_player_indices.copy()
                for idx in iter:
                    for srv in closest_servers:
                        if player_count_on_servers[srv] < int(max_players):
                            chromosome[idx] = srv
                            player_count_on_servers[srv] += 1
                            player_count_on_servers[server] -=1
                            drop_connected_player_indices.remove(idx)
                            break
                            
            if len(drop_connected_player_indices) > 0:
                print("Hmmmm....")


    for server, player_count in player_count_on_servers.items():
        if player_count < int(min_connected_players) and player_count > 0:

            connected_players = [i for i, s in enumerate(chromosome) if s == server]
            players_to_move = connected_players.copy()
            selected_servers = {srv:player_cnt for srv, player_cnt in player_count_on_servers.items() if player_cnt != 0 and srv != server}
            closest_selected_servers = sorted(selected_servers.keys(), key=lambda srv: network.get_shortest_path_delay(srv, server))
            for player in players_to_move:
                for closest_server in closest_selected_servers:
                    if player_count_on_servers[closest_server] + 1 >= int(min_connected_players) and player_count_on_servers[closest_server] + 1 <= int(max_connected_players):
                        chromosome[player] = closest_server
                        player_count_on_servers[server] -= 1
                        player_count_on_servers[closest_server] += 1
                        break
                players_to_move.remove(player)

    return chromosome


def enforce_max_server_occurrencess(chromosome, max_server_nr):
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
def enforce_min_max_players_per_server(network: NetworkGraph, chromosome, max_connected_players, min_connected_players):
    # Count players on each server
    chromosome = list(chromosome)
    player_count_on_servers = {server: 0 for server in network._only_servers}
    for server in chromosome:
        if server != -1 and server is not None:
            player_count_on_servers[server] += 1

    # Enforce max players per server
    for server, player_count in player_count_on_servers.items():
        if network.is_core_server(server):
            max_players = 2 * max_connected_players
        else:
            max_players = max_connected_players

        if player_count > int(max_players):
            # Find indices of players connected to this server
            connected_players = [i for i, s in enumerate(chromosome) if s == server]

            # Sort connected players by shortest path delay
            sorted_connected_players = sorted(connected_players, key=lambda x: network.get_shortest_path_delay(f"P{x+1}", server))

            drop_connected_player_indices = sorted_connected_players[int(max_players):]
            selected_servers = {srv:player_cnt for srv, player_cnt in player_count_on_servers.items() if player_cnt != 0 and srv != server}
            closest_selected_servers = sorted(selected_servers.keys(), key=lambda srv: network.get_shortest_path_delay(srv, server))

            # Move excess players to closest selected servers
            iter_indices = drop_connected_player_indices.copy()
            for idx in iter_indices:
                for srv in closest_selected_servers:
                    if network.is_core_server(srv):
                        srv_max_players = 2 * max_connected_players
                    else:
                        srv_max_players = max_connected_players
                    if player_count_on_servers[srv] < int(srv_max_players):
                        chromosome[idx] = srv
                        player_count_on_servers[srv] += 1
                        player_count_on_servers[server] -= 1
                        drop_connected_player_indices.remove(idx)
                        break

            # If still not resolved, try any closest servers
            if len(drop_connected_player_indices) > 0:
                closest_all_servers = network.get_closest_servers(server)
                iter_indices = drop_connected_player_indices.copy()
                for idx in iter_indices:
                    for srv in closest_all_servers:
                        if network.is_core_server(srv):
                            srv_max_players = 2 * max_connected_players
                        else:
                            srv_max_players = max_connected_players

                        if player_count_on_servers[srv] < int(srv_max_players):
                            chromosome[idx] = srv
                            player_count_on_servers[srv] += 1
                            player_count_on_servers[server] -= 1
                            drop_connected_player_indices.remove(idx)
                            break

            if len(drop_connected_player_indices) > 0:
                print("Could not reassign all players to meet max constraints.")

    # Enforce min players per server
    for server, player_count in player_count_on_servers.items():
        if player_count < int(min_connected_players) and player_count > 0:
            connected_players = [i for i, s in enumerate(chromosome) if s == server]
            players_to_move = connected_players.copy()
            selected_servers = {srv:player_cnt for srv, player_cnt in player_count_on_servers.items() if player_cnt != 0 and srv != server}
            closest_selected_servers = sorted(selected_servers.keys(), key=lambda srv: network.get_shortest_path_delay(srv, server))
            for player in players_to_move:
                for closest_server in closest_selected_servers:
                    if network.is_core_server(closest_server):
                        srv_max_players = 2 * max_connected_players
                    else:
                        srv_max_players = max_connected_players

                    if (player_count_on_servers[closest_server] + 1 >= int(min_connected_players)) and (player_count_on_servers[closest_server] + 1 <= int(srv_max_players)):
                        chromosome[player] = closest_server
                        player_count_on_servers[server] -= 1
                        player_count_on_servers[closest_server] += 1
                        break
                players_to_move.remove(player)

    return chromosome


@lru_cache(maxsize=None)
def enforce_max_server_occurrences(network: NetworkGraph, chromosome, max_core_server, max_edge_server, initial):
    # Count how many unique core and edge servers are selected
    selected_core_servers = []
    selected_edge_servers = []
    chromosome = list(chromosome)
    for server in set(chromosome):
        if server != -1 and server is not None:
            if network.is_core_server(server):
                selected_core_servers.append(server)
            elif network.is_edge_server(server):
                selected_edge_servers.append(server)

    if len(selected_core_servers) <= int(max_core_server) and len(selected_edge_servers) <= int(max_edge_server):
        return chromosome

    mutated = chromosome.copy()
    default_random.shuffle(selected_core_servers)
    default_random.shuffle(selected_edge_servers)

    core_servers_to_keep = selected_core_servers[:int(max_core_server)]
    edge_servers_to_keep = []
    if initial is False:
        selected_edge_servers[:int(max_edge_server)] 

    for i, server in enumerate(mutated):
        if server == -1:
            continue
        if server in core_servers_to_keep or server in edge_servers_to_keep:
            continue
        elif len(edge_servers_to_keep) > 0:
            mutated[i] = default_random.choice(edge_servers_to_keep)
        elif len(core_servers_to_keep) > 0:
            mutated[i] = default_random.choice(core_servers_to_keep)
        else:
            mutated[i] = default_random.choice(network.core_servers)
    return mutated


@lru_cache(maxsize=None)
def fitness_sum(network: NetworkGraph, chromosome, max_core_server_nr, max_edge_server_nr,max_connected_players, min_connected_players, generation, iteration, prev_chromosome=None, 
                penalty_core_factor=1.0, 
                penalty_edge_factor=1.0, 
                penalty_players_factor=1.0,
                use_penalty=False):

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
                # Large penalty for players not assigned to a server
                sum_delays += 1000

    total_fitness = (sum_delays + migration_cost) / len(network.players)
    if use_penalty is False:
        return total_fitness
    
    # Count selected servers
    selected_core_servers = []
    selected_edge_servers = []
    for srv in set(chromosome):
        if srv != -1 and srv is not None:
            if network.is_core_server(srv):
                selected_core_servers.append(srv)
            elif network.is_edge_server(srv):
                selected_edge_servers.append(srv)

    # Core/edge server count penalty
    if len(selected_core_servers) > max_core_server_nr:
        penalty += penalty_core_factor * total_fitness * (len(selected_core_servers) - max_core_server_nr)

    if len(selected_edge_servers) > max_edge_server_nr:
        penalty += total_fitness * penalty_edge_factor * (len(selected_edge_servers) - max_edge_server_nr)

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
        if player_count < min_connected_players:
            penalty += (min_connected_players - player_count) * total_fitness * penalty_players_factor

    scale = iteration / generation
    fitness_value = (penalty * scale) + total_fitness
    return fitness_value


@lru_cache(maxsize=None)
def fitness_ipd(network: NetworkGraph, chromosome, max_core_server_nr, max_edge_server_nr, 
                max_connected_players, min_connected_players, generation, iteration,
                penalty_core_factor=1.0, 
                penalty_edge_factor=1.0, 
                penalty_players_factor=1.0,
                use_penalty=False):

    max_values_sum = 0
    penalty = 0

    connected_players_to_server = {}
    for player_index, server_index in enumerate(chromosome):
        if server_index not in connected_players_to_server and server_index is not None:
            connected_players_to_server[server_index] = []
        if server_index != -1 and server_index is not None:
            connected_players_to_server[server_index].append(f"P{player_index+1}")

    for srv, players_list in connected_players_to_server.items():
        local_max = 0
        if len(players_list) > 1:
            for player1 in players_list:
                for player2 in players_list:
                    if player1 != player2:
                        delay = network.get_shortest_path_delay(player1, srv) + network.get_shortest_path_delay(player2, srv)
                        if delay > local_max:
                            local_max = delay
        else:
            # If single player on server
            if players_list:
                p = players_list[0]
                delay = network.get_shortest_path_delay(p, srv)
                if delay > local_max:
                    local_max = delay

        max_values_sum += local_max

    fitness_value = max_values_sum
    if use_penalty is False:
        return fitness_value
    
    # Count servers
    selected_core_servers = []
    selected_edge_servers = []
    for s in set(chromosome):
        if s != -1 and s is not None:
            if network.is_core_server(s):
                selected_core_servers.append(s)
            elif network.is_edge_server(s):
                selected_edge_servers.append(s)

    # Penalties
    if len(selected_core_servers) > max_core_server_nr:
        penalty += (penalty_core_factor * max_values_sum * (len(selected_core_servers) - max_core_server_nr))

    if len(selected_edge_servers) > max_edge_server_nr:
        penalty += (penalty_edge_factor * max_values_sum * (len(selected_edge_servers) - max_edge_server_nr)) 

    # Player distribution penalties
    player_count_on_servers = {server: 0 for server in network._only_servers}
    for s in chromosome:
        if s != -1 and s:
            player_count_on_servers[s] += 1

    for srv, player_count in player_count_on_servers.items():
        if network.is_core_server(srv):
            max_player_nr = 2 * max_connected_players
        else:
            max_player_nr = max_connected_players

        if player_count > int(max_player_nr):
            penalty += (player_count - max_player_nr) * max_values_sum * penalty_players_factor
        if player_count < min_connected_players:
            penalty += (min_connected_players - player_count) * max_values_sum * penalty_players_factor

    scale = iteration / generation
    fitness_value = (penalty * scale) + max_values_sum

    return fitness_value


@lru_cache(maxsize=None)
def fitness_qoe(network: NetworkGraph, chromosome, max_core_server_nr, max_edge_server_nr,max_connected_players, min_connected_players, generation, iteration, prev_chromosome=None, 
                penalty_core_factor=1.0, 
                penalty_edge_factor=1.0, 
                penalty_players_factor=1.0,
                use_penalty=False):

    sum_qoe = 0
    migration_cost = 0
    penalty = 0

    for player_index, server in enumerate(chromosome):
        if server != -1:
            if server is not None:
                sum_qoe += network.calculate_QoE(f'P{int(player_index)+1}', server)
                if prev_chromosome:
                    migration_cost += network.calculate_migration_cost(prev_chromosome[player_index], server)
            else:
                # Large penalty for players not assigned to a server
                sum_qoe -= 1000

    total_fitness = (sum_qoe - migration_cost) / len(network.players)
    if use_penalty is False:
        return total_fitness
    
    # Count selected servers
    selected_core_servers = []
    selected_edge_servers = []
    for srv in set(chromosome):
        if srv != -1 and srv is not None:
            if network.is_core_server(srv):
                selected_core_servers.append(srv)
            elif network.is_edge_server(srv):
                selected_edge_servers.append(srv)

    # Core/edge server count penalty
    if len(selected_core_servers) > max_core_server_nr:
        penalty += penalty_core_factor * total_fitness * (len(selected_core_servers) - max_core_server_nr)

    if len(selected_edge_servers) > max_edge_server_nr:
        penalty += total_fitness * penalty_edge_factor * (len(selected_edge_servers) - max_edge_server_nr)

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
        if player_count < min_connected_players:
            penalty += (min_connected_players - player_count) * total_fitness * penalty_players_factor

    scale = iteration / generation
    fitness_value = (penalty * scale) + total_fitness
    return fitness_value


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
            if int(server) > -1:
                if default_random.random() < mutation_rate:
                    closest_servers = network.get_closest_servers(server)
                    new_server = default_random.choice(closest_servers)

                    for i in range(len(mutated_chromosome)):
                        if mutated_chromosome[i] == server:
                            mutated_chromosome[i] = new_server

        return mutated_chromosome

    else:
        print(f"Method type: {method} is not found!")


def mutate_to_edge_servers(network: NetworkGraph, chromosome, mutation_rate, max_core_servers, max_edge_servers):
    mutated_chromosome = chromosome.copy()
    unique_edge_servers = network.edge_servers
    unique_core_servers = network.core_servers

    selected_servers = [server for server in set(chromosome) if server != -1]
    selected_core_servers = [server for server in set(chromosome) if server != -1 and network.is_core_server(server) and server is not None]
    selected_edge_servers = [server for server in set(chromosome) if server != -1 and network.is_edge_server(server) and server is not None]

    for server in selected_servers:
        if default_random.random() < mutation_rate:
            # in case the player isn't connected to a server yet, we activate a random one 
            if server is None:
                new_server = default_random.choice(unique_edge_servers)
                while new_server == None:
                    new_server = default_random.choice(unique_edge_servers)
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
                    #continue

            for i in range(len(mutated_chromosome)):
                if mutated_chromosome[i] == server:
                    mutated_chromosome[i] = new_server

    return mutated_chromosome


def mutate_random_edges(network: NetworkGraph, chromosome, mutation_rate, max_edge_servers, initial):
    chromosome = list(chromosome)
    mutated_chromosome = chromosome.copy()

    selected_core_servers = [server for server in set(chromosome) if server != -1 and network.is_core_server(server) and server is not None]
        
    if default_random.random() < mutation_rate:

        potential_servers = selected_core_servers + default_random.sample(network.edge_servers, k=max_edge_servers) if initial is True else network.core_servers

        for i in range(len(mutated_chromosome)):
            if mutated_chromosome[i] != -1:
                mutated_chromosome[i] = default_random.choice(potential_servers)
        
    return mutated_chromosome


def muts(network: NetworkGraph, chromosome, mutation_rate, max_edge_servers, initial):
    mutated_chromosome = chromosome.copy()
    selected_servers = [server for server in set(chromosome) if server != -1]
    selected_core_servers = [server for server in set(chromosome) if server != -1 and network.is_core_server(server) and server is not None]
    selected_edge_servers = [server for server in set(chromosome) if server != -1 and network.is_edge_server(server) and server is not None]
        
    # sometimes because of the crossover, we are out of the bounds
    if len(selected_servers) > len(selected_core_servers) + max_edge_servers:
        potential_servers = default_random.sample(selected_servers, k=(len(selected_core_servers) + max_edge_servers))
        for i in range(len(mutated_chromosome)):
            if mutated_chromosome[i] != -1:
                mutated_chromosome[i] = default_random.choice(potential_servers)
        return mutated_chromosome
    


    if default_random.random() < mutation_rate:
        if len(selected_edge_servers) < max_edge_servers:
            potential_servers = selected_core_servers + default_random.sample(network.edge_servers, k=max_edge_servers) 
        else:
            potential_servers = selected_core_servers + default_random.sample(selected_edge_servers, k=(max_edge_servers - 1)) + default_random.sample(network.edge_servers, k=1)

        if initial:
            potential_servers = network.core_servers

        for i in range(len(mutated_chromosome)):
            if mutated_chromosome[i] != -1:
                mutated_chromosome[i] = default_random.choice(potential_servers)
        
    return mutated_chromosome


def mutate_to_edge_serverss(network: NetworkGraph, chromosome, mutation_rate, max_edge_servers, max_players_per_edge_server, min_players_per_edge_server, min_players_per_core_server):

    mutated_chromosome = chromosome.copy()

    # Get the list of core and edge servers from the network
    selected_core_servers = [server for server in set(chromosome) if server != -1 and network.is_core_server(server) and server is not None]
    edge_servers = network.edge_servers

    # Track the number of active edge servers
    active_edge_servers = set()

    # Count current players on all servers
    player_count_on_servers = {server: 0 for server in network._only_servers}
    for server in chromosome:
        if server != -1 and server:
            player_count_on_servers[server] += 1
            if network.is_edge_server(server):
                active_edge_servers.add(server)

    for player_idx, current_server in enumerate(mutated_chromosome):
        # Skip players not in the network
        if current_server == -1:
            continue

        # Handle players without a server (new players)
        if current_server is None:
            # Assign to a random edge or core server
            potential_targets = selected_core_servers + edge_servers
            potential_targets = [
                srv for srv in potential_targets
                if (srv in selected_core_servers and player_count_on_servers[srv] + 1 <= 2 * max_players_per_edge_server) or
                   (srv in edge_servers and player_count_on_servers[srv] + 1 <= max_players_per_edge_server and len(active_edge_servers) < max_edge_servers)
            ]
            if potential_targets:
                new_server = default_random.choice(potential_targets)
                mutated_chromosome[player_idx] = new_server
                player_count_on_servers[new_server] += 1
                if new_server in edge_servers:
                    active_edge_servers.add(new_server)
            continue

        # Randomly decide if this player should migrate
        if default_random.random() < mutation_rate:
            # Determine potential migration targets
            if current_server in selected_core_servers:
                # If on a core server, migrate to another core or edge server
                potential_targets = [srv for srv in selected_core_servers if srv != current_server] + edge_servers
            else:
                # If on an edge server, migrate to any core or edge server
                potential_targets = selected_core_servers + edge_servers

            # Prevent emptying core servers below their minimum player count
            if current_server in selected_core_servers and player_count_on_servers[current_server] + 1 <= min_players_per_core_server:
                potential_targets = [srv for srv in potential_targets if srv != current_server]


            # Enforce player limits and edge server count
            potential_targets = [
                srv for srv in potential_targets
                if (srv in selected_core_servers and player_count_on_servers[srv] + 1 <= 2 * max_players_per_edge_server) or #and player_count_on_servers[srv] + 1 >= min_players_per_core_server) or
                (srv in edge_servers and player_count_on_servers[srv] + 1 <= max_players_per_edge_server and 
                    (srv in active_edge_servers or len(active_edge_servers) < max_edge_servers)) #and 
                   # player_count_on_servers[srv] + 1 >= min_players_per_edge_server)
            ]

            # Assign to a new server if there are valid targets
            if potential_targets:
                new_server = default_random.choice(potential_targets)
                mutated_chromosome[player_idx] = new_server

                # Update player counts and active edge servers
                player_count_on_servers[current_server] -= 1
                player_count_on_servers[new_server] += 1
                if new_server in edge_servers:
                    active_edge_servers.add(new_server)
                if current_server in edge_servers and player_count_on_servers[current_server] < min_players_per_edge_server:
                    active_edge_servers.discard(current_server)

    return mutated_chromosome


def mutate_players(network, chromosome, mutation_rate, servers):
    #TODO: this function might be broken since the addition of individual player addition and removal
    mutated_chromosome = chromosome.copy()
    for player, server in enumerate(mutated_chromosome):
        if default_random.random() < mutation_rate:
            if player != -1:
                potential_server = default_random.choice(servers)
                if network.get_shortest_path_delay(f'P{int(player)+1}', potential_server) < network.get_shortest_path_delay(f'P{int(player)+1}', server):
                    player = potential_server

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
            child1 = enforce_max_server_occurrences(network, child1, max_server_nr)
            child1 = enforce_min_max_players_per_server(network, child1, max_connected_players, min_connected_players)
            child2 = enforce_max_server_occurrences(network, child2, max_server_nr)
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
                                                child1 = enforce_min_max_players_per_server(enforce_max_server_occurrences(network, child1, max_server_nr), max_connected_players, min_connected_players)
                                                child2 = enforce_min_max_players_per_server(enforce_max_server_occurrences(network, child2, max_server_nr), max_connected_players, min_connected_players)
                                                offspring.extend([child1, child2])

                                            population = parents + offspring

                                        all_fitness_histories.append(fitness_history)

                                    mean_fitness = np.mean(all_fitness_histories, axis=0)
                                    stderr_fitness = sem(all_fitness_histories, axis=0)
                                    results[param_key][key] = {'mean': mean_fitness, 'stderr': stderr_fitness}

    plot_fitness_comparison(results, generations)


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