import os
from utils import *
from network_graph import *
from visualization import *
from gurobi import *
from datetime import datetime
from mutation import *

dir_path = os.path.dirname(os.path.realpath(__file__))
save_dir = os.path.join(dir_path, "saves/")
config_file = os.path.join(dir_path, "config.ini")
config = read_configuration(config_file)

#seed_value = 42

debug_prints, optimize, save, plot, active_models = get_toggles_from_config(config)
param_combinations = read_parameters_from_config(config)
topology = config['Topology']['topology']
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Get current timestamp

num_players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay = param_combinations[0]
network = NetworkGraph(modelname='ilp_sum', config=config, num_gen_players=num_players)

sum_delay_optimization(
                network=network, 
                server_positions=network.server_positions,
                players=network.players, 
                nr_of_servers=nr_of_servers,
                min_players_connected=min_players_connected, 
                max_connected_players=max_connected_players,              
                max_allowed_delay=max_allowed_delay,
                debug_prints=debug_prints)

network.calculate_delays(method_type='', debug_prints=debug_prints)  

network.color_graph()

network.get_closest_servers('3')
#network.migrate_edge_servers_if_beneficial("P1")
#print
network.draw_graph(title="Graf")

#move
for i in range(120):
    #for i in range(num_players):
    i = 1
    network.move_player_diagonally(f'P{i+1}', dist=-1, debug_prints=False)

network.remove_player_from_graph("P1", debug_prints=True)

initial_chromosome = convert_ILP_to_chromosome(network.server_to_player_delays)

population_size = 100
population = chromosome_to_uniform_population(initial_chromosome, population_size)

network.clear_game_servers()

generations = 500
for _ in range(int(generations)):
    fitness_method='sum'
    fitness_values = [fitness(network, tuple(chromosome), fitness_method) for chromosome in population]
    
    sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])  
    best_solution = sorted_pop[0]
    best_fitness = fitness_values[population.index(best_solution)]

    selection_strategy = 'rank_based'
    tournament_size = '5'
    parents = selection(population, fitness_values, selection_strategy, tournament_size)
    offspring = []
    while len(offspring) < population_size - len(parents):
        parent1, parent2 = default_random.sample(parents, 2)
        crossover_method = 'single_point'
        child1, child2 = crossover(parent1, parent2, method=crossover_method)
        mutatiod_method = 'mut_servers'
        mutation_rate = 0.1
        child1 = mutate_edge_servers(network, child1, mutation_rate)
        child2 = mutate_edge_servers(network, child2, mutation_rate)

        # Enforce boundaries
        max_server_nr = 3
        max_connected_players = 24
        min_connected_players = 4

        child1 = enforce_max_server_occurrences(network, child1, max_server_nr)
        child1 = enforce_min_max_players_per_server(network, child1, max_connected_players, min_connected_players, migrate_to_edge_servers=True)

        child2 = enforce_max_server_occurrences(network, child2, max_server_nr)
        child2 = enforce_min_max_players_per_server(network, child2, max_connected_players, min_connected_players, migrate_to_edge_servers=True)

        offspring.extend([child1, child2])

    population = parents + offspring

sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])  
best_solution = sorted_pop[0]

network.set_player_server_metrics(best_solution)

network.color_graph()
        
#print again
network.draw_graph(title="Graf")


network.display_plots()

print("end")