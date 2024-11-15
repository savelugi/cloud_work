import os
from utils import *
from network_graph import *
from visualization import *
from gurobi import *
from datetime import datetime
from mutation import *
import globvars
from globvars import logger

TOTAL_TICK_COUNT = 30

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

debug_prints, optimize, save, plot, active_models = get_toggles_from_config(config)
param_combinations = read_parameters_from_config(config)
num_players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay = param_combinations[0]

network = NetworkGraph(modelname='ilp_sum', config=config, num_gen_players=num_players)
tick = 0
default_random = random.Random()
write_dynamic_csv_header(csv_path)

logger.log("Dynamic player simulation started")

for tick in range(TOTAL_TICK_COUNT):
    csv_list = []
    tick += 1
    ILP_has_run = False

    if default_random.random() < 0.1:
        for i in range(len(network.players)):
            if default_random.random() < 0.1:
                network.add_random_player_to_graph()

    if default_random.random() < 0.2:
        for i in range(len(network.players)):
            if default_random.random() < 0.1:
                network.remove_player_from_graph(f'P{default_random.randrange(1, len(network.players))}')

    if default_random.random() < 0.5:
        if len(network.players) > 1:
            for i in range(1, len(network.players)):
                network.move_player_diagonally(f'P{default_random.randrange(1, len(network.players))}', 0.1)
       
    if tick % 10 == 0 or tick == 1:

        sum_delay_optimization(
            network=network, 
            server_positions=network.server_positions,
            players=network.players, 
            nr_of_servers=nr_of_servers,
            min_players_connected=min_players_connected, 
            max_connected_players=max_connected_players,              
            max_allowed_delay=max_allowed_delay,
            debug_prints=debug_prints)

        network.calculate_delays(method_type="sum_delay", debug_prints=debug_prints)
        network.calculate_qoe_metrics()
        csv_list.append(tick)
        csv_list.append('ILP')
        csv_list.append(len(network.players))
        csv_list.append(network.delay_metrics[6])
        csv_list.append(network.calculate_player_migrations())
        csv_list.append(network.calculate_server_migrations())
        csv_list.append(globvars.move_counter)
        globvars.move_counter = 0
        for i in range (0, 5):
            csv_list.append(network.delay_metrics[i])
        
        write_csv_row(csv_path, csv_list)

        #network.append(round(timer.get_elapsed_time()))

        network.color_graph()
        network.draw_graph(title=str(tick).zfill(4) + '_' + 'Gurobi', save=True, save_dir=save_path)

        ILP_has_run = True

    if tick % 5 == 0 and not ILP_has_run:
        logger.log('--------------------------------------------------------------')
        logger.log("Genetic algorithm started")
        network.clear_game_servers()
        initial_chromosome = convert_ILP_to_chromosome(network.server_to_player_delays)
        prev_chromosome = initial_chromosome

        population_size = 100
        population = chromosome_to_uniform_population(initial_chromosome, population_size)

        generations = 1000
        for _ in range(int(generations)):
            fitness_method='sum'
            fitness_values = [fitness(network, tuple(chromosome), fitness_method, prev_chromosome=tuple(prev_chromosome)) for chromosome in population]
            
            sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])  
            best_solution = sorted_pop[0]
            prev_chromosome = best_solution
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

                child1 = enforce_max_server_occurrences(child1, max_server_nr)
                child1 = enforce_min_max_players_per_server(network, child1, max_connected_players, min_connected_players, migrate_to_edge_servers=True)

                child2 = enforce_max_server_occurrences(child2, max_server_nr)
                child2 = enforce_min_max_players_per_server(network, child2, max_connected_players, min_connected_players, migrate_to_edge_servers=True)

                offspring.extend([child1, child2])

            population = parents + offspring

        sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])  
        best_solution = sorted_pop[0]
        logger.log('Genetic algorithm has found a solution with a fitness of ' + str(best_fitness))

        network.set_player_server_metrics(best_solution)
        network.calculate_delays("Genetic algorithm", debug_prints=True)
        network.calculate_qoe_metrics()

        csv_list.append(tick)
        csv_list.append('GEN')
        csv_list.append(len(network.players))
        csv_list.append(network.delay_metrics[6])
        csv_list.append(network.calculate_player_migrations())
        csv_list.append(network.calculate_server_migrations())
        csv_list.append(globvars.move_counter)
        globvars.move_counter = 0
        for i in range (0, 5):
            csv_list.append(network.delay_metrics[i])
        write_csv_row(csv_path, csv_list)

        network.color_graph()     
        network.draw_graph(title=str(tick).zfill(4) + '_' + "Heuristic", save=True, save_dir=save_path)

#network.display_plots()
generate_GIF(save_path)

logger.log("Simulation complete.")