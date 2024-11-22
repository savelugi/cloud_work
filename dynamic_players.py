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

TOTAL_TICK_COUNT = 50

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

INITIAL_PLAYER_NUMBER = 40
NR_OF_GAME_SERVERS = 5
MIN_PLAYERS_ON_SERVER = 4
MAX_PLAYERS_ON_SERVER = 16
MAX_ALLOWED_DELAY = 20

network = NetworkGraph(modelname='ilp_sum', config=config, num_gen_players=INITIAL_PLAYER_NUMBER)
tick = 0
default_random = random.Random()
write_dynamic_csv_header(csv_path)

logger.log("Dynamic player simulation started", print_to_console=True)

for tick in range(TOTAL_TICK_COUNT):
    csv_list = []
    tick += 1
    ILP_has_run = False

    if default_random.random() < 0.5:
        counter  = 0
        logger.log(f"T{tick}: Adding random players to the network graph!")
        for i in range(len(network.players)):
            if default_random.random() < 0.1:
                network.add_random_player_to_graph()
                counter += 1

        logger.log(f"Player addition has finished, added {counter} players, the total number of players in the network: {len(network.players)}")

    if default_random.random() < 0.3:
        counter = 0
        logger.log(f"T{tick}: Removing random players from the network graph!")
        for i in range(len(network.players)):
            if default_random.random() < 0.1:
                network.remove_player_from_graph(f'P{default_random.randrange(1, len(network.players))}')
                counter += 1

        logger.log(f"Player removal has finished, removed {counter} players, the total number of players in the network: {len(network.players)}")

    if default_random.random() < 0.5:
        counter = 0
        logger.log(f"T{tick}: Moving random players!")
        if len(network.players) > 1:
            for i in range(1, len(network.players)):
                #debug prints can be toggled with the debug_prints argument (warning can flood logs when player count is high)
                network.move_player_diagonally(f'P{default_random.randrange(1, len(network.players))}', 0.1)
                counter += 1

        logger.log(f"Player moving has finished, moved {counter} players!")

    # Dynamically increasing game server numbers if needed
    if len(network.players) > NR_OF_GAME_SERVERS * MAX_PLAYERS_ON_SERVER:
        NR_OF_GAME_SERVERS += 1

    if tick % 10 == 0 or tick == 1:

        sum_delay_optimization(
        #interplayer_delay_optimization(
            network=network, 
            server_positions=network.server_positions,
            players=network.players, 
            nr_of_servers=NR_OF_GAME_SERVERS,
            min_players_connected=MIN_PLAYERS_ON_SERVER, 
            max_connected_players = MAX_PLAYERS_ON_SERVER,
            max_allowed_delay=MAX_ALLOWED_DELAY,
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
        for i in range (0, 6):
            csv_list.append(network.delay_metrics[i])
        csv_list.append(network.delay_metrics[7])
        write_csv_row(csv_path, csv_list)

        #network.append(round(timer.get_elapsed_time()))

        network.color_graph()
        network.draw_graph(title=str(tick).zfill(4) + '_' + 'Gurobi', save=True, save_dir=save_path)

        ILP_has_run = True

    if tick % 5 == 0 and not ILP_has_run:
        logger.log('--------------------------------------------------------------')
        logger.log(f"T{tick}: Genetic algorithm started")
        network.clear_game_servers()
        initial_chromosome = convert_ILP_to_chromosome(network.server_to_player_delays)
        prev_chromosome = initial_chromosome

        population_size = 100
        population = chromosome_to_uniform_population(initial_chromosome, population_size)

        generations = 1000
        for iter in range(int(generations)):
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

                child1 = enforce_max_server_occurrences(child1, NR_OF_GAME_SERVERS)
                child1 = enforce_min_max_players_per_server(network, child1, MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER, migrate_to_edge_servers=True)

                child2 = enforce_max_server_occurrences(child2, NR_OF_GAME_SERVERS)
                child2 = enforce_min_max_players_per_server(network, child2, MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER, migrate_to_edge_servers=True)

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
        for i in range (0, 6):
            csv_list.append(network.delay_metrics[i])
        csv_list.append(network.delay_metrics[7])
        write_csv_row(csv_path, csv_list)

        network.color_graph()     
        network.draw_graph(title=str(tick).zfill(4) + '_' + "Heuristic", save=True, save_dir=save_path)

#network.display_plots()
generate_GIF(save_path)

logger.log("Simulation completed successfully.", print_to_console=True)