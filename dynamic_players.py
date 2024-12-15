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

TOTAL_TICK_COUNT = 500

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
logger.set_log_level("INFO")

debug_prints = True
INITIAL_PLAYER_NUMBER = 96
network = NetworkGraph(modelname='ilp_ipd', config=config, num_gen_players=INITIAL_PLAYER_NUMBER)
NR_OF_GAME_SERVERS = 3
#NR_OF_GAME_SERVERS = len(network._only_servers)
MIN_PLAYERS_ON_SERVER = 4
MAX_PLAYERS_ON_SERVER = 16
MAX_EDGE_SERVERS = 2
#MAX_EDGE_SERVERS = len(network.edge_servers)
MAX_CORE_SERVERS = 2
#MAX_CORE_SERVERS = len(network.core_servers)
MIGRATION_COST = 0.2

CIRCULAR_MOVEMENT = False
DAYNIGHTCYCLE = False
ADDING_PLAYERS = False
REMOVING_PLAYERS = False
MOVING_PLAYERS = True
GEN_OPT = True
GUROBI_OPT = False

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
bigtimer = Timer()
bigtimersum = 0
fitnesstimer = Timer()
fitnesstimersum = 0
whiletimer = Timer()
whiletimersum = 0
timerone = Timer()
timeronesum = 0
timertwo = Timer()
timertwosum = 0
timerthree = Timer()
timerthreesum = 0
added_players = False
removed_players = False

players_to_remove = []
last_optimized_delay = None
last_optimized_player_count = len(network.players)

for tick in range(TOTAL_TICK_COUNT):
    default_random = random.Random()
    logger.log('--------------------------------------------------------------')
    csv_list = []
    tick += 1
    ILP_has_run = False
    GEN_has_run = False

    logger.log(f"TICK:{tick}")

    if ADDING_PLAYERS and default_random.random() < 0.5 and tick > 1:
        counter  = 0
        logger.log(f"T{tick}: Adding random players to the network graph!")
        #for i in range(len(network.players)):
        for i in range(101):
            #if default_random.random() < 0.4:
            network.add_random_player_to_graph()
            counter += 1

        logger.log(f"Player addition has finished, added {counter} players, the total number of players in the network: {len(network.players)}")
        added_players = True

    if REMOVING_PLAYERS and default_random.random() < 0.3:
        counter = 0
        logger.log(f"T{tick}: Removing random players from the network graph!")
        #for i in range(len(network.players)):
        for i in range(51):
            #if default_random.random() < 0.2:
            network.remove_player_from_graph(f'P{default_random.randrange(0, len(network.players)+1)}')
            counter += 1

        logger.log(f"Player removal has finished, removed {counter} players, the total number of players in the network: {len(network.players)}")
        removed_players = True
    
    # for circular movement simulation
    if CIRCULAR_MOVEMENT:
        if MOVING_PLAYERS and tick in range(2,21):
            counter = 0
            logger.log(f"T{tick}: Moving players!")
            if len(network.players) > 1:
                for player in ['P1', 'P7', 'P11', 'P13', 'P28', 'P37', 'P45', 'P99', 'P100']: #, 'P28', 'P37', 'P45', 'P99', 'P100'
                    #debug prints can be toggled with the debug_prints argument (warning can flood logs when player count is high)
                    network.move_player_vertically(player,-0.9,debug_prints=True)
                    counter += 1

            logger.log(f"Player moving has finished, moved {counter} players!")

        if MOVING_PLAYERS and tick in range(21,41):
            counter = 0
            logger.log(f"T{tick}: Moving players!")
            if len(network.players) > 1:
                for player in ['P1', 'P7', 'P11', 'P13', 'P28', 'P37', 'P45', 'P99', 'P100']:
                    #debug prints can be toggled with the debug_prints argument (warning can flood logs when player count is high)
                    network.move_player_horizontally(player,2.2,debug_prints=True)
                    counter += 1

            logger.log(f"Player moving has finished, moved {counter} players!")

        if MOVING_PLAYERS and tick in range(41,61):
            counter = 0
            logger.log(f"T{tick}: Moving players!")
            if len(network.players) > 1:
                for player in ['P1', 'P7', 'P11', 'P13', 'P28', 'P37', 'P45', 'P99', 'P100']:
                    #debug prints can be toggled with the debug_prints argument (warning can flood logs when player count is high)
                    network.move_player_vertically(player,0.75,debug_prints=True)
                    counter += 1

            logger.log(f"Player moving has finished, moved {counter} players!")

        if MOVING_PLAYERS and tick in range(61,81):
            counter = 0
            logger.log(f"T{tick}: Moving players!")
            if len(network.players) > 1:
                for player in ['P1', 'P7', 'P11', 'P13', 'P28', 'P37', 'P45', 'P99', 'P100']:
                    #debug prints can be toggled with the debug_prints argument (warning can flood logs when player count is high)
                    network.move_player_horizontally(player,-2.2,debug_prints=True)
                    counter += 1

            logger.log(f"Player moving has finished, moved {counter} players!")

    # for whitenoise sim
    if MOVING_PLAYERS and tick > 1:
       network.move_players_white_noise(range_x=(network.lat_range[1]-network.lat_range[0])/20,range_y=(network.long_range[1]-network.long_range[0])/20,debug_prints=True)

    if DAYNIGHTCYCLE:
        scale = 1 # A skálázás a long_range és lat_range lépései között
        latitudes = list(range(network.long_range[0], network.long_range[1], scale))  # 5 db
        longitudes= list(range(network.lat_range[0], network.lat_range[1], scale))    # 11 db
        
        total_columns = len(longitudes)  # Összes oszlop száma 11
        ticks_per_column = int((TOTAL_TICK_COUNT * 0.75 ) // total_columns ) # Tickek oszloponként

        if tick % ticks_per_column == 0:
            if tick // ticks_per_column <= total_columns:
                current_column = tick // ticks_per_column  # Aktuális oszlop

                for latitude in latitudes:
                    longitude = longitudes[current_column - 1]  # Csak az aktuális oszlop longitudes értékeit használjuk
                    player = network.add_random_player_to_graph(longitude=longitude, latitude=latitude)
                    if player:
                        players_to_remove.append(player)
                        added_players = True

            # Játékos törlése a tickek második felében
            if tick > TOTAL_TICK_COUNT // 4:
                players_to_remove_per_tick = len(latitudes)
                for _ in range(players_to_remove_per_tick):
                    if players_to_remove:
                        player_to_remove = players_to_remove.pop(0)  # Az első játékos törlése a listából
                        network.remove_player_from_graph(player_to_remove)
                        logger.log(f"T{tick}: Removed player {player_to_remove}")
                        removed_players = True

    # Dynamically increasing or decreasing game server numbers if needed
    if ADDING_PLAYERS or REMOVING_PLAYERS or DAYNIGHTCYCLE:
        while len(network.players) > NR_OF_GAME_SERVERS * MAX_PLAYERS_ON_SERVER:
            NR_OF_GAME_SERVERS += 1
            if NR_OF_GAME_SERVERS > len(network._only_servers):
                raise ValueError("Too many players are trying to play")
        logger.log(f"Number of game servers increased to: {NR_OF_GAME_SERVERS}")

        #TODO: check this: Dynamically turning servers off if there are too many
        while math.ceil(len(network.players) / MAX_PLAYERS_ON_SERVER) < NR_OF_GAME_SERVERS:
            NR_OF_GAME_SERVERS -= 1
            logger.log(f"Number of game servers decreased to: {NR_OF_GAME_SERVERS}")

        # if NR_OF_GAME_SERVERS > 10:
        #     MAX_EDGE_SERVERS = math.ceil(NR_OF_GAME_SERVERS * 0.7)
        #     logger.log(f"Number of maximum edge servers:{MAX_EDGE_SERVERS}")
        #     MAX_CORE_SERVERS = NR_OF_GAME_SERVERS - MAX_EDGE_SERVERS
        #     logger.log(f"Number of maximum core servers:{MAX_CORE_SERVERS}")


    run_migration_due_to_threshold = False
    if last_optimized_delay is not None:
        current_delay = network.delay_metrics[0]
        if current_delay > 1.2 * last_optimized_delay:
            logger.log(f"Average delay increased by more than 20% since last optimization (from {last_optimized_delay} to {current_delay}). Running migration optimization.")
            run_migration_due_to_threshold = True
    run_migration_due_to_threshold = False

    current_player_count = len(network.players)
    run_migration_due_to_player_count_change = False
    if last_optimized_player_count is not None and last_optimized_player_count > 0:
        if (current_player_count > 1.1 * last_optimized_player_count) or (current_player_count < 0.9 * last_optimized_player_count):
            logger.log("Player count changed by more than 10% since last optimization. Will run optimization.")
            run_migration_due_to_player_count_change = True
    run_migration_due_to_player_count_change = False


    if GUROBI_OPT and tick == 1:
    #if GUROBI_OPT and tick:

        timer.start()
        # qoe_optimization = QoEOptimizationInitial(
        #     network=network,
        #     potential_servers=network._only_servers,
        #     players=network.players,
        #     nr_of_game_servers=NR_OF_GAME_SERVERS,
        #     min_players_connected=MIN_PLAYERS_ON_SERVER,
        #     max_connected_players=MAX_PLAYERS_ON_SERVER,
        #     debug_prints=True
        # )

        # delaysum_optimization = DelaySumInitialOptimization(
        #     network=network,
        #     potential_servers=network.core_servers,
        #     players=network.players,
        #     nr_of_game_servers=MAX_CORE_SERVERS,
        #     min_players_connected=MIN_PLAYERS_ON_SERVER,
        #     max_connected_players=MAX_PLAYERS_ON_SERVER,
        #     debug_prints=False 
        # )

        interplayer_delay_optimization = InterplayerDelayInitialOptimization(
            network=network,
            potential_servers=network.core_servers,
            players=network.players,
            nr_of_game_servers=NR_OF_GAME_SERVERS,
            min_players_connected=MIN_PLAYERS_ON_SERVER,
            max_connected_players=MAX_PLAYERS_ON_SERVER,
            debug_prints=True
        )

        
        success = interplayer_delay_optimization.solve()
        if success is False:
            raise ValueError("Optimization failed!")

        timer.stop()

        network.calculate_delays(method_type="", debug_prints=debug_prints)
        last_optimized_delay = network.delay_metrics[0]
        last_optimized_player_count = len(network.players)
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
        network.draw_graph(title=str(tick).zfill(4) + '_' + 'Gurobi' + '_' + f"{len(network.players)}_{NR_OF_GAME_SERVERS}_{len(network.selected_core_servers)}_{len(network.selected_edge_servers)}", figsize=(12,8), save=True, save_dir=save_path)

        ILP_has_run = True

    if (0 and GEN_OPT and tick % 10 == 0 and not ILP_has_run ) or tick == 1: #or run_migration_due_to_threshold or run_migration_due_to_player_count_change):
        logger.log(f"T{tick}: Genetic algorithm started", print_to_console=True)
        network.clear_game_servers()
        initial_chromosome = convert_ILP_to_chromosome(network.server_to_player_delays)
        prev_chromosome = initial_chromosome

        population_size = 250
        #if added_players or removed_players:
        # if tick == 10:
        #     population = chromosome_to_uniform_population(initial_chromosome, population_size)

            #population = initial_population(network.players, network._only_servers, population_size) 
        if tick == 1:
            population = initial_population(network.players, network._only_servers, population_size)
        else:
            population = last_pop

        generations = 1500
        timer.start()
        for iter in range(int(generations)):
            fitnesstimer.start()
            fitness_method='fitness'
            fitness_values = [fitness_ipd(
                                network,
                                tuple(chromosome),
                                max_core_server_nr=MAX_CORE_SERVERS,
                                max_edge_server_nr=MAX_EDGE_SERVERS,
                                max_connected_players=MAX_PLAYERS_ON_SERVER,
                                min_connected_players=MIN_PLAYERS_ON_SERVER,
                                generation=generations,
                                iteration=iter
                                )
                                for chromosome in population]
            fitnesstimer.stop()
            fitnesstimersum += fitnesstimer.get_elapsed_time()
            sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)], reverse=True if fitness_method=='fitness_qoe' else False)
            best_solution = sorted_pop[0]
            prev_chromosome = best_solution
            best_fitness = fitness_values[population.index(best_solution)]

            selection_strategy = 'rank_based'
            selection_strategy = 'tournament'
            tournament_size = '4'
            parents = selection(population, fitness_values, selection_strategy, tournament_size)
            
            whiletimer.start()
            offspring = []
            while len(offspring) < population_size - len(parents):
                parent1, parent2 = default_random.sample(parents, 2)
                crossover_method = 'single_point'
                crossover_method = 'uniform'
                child1, child2 = crossover(parent1, parent2, method=crossover_method)
                mutatiod_method = 'mut_servers'
                mutation_rate = 0.01
                timerone.start()
                child1 = mutate_random_edges(network, tuple(child1), mutation_rate, max_edge_servers=MAX_EDGE_SERVERS, initial=True if tick == 1 else False)
                child2 = mutate_random_edges(network, tuple(child2), mutation_rate, max_edge_servers=MAX_EDGE_SERVERS, initial=True if tick == 1 else False)
                #child1 = mutate_servers(network, child1, mutation_rate)
                #child2 = mutate_servers(network, child2, mutation_rate)
                # child1 = mutate_players(network, child1, mutation_rate, network._only_servers)
                # child2 = mutate_players(network, child2, mutation_rate, network._only_servers)
                timerone.stop()
                timeronesum += timerone.get_elapsed_time()
                
                timertwo.start()
                #this should be used when migrating edge servers
                child1 = enforce_max_server_occurrences(network=network, chromosome=tuple(child1), max_core_server=MAX_CORE_SERVERS if tick == 1 else MAX_CORE_SERVERS,
                                                         max_edge_server=MAX_EDGE_SERVERS, initial=True if tick == 1 else False)
                child2 = enforce_max_server_occurrences(network=network, chromosome=tuple(child2), max_core_server=MAX_CORE_SERVERS if tick == 1 else MAX_CORE_SERVERS,
                                                         max_edge_server=MAX_EDGE_SERVERS, initial=True if tick == 1 else False)
                # child1 = enforce_max_server_occurrencess(child1, NR_OF_GAME_SERVERS)
                # child2 = enforce_max_server_occurrencess(child2, NR_OF_GAME_SERVERS)
                timertwo.stop()
                timertwosum += timertwo.get_elapsed_time()
                
                timerthree.start()
                child1 = enforce_min_max_players_per_server(network, tuple(child1), MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER)
                child2 = enforce_min_max_players_per_server(network, tuple(child2), MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER)
                timerthree.stop()
                timerthreesum += timerthree.get_elapsed_time()


                offspring.extend([child1, child2])

            whiletimer.stop()
            whiletimersum += whiletimer.get_elapsed_time()
            population = parents + offspring

        sorted_pop = sorted(population, key=lambda x: fitness_values[population.index(x)])
        last_pop = sorted_pop.copy()
        best_solution = sorted_pop[0]
        timer.stop()
        #bigtimersum += bigtimer.get_elapsed_time()
        logger.log('Genetic algorithm has found a solution with a fitness of ' + str(best_fitness), print_to_console=True)
        success = constraints_are_met(network, best_solution, MAX_CORE_SERVERS, MAX_EDGE_SERVERS, MAX_PLAYERS_ON_SERVER, MIN_PLAYERS_ON_SERVER)
        logger.log(f'Constraints are{" " if success == 0 else " not " }met ({success})', print_to_console=True)
      #  logger.log(f"timersums: {bigtimersum}, {fitnesstimersum}, {whiletimersum}, {timeronesum}, {timertwosum}, {timerthreesum}", level="DEBUG", print_to_console=False)
        network.set_player_server_metrics(best_solution)
        network.calculate_delays("Genetic algorithm", debug_prints=True)
        last_optimized_delay = network.delay_metrics[0]
        last_optimized_player_count = len(network.players)
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
        network.draw_graph(title=str(tick).zfill(4) + '_' + "Heuristic" + '_' + f"{len(network.players)}_{NR_OF_GAME_SERVERS}_{len(network.selected_core_servers)}_{len(network.selected_edge_servers)}", figsize=(20,20), save=True, save_dir=save_path)
        
        GEN_has_run = True
        added_players = False
        removed_players = False
    
    if (GUROBI_OPT and (0 and (tick == 101 or tick == 201 or tick == 301 or tick == 401)) and not ILP_has_run): #run_migration_due_to_threshold or run_migration_due_to_player_count_change
        timer.start()
        # qoe_optimization_migration = QoEOptimizationMigration(
        #     network=network,
        #     fix_servers=network.selected_core_servers,
        #     dynamic_servers=network.edge_servers,
        #     players=network.players,
        #     nr_of_game_servers=len(network.selected_core_servers)+MAX_EDGE_SERVERS,
        #     min_players_connected=MIN_PLAYERS_ON_SERVER,
        #     max_connected_players = MAX_PLAYERS_ON_SERVER,
        #     migration_cost=MIGRATION_COST,
        #     debug_prints=False
        # )

        # delaysum_optimization_migration = DelaySumMigrationOptimization(
        #     network=network,
        #     fix_servers=network.selected_core_servers,
        #     dynamic_servers=network.edge_servers,
        #     players=network.players,
        #     nr_of_game_servers=len(network.selected_core_servers)+MAX_EDGE_SERVERS,
        #     min_players_connected=MIN_PLAYERS_ON_SERVER,
        #     max_connected_players = MAX_PLAYERS_ON_SERVER,
        #     migration_cost=MIGRATION_COST,
        #     debug_prints=False
        # )

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

        # delaysum_optimization = DelaySumInitialOptimization(
        #     network=network,
        #     potential_servers=network._only_servers,
        #     players=network.players,
        #     nr_of_game_servers=NR_OF_GAME_SERVERS,
        #     min_players_connected=MIN_PLAYERS_ON_SERVER,
        #     max_connected_players=MAX_PLAYERS_ON_SERVER,
        #     debug_prints=False 
        # )

        print('optimization started')
        success = interplayer_delay_optimization_migration.solve()
        if success is False:
            raise ValueError("Optimization failed!")
        print('optimization finished')
        timer.stop()

        network.calculate_delays(method_type="sum_delay", debug_prints=debug_prints)
        last_optimized_delay = network.delay_metrics[0]
        last_optimized_player_count = len(network.players)
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
        network.draw_graph(title=str(tick).zfill(4) + '_' + 'Gurobi mig' + '_' + f"{len(network.players)}_{NR_OF_GAME_SERVERS}_{len(network.selected_core_servers)}_{len(network.selected_edge_servers)}", figsize=(12,8), save=True, save_dir=save_path)
        ILP_has_run = True

    if (tick > 1 and not ILP_has_run and not GEN_has_run):
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
    print(tick)

#network.display_plots()
generate_GIF(save_path)

logger.log("Simulation completed successfully.", print_to_console=True)