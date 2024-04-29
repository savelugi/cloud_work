import numpy as np
import pygad
from network_graph import NetworkGraph
import networkx as nx
import random
from utils import *
from network_graph import *
from visualization import *
from gurobi import *


#usa, germany, cost
topology = "cost"

config_file = r"C:\Users\bbenc\OneDrive\Documents\aGraph\cloud_work\config.ini"
config = read_configuration(config_file)

topology_file = get_topology_filename(topology, config)
save_dir = get_save_dir(config)
seed_value = 42

debug_prints, optimize, save, plot, sum_model, ipd_model, gen_model = get_toggles_from_config(config)

# Adding server nodes
network = NetworkGraph()
network.load_topology(topology_file)

# Getting server positions
servers = list(network.graph.nodes)
server_positions = network.get_server_positions()


long_range, lat_range = get_lat_long_range(topology)
num_players = 30

players = generate_players(num_players, long_range, lat_range, seed_value)
network.add_players(players)



for player in players:
            network.connect_player_to_server(players, player, server_positions)

players = list(players)



# Defining the fitness function
def fitness_function(solution, players, network):
    delay = 0
    for i, server in enumerate(solution):
        player = players[i]
        delay += network.get_shortest_path_delay(server, player)
    return delay

# Create an instance of the pygad.GA class
ga_instance = pygad.GA(num_generations=100,
                       num_parents_mating=50,
                       fitness_func=fitness_function,
                       sol_per_pop=100,
                       num_genes=num_players,
                       init_range_low=0,
                       init_range_high=len(servers)-1,
                       gene_type=int,
                       mutation_percent_genes=10,
                       parent_selection_type="rank",
                       crossover_type="single_point",
                       mutation_type="random")

# Running the Genetic Algorithm
ga_instance.run()

# Getting the best solution after running the GA
solution, solution_fitness = ga_instance.best_solution()

# Printing the optimized solution
print("Best solution found:")
print(solution)
print("Fitness value of the best solution:")
print(solution_fitness)
