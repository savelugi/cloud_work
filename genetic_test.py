import os
from utils import *
from network_graph import *
from visualization import *
from gurobi import *
from datetime import datetime
from mutation import *

config_file = "/Users/ebenbot/Documents/University/cloud_work/genconfig.ini"
config = read_configuration(config_file)
save_dir = get_save_dir(config)

debug_prints, optimize, save, active_models = get_toggles_from_genconfig(config)

timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Get current timestamp
timer = Timer()
if optimize:
    param_combinations = read_parameters_from_genconfig(config)

    if save:
        topology = config['Topology']['topology']
        save_path = save_dir + 'ga' + timestamp + '_' + topology + "/"
        # Check if the directory exists, if not, create it
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        csv_path = save_path+topology+"_"+str(param_combinations[0][0])+"_"+str(timestamp)+".csv"
        write_ga_csv_header(csv_path, active_models)

    # Main loop, going through all the parameters
    for params in param_combinations:
        num_players, nr_of_servers, max_players_connected, mutation_rate, generation_size, tournament_size = params
        temp_csv_row = list(params)

######################################################################################################################################################
######################################################################################################################################################
        modelname = 'sum_rank_single'
        if 'sum_rank_single' in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            timer.start()
            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate=mutation_rate,
                generations=generation_size,
                min_connected_players=tournament_size,
                max_connected_players=max_players_connected,
                max_server_nr=nr_of_servers,
                selection_strategy="rank_based",
                fitness_method='sum',
                crossover_method='single_point')
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_ga_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
    
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")


######################################################################################################################################################
######################################################################################################################################################
        modelname = 'sum_rank_multi'
        if modelname in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            timer.start()
            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate=mutation_rate,
                generations=generation_size,
                min_connected_players=tournament_size,
                max_connected_players=max_players_connected,
                max_server_nr=nr_of_servers,
                selection_strategy="rank_based",
                fitness_method='sum',
                crossover_method='multi_point')
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_ga_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
    
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")

######################################################################################################################################################
######################################################################################################################################################
        modelname = 'sum_rank_unif'
        if modelname in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            timer.start()
            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate=mutation_rate,
                generations=generation_size,
                min_connected_players=tournament_size,
                max_connected_players=max_players_connected,
                max_server_nr=nr_of_servers,
                selection_strategy="rank_based",
                fitness_method='sum',
                crossover_method='uniform')
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_ga_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
    
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")

######################################################################################################################################################
######################################################################################################################################################
        modelname = 'sum_tournament_single'
        if modelname in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            timer.start()
            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate=mutation_rate,
                generations=generation_size,
                min_connected_players=tournament_size,
                max_connected_players=max_players_connected,
                max_server_nr=nr_of_servers,
                selection_strategy="tournament",
                tournament_size=tournament_size,
                fitness_method='sum',
                crossover_method='single_point')
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_ga_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
    
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")


######################################################################################################################################################
######################################################################################################################################################
        modelname = 'sum_tournament_multi'
        if modelname in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            timer.start()
            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate=mutation_rate,
                generations=generation_size,
                min_connected_players=tournament_size,
                max_connected_players=max_players_connected,
                max_server_nr=nr_of_servers,
                selection_strategy="tournament",
                tournament_size=tournament_size,
                fitness_method='sum',
                crossover_method='multi_point')
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_ga_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
    
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")


######################################################################################################################################################
######################################################################################################################################################
        modelname = 'sum_tournament_unif'
        if modelname in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            timer.start()
            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate=mutation_rate,
                generations=generation_size,
                min_connected_players=tournament_size,
                max_connected_players=max_players_connected,
                max_server_nr=nr_of_servers,
                selection_strategy="tournament",
                tournament_size=tournament_size,
                fitness_method='sum',
                crossover_method='uniform')
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_ga_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
    
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")

######################################################################################################################################################
######################################################################################################################################################
        modelname = 'sum_roulette_single'
        if modelname in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            timer.start()
            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate=mutation_rate,
                generations=generation_size,
                min_connected_players=tournament_size,
                max_connected_players=max_players_connected,
                max_server_nr=nr_of_servers,
                selection_strategy="roulette_wheel",
                tournament_size=tournament_size,
                fitness_method='sum',
                crossover_method='single_point')
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_ga_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
    
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")

######################################################################################################################################################
######################################################################################################################################################
        modelname = 'sum_roulette_multi'
        if modelname in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            timer.start()
            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate=mutation_rate,
                generations=generation_size,
                min_connected_players=tournament_size,
                max_connected_players=max_players_connected,
                max_server_nr=nr_of_servers,
                selection_strategy="roulette_wheel",
                tournament_size=tournament_size,
                fitness_method='sum',
                crossover_method='multi_point')
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_ga_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
    
######################################################################################################################################################
######################################################################################################################################################
        modelname = 'sum_roulette_unif'
        if modelname in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            timer.start()
            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate=mutation_rate,
                generations=generation_size,
                min_connected_players=tournament_size,
                max_connected_players=max_players_connected,
                max_server_nr=nr_of_servers,
                selection_strategy="roulette_wheel",
                tournament_size=tournament_size,
                fitness_method='sum',
                crossover_method='uniform')
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_ga_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")
        if save:    
            write_csv_row(csv_path, temp_csv_row)