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

TOTAL_TICK_COUNT = 80

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
MIGRATION_COST = 0.1

ADDING_PLAYERS = False
REMOVING_PLAYERS = False
MOVING_PLAYERS = True
GEN_OPT = False
GUROBI_OPT = True

network = NetworkGraph(modelname='ilp_sum', config=config, num_gen_players=INITIAL_PLAYER_NUMBER)
tick = 0
last_pop = []
write_dynamic_csv_header(csv_path)

logger.log("Dynamic player simulation started", print_to_console=True)
logger.log("Initial parameters:")
logger.log(f"INITIAL_PLAYER_NUMBER={INITIAL_PLAYER_NUMBER}")
logger.log(f"NR_OF_GAME_SERVERS={NR_OF_GAME_SERVERS}")
logger.log(f"MIN_PLAYERS_ON_SERVER={MIN_PLAYERS_ON_SERVER}")
logger.log(f"MAX_PLAYERS_ON_SERVER={MAX_PLAYERS_ON_SERVER}")
logger.log(f"MIGRATION_COST={MIGRATION_COST}")
logger.log(f"ADDING_PLAYERS={ADDING_PLAYERS}")
logger.log(f"REMOVING_PLAYERS={REMOVING_PLAYERS}")
logger.log(f"MOVING_PLAYERS={MOVING_PLAYERS}")

timer = Timer()

for tick in range(TOTAL_TICK_COUNT):
    default_random = random.Random()
    logger.log('--------------------------------------------------------------')
    csv_list = []
    tick += 1
    ILP_has_run = False
    GEN_has_run = False
    added_players = False
    removed_players = False

    logger.log(f"TICK:{tick}")

    if ADDING_PLAYERS and default_random.random() < 0.5:
        counter  = 0
        logger.log(f"T{tick}: Adding random players to the network graph!")
        for i in range(len(network.players)):
            if default_random.random() < 0.1:
                network.add_random_player_to_graph()
                counter += 1

        logger.log(f"Player addition has finished, added {counter} players, the total number of players in the network: {len(network.players)}")
        added_players = True

    if REMOVING_PLAYERS and default_random.random() < 0.3:
        counter = 0
        logger.log(f"T{tick}: Removing random players from the network graph!")
        for i in range(len(network.players)):
            if default_random.random() < 0.1:
                network.remove_player_from_graph(f'P{default_random.randrange(0, len(network.players)+1)}')
                counter += 1

        logger.log(f"Player removal has finished, removed {counter} players, the total number of players in the network: {len(network.players)}")
        removed_players = True

    if MOVING_PLAYERS and tick in range(2,21):
        counter = 0
        logger.log(f"T{tick}: Moving players!")
        if len(network.players) > 1:
            for player in ['P1', 'P7', 'P11', 'P13']: #, 'P28', 'P37', 'P45', 'P99', 'P100'
                #debug prints can be toggled with the debug_prints argument (warning can flood logs when player count is high)
                network.move_player_vertically(player,-0.9,debug_prints=True)
                counter += 1

        logger.log(f"Player moving has finished, moved {counter} players!")

    if MOVING_PLAYERS and tick in range(21,41):
        counter = 0
        logger.log(f"T{tick}: Moving players!")
        if len(network.players) > 1:
            for player in ['P1', 'P7', 'P11', 'P13']:
                #debug prints can be toggled with the debug_prints argument (warning can flood logs when player count is high)
                network.move_player_horizontally(player,2.2,debug_prints=True)
                counter += 1

        logger.log(f"Player moving has finished, moved {counter} players!")

    if MOVING_PLAYERS and tick in range(41,61):
        counter = 0
        logger.log(f"T{tick}: Moving players!")
        if len(network.players) > 1:
            for player in ['P1', 'P7', 'P11', 'P13']:
                #debug prints can be toggled with the debug_prints argument (warning can flood logs when player count is high)
                network.move_player_vertically(player,0.75,debug_prints=True)
                counter += 1

        logger.log(f"Player moving has finished, moved {counter} players!")

    if MOVING_PLAYERS and tick in range(61,81):
        counter = 0
        logger.log(f"T{tick}: Moving players!")
        if len(network.players) > 1:
            for player in ['P1', 'P7', 'P11', 'P13']:
                #debug prints can be toggled with the debug_prints argument (warning can flood logs when player count is high)
                network.move_player_horizontally(player,-2.2,debug_prints=True)
                counter += 1

        logger.log(f"Player moving has finished, moved {counter} players!")

    # Dynamically increasing game server numbers if needed
    if ADDING_PLAYERS or REMOVING_PLAYERS:
        if len(network.players) > NR_OF_GAME_SERVERS * MAX_PLAYERS_ON_SERVER:
            NR_OF_GAME_SERVERS += 1
            logger.log(f"Number of game servers increased to: {NR_OF_GAME_SERVERS}")

    # #TODO: check this: Dynamically turning servers off if there are too many
    # if math.ceil(len(network.players) / MAX_PLAYERS_ON_SERVER) < NR_OF_GAME_SERVERS:
    #     NR_OF_GAME_SERVERS -= 1
    #     logger.log(f"Number of game servers decreased to: {NR_OF_GAME_SERVERS}")

        if NR_OF_GAME_SERVERS > 5:
            MAX_EDGE_SERVERS = math.ceil(NR_OF_GAME_SERVERS * 0.7)
            logger.log(f"Number of maximum edge servers:{MAX_EDGE_SERVERS}")
            MAX_CORE_SERVERS = NR_OF_GAME_SERVERS - MAX_EDGE_SERVERS
            logger.log(f"Number of maximum core servers:{MAX_CORE_SERVERS}")


    if GUROBI_OPT and tick == 1:
        qoe_optimization = QoEOptimizationInitial(
            network=network,
            potential_servers=network.core_servers,
            players=network.players,
            nr_of_game_servers=MAX_CORE_SERVERS,
            min_players_connected=MIN_PLAYERS_ON_SERVER,
            max_connected_players=MAX_PLAYERS_ON_SERVER,
            debug_prints=False
        )

        delaysum_optimization = DelaySumInitialOptimization(
            network=network,
            potential_servers=network.core_servers,
            players=network.players,
            nr_of_game_servers=MAX_CORE_SERVERS,
            min_players_connected=MIN_PLAYERS_ON_SERVER,
            max_connected_players=MAX_PLAYERS_ON_SERVER,
            debug_prints=False 
        )

        interplayer_delay_optimization = InterplayerDelayInitialOptimization(
            network=network,
            potential_servers=network.core_servers,
            players=network.players,
            nr_of_game_servers=MAX_CORE_SERVERS,
            min_players_connected=MIN_PLAYERS_ON_SERVER,
            max_connected_players=MAX_PLAYERS_ON_SERVER,
            debug_prints=False
        )

        timer.start()
        success = interplayer_delay_optimization.solve()
        timer.stop()

        network.calculate_delays(method_type="", debug_prints=debug_prints)
        network.calculate_QoE_metrics()
        csv_list.append(tick)
        csv_list.append('ILP')
        csv_list.append(len(network.players))
        csv_list.append(network.delay_metrics[6])
        csv_list.append(network.calculate_player_migrations())
        csv_list.append(network.calculate_total_player_migration_cost(MIGRATION_COST))
        csv_list.append(network.calculate_server_migrations())
        
        csv_list.append(globvars.move_counter)
        globvars.move_counter = 0
        for i in range (0, 6):
            csv_list.append(network.delay_metrics[i])
        csv_list.append(network.delay_metrics[7])
        csv_list.append(round(timer.get_elapsed_time()))
        csv_list.append(MIGRATION_COST)
        write_csv_row(csv_path, csv_list)


        network.color_graph()
        network.draw_graph(title=str(tick).zfill(4) + '_' + 'Gurobi' + '_' + f"{len(network.players)}_{NR_OF_GAME_SERVERS}_{len(network.selected_core_servers)}_{len(network.selected_edge_servers)}", save=True, save_dir=save_path)

        ILP_has_run = True

    if GEN_OPT and tick % 5 == 0 and not ILP_has_run or (GEN_OPT and tick == 1):
        logger.log(f"T{tick}: Genetic algorithm started", print_to_console=True)
        network.clear_game_servers()
        #initial_chromosome = convert_ILP_to_chromosome(network.server_to_player_delays)
        #prev_chromosome = initial_chromosome

        population_size = 100
        #population = chromosome_to_uniform_population(initial_chromosome, population_size)
        if tick == 1:
            population = initial_population(network.players, network._only_servers, population_size)
        else:
            population = last_pop

        generations = 6000
        timer.start()
        for iter in range(int(generations)):
            fitness_method='sum'
            #fitness_values = [fitness(network, tuple(chromosome), fitness_method, prev_chromosome=tuple(prev_chromosome)) for chromosome in population]
            if tick == 1:
                fitness_values = [fitness_ipd(
                                    network,
                                    tuple(chromosome),
                                    max_core_server_nr=MAX_CORE_SERVERS,
                                    max_edge_server_nr=MAX_EDGE_SERVERS,
                                    max_connected_players=MAX_PLAYERS_ON_SERVER,
                                    min_connected_players=MIN_PLAYERS_ON_SERVER,
                                    initial=True)
                                    for chromosome in population]            

            else:
                fitness_values = [fitness_ipd(
                                    network,
                                    tuple(chromosome),
                                    max_core_server_nr=MAX_CORE_SERVERS,
                                    max_edge_server_nr=MAX_EDGE_SERVERS,
                                    max_connected_players=MAX_PLAYERS_ON_SERVER,
                                    min_connected_players=MIN_PLAYERS_ON_SERVER,
                                    initial=False)
                                    for chromosome in population]            
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
                # child1 = mutate_to_edge_servers(network, child1, mutation_rate, max_core_servers=MAX_CORE_SERVERS, max_edge_servers=MAX_EDGE_SERVERS)
                # child2 = mutate_to_edge_servers(network, child2, mutation_rate, max_core_servers=MAX_CORE_SERVERS, max_edge_servers=MAX_EDGE_SERVERS)

                #child1 = enforce_max_server_occurrences(network, child1, MAX_CORE_SERVERS, MAX_EDGE_SERVERS)
                #child1 = enforce_min_max_players_per_server(network, child1, MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER, migrate_to_edge_servers=True)

                #child2 = enforce_max_server_occurrences(network,child2, MAX_CORE_SERVERS, MAX_EDGE_SERVERS)
                #child2 = enforce_min_max_players_per_server(network, child2, MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER, migrate_to_edge_servers=True)
                #child1 = mutate_to_edge_servers(network, child1, mutation_rate, max_edge_servers=MAX_EDGE_SERVERS, max_players_per_edge_server=MAX_PLAYERS_ON_SERVER, min_players_per_core_server=MIN_PLAYERS_ON_SERVER, min_players_per_edge_server=MIN_PLAYERS_ON_SERVER)
                #child2 = mutate_to_edge_servers(network, child2, mutation_rate, max_edge_servers=MAX_EDGE_SERVERS, max_players_per_edge_server=MAX_PLAYERS_ON_SERVER, min_players_per_core_server=MIN_PLAYERS_ON_SERVER, min_players_per_edge_server=MIN_PLAYERS_ON_SERVER)
                if tick == 1:
                    child1 = mutate_random_edges(network, child1, mutation_rate, max_edge_servers=MAX_EDGE_SERVERS, initial=True)
                    child2 = mutate_random_edges(network, child2, mutation_rate, max_edge_servers=MAX_EDGE_SERVERS, initial=True)
                else:
                    child1 = mutate_random_edges(network, child1, mutation_rate, max_edge_servers=MAX_EDGE_SERVERS, initial=False)
                    child2 = mutate_random_edges(network, child2, mutation_rate, max_edge_servers=MAX_EDGE_SERVERS, initial=False)
                # child1 = enforce_min_max_players_per_server(network, child1, MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER)
                # child1 = enforce_min_max_players_per_server(network, child2, MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER)


                offspring.extend([child1, child2])

            population = parents + offspring

        sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])
        last_pop = sorted_pop.copy()
        best_solution = sorted_pop[0]
        timer.stop()
        logger.log('Genetic algorithm has found a solution with a fitness of ' + str(best_fitness), print_to_console=True)

        network.set_player_server_metrics(best_solution)
        network.calculate_delays("Genetic algorithm", debug_prints=True)
        network.calculate_QoE_metrics()

        csv_list.append(tick)
        csv_list.append('GEN')
        csv_list.append(len(network.players))
        csv_list.append(network.delay_metrics[6])
        csv_list.append(network.calculate_player_migrations())
        csv_list.append(network.calculate_total_player_migration_cost(MIGRATION_COST))
        csv_list.append(network.calculate_server_migrations())
        csv_list.append(globvars.move_counter)
        globvars.move_counter = 0
        for i in range (0, 6):
            csv_list.append(network.delay_metrics[i])
        csv_list.append(network.delay_metrics[7])
        csv_list.append(round(timer.get_elapsed_time()))
        write_csv_row(csv_path, csv_list)

        network.color_graph()     
        network.draw_graph(title=str(tick).zfill(4) + '_' + "Heuristic" + '_' + f"{len(network.players)}_{NR_OF_GAME_SERVERS}_{len(network.selected_core_servers)}_{len(network.selected_edge_servers)}", save=True, save_dir=save_path)
        
        GEN_has_run = True
    
    if GUROBI_OPT and tick % 5 == 0 and not ILP_has_run:
        qoe_optimization_migration = QoEOptimizationMigration(
            network=network,
            fix_servers=network.selected_core_servers,
            dynamic_servers=network.edge_servers,
            players=network.players,
            nr_of_game_servers=len(network.selected_core_servers)+MAX_EDGE_SERVERS,
            min_players_connected=MIN_PLAYERS_ON_SERVER,
            max_connected_players = MAX_PLAYERS_ON_SERVER,
            migration_cost=MIGRATION_COST,
            debug_prints=False
        )

        delaysum_optimization_migration = DelaySumMigrationOptimization(
            network=network,
            fix_servers=network.selected_core_servers,
            dynamic_servers=network.edge_servers,
            players=network.players,
            nr_of_game_servers=len(network.selected_core_servers)+MAX_EDGE_SERVERS,
            min_players_connected=MIN_PLAYERS_ON_SERVER,
            max_connected_players = MAX_PLAYERS_ON_SERVER,
            migration_cost=MIGRATION_COST,
            debug_prints=False
        )

        interplayer_delay_optimization_migration = InterplayerDelayMigrationOptimization(
            network=network,
            fix_servers=network.selected_core_servers,
            dynamic_servers=network.edge_servers,
            players=network.players,
            nr_of_game_servers=len(network.selected_core_servers)+MAX_EDGE_SERVERS,
            min_players_connected=MIN_PLAYERS_ON_SERVER,
            max_connected_players = MAX_PLAYERS_ON_SERVER,
            migration_cost=MIGRATION_COST,
            debug_prints=False  
        )

        timer.start()
        success = interplayer_delay_optimization_migration.solve()
        timer.stop()

        network.calculate_delays(method_type="sum_delay", debug_prints=debug_prints)
        network.calculate_QoE_metrics()
        csv_list.append(tick)
        csv_list.append('ILP')
        csv_list.append(len(network.players))
        csv_list.append(network.delay_metrics[6])
        csv_list.append(network.calculate_player_migrations())
        csv_list.append(network.calculate_total_player_migration_cost(MIGRATION_COST))
        csv_list.append(network.calculate_server_migrations())
        csv_list.append(globvars.move_counter)
        globvars.move_counter = 0
        for i in range (0, 6):
            csv_list.append(network.delay_metrics[i])
        csv_list.append(network.delay_metrics[7])
        csv_list.append(round(timer.get_elapsed_time()))
        csv_list.append(MIGRATION_COST)
        write_csv_row(csv_path, csv_list)
        network.color_graph()
        network.draw_graph(title=str(tick).zfill(4) + '_' + 'Gurobi mig' + '_' + f"{len(network.players)}_{NR_OF_GAME_SERVERS}_{len(network.selected_core_servers)}_{len(network.selected_edge_servers)}", save=True, save_dir=save_path)
        ILP_has_run = True

    if(tick > 1 and not ILP_has_run and not GEN_has_run):
        network.calculate_delays(method_type="update", debug_prints=debug_prints)
        network.calculate_QoE_metrics()
        csv_list.append(tick)
        csv_list.append('***')
        csv_list.append(len(network.players))
        csv_list.append(network.delay_metrics[6])
        csv_list.append(network.calculate_player_migrations())
        csv_list.append(network.calculate_total_player_migration_cost(MIGRATION_COST))
        csv_list.append(network.calculate_server_migrations())
        csv_list.append(globvars.move_counter)
        globvars.move_counter = 0
        for i in range (0, 6):
            csv_list.append(network.delay_metrics[i])
        csv_list.append(network.delay_metrics[7])
        csv_list.append(round(timer.get_elapsed_time()))
        csv_list.append(MIGRATION_COST)
        write_csv_row(csv_path, csv_list)


#network.display_plots()
generate_GIF(save_path)

logger.log("Simulation completed successfully.", print_to_console=True)