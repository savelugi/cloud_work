import os
from utils import *
from network_graph import *
from visualization import *
from gurobi import *
from datetime import datetime
from mutation import *

#usa, germany, cost
topology = "cost"

config_file = "/Users/ebenbot/Documents/University/cloud_work/config.ini"
#config_file = r"C:\Users\bbenc\OneDrive\Documents\aGraph\cloud_work\config.ini"
config = read_configuration(config_file)

save_dir = get_save_dir(config)
#seed_value = 42

debug_prints, optimize, save, plot, active_models = get_toggles_from_config(config)

timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Get current timestamp

timer = Timer()
if optimize:
    param_combinations = read_parameters_from_config(config)

    if save:
        topology = config['Topology']['topology']
        save_path = save_dir + timestamp + '_' + topology + "/"
        # Check if the directory exists, if not, create it
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        csv_path = save_path+topology+"_"+str(param_combinations[0][0])+"_"+str(timestamp)+".csv"
        write_csv_header(csv_path, active_models)

    # Main loop, going through all the parameters
    for params in param_combinations:
        num_players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay = params
        temp_csv_row = list(params)
        
# ILP_SUM        
######################################################################################################################################################
######################################################################################################################################################
        modelname = 'ilp_sum'
        if 'ilp_sum' in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            if debug_prints:
                print_pattern()

            timer.start()
            optimization_has_run = sum_delay_optimization(
                network=network, 
                server_positions=network.server_positions,
                players=network.players, 
                nr_of_servers=nr_of_servers,
                min_players_connected=min_players_connected, 
                max_connected_players=max_connected_players,              
                max_allowed_delay=max_allowed_delay,
                debug_prints=debug_prints)
            timer.stop()   

            # Calculate metrics for the first Gurobi model
            if optimization_has_run:
                network.calculate_delays(method_type='ILP Delay sum method', debug_prints=debug_prints)                
                network.calculate_qoe_metrics()
                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                save_path = network.save_graph(timestamp, params)
                temp_csv_row += network.delay_metrics

        elif debug_prints:
            print(f"{modelname} model is turned off at this optimization sequece!")

# IPD
######################################################################################################################################################
######################################################################################################################################################
        modelname = 'ilp_ipd'
        if 'ilp_ipd' in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            timer.start()
            optimization_has_run = interplayer_delay_optimization(
                network=network,
                server_positions=network.server_positions,
                players=network.players,
                nr_of_servers=nr_of_servers,
                min_players_connected=min_players_connected,
                max_connected_players=max_connected_players,
                max_allowed_delay=max_allowed_delay,
                debug_prints=debug_prints)
            timer.stop()

            # Calculate metrics for the second Gurobi model
            if optimization_has_run:
                network.calculate_delays(method_type='ILP Interplayer delay method', debug_prints=debug_prints)
                network.calculate_qoe_metrics()
                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_graph(timestamp, params)
                temp_csv_row += network.delay_metrics

                
        elif debug_prints:
            print(f"{modelname} model is turned off at this optimization sequece!")

# GENETIC SUM
######################################################################################################################################################
######################################################################################################################################################
        modelname = 'gen_sum'
        if 'gen_sum' in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)
            timer.start()
            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate= 0.01,
                generations= 1000,
                min_connected_players=min_players_connected,
                max_connected_players=max_connected_players,
                max_server_nr=nr_of_servers,
                selection_strategy="rank_based",
                tournament_size=50,
                fitness_method='sum')
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='Metaheuristic sum delay method', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
    
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")

# GENETIC IPD
######################################################################################################################################################
######################################################################################################################################################
        modelname = 'gen_ipd'
        if 'gen_ipd' in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)

            timer.start()

            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate= 0.01,
                generations= 1000,
                min_connected_players=min_players_connected,
                max_connected_players=max_connected_players,
                max_server_nr=nr_of_servers,
                selection_strategy="rank_based",
                tournament_size=50,
                fitness_method='ipd')
            
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='Metaheuristic ipd delay method', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
    
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")

# GENETIC COMBINED
######################################################################################################################################################
######################################################################################################################################################
        modelname = 'gen_combined'
        if 'gen_combined' in active_models:
            network = NetworkGraph(modelname=modelname, config=config, num_players=num_players)

            timer.start()
            #max_allowed_delay param is being used for ratio! int type but it is converted to float in the fitness function
            optimization_has_run = genetic_algorithm(
                network=network,
                players=list(network.players),
                servers=network._only_servers,
                population_size=len(network.players),
                mutation_rate= 0.01,
                generations= 1000,
                min_connected_players=min_players_connected,
                max_connected_players=max_connected_players,
                max_server_nr=nr_of_servers,
                selection_strategy="rank_based",
                tournament_size=50,
                fitness_method='sum_ipd',
                ratio=max_allowed_delay)
            
            timer.stop()
            
            # Calculate metrics for the metaheuristic model
            if optimization_has_run:
                network.calculate_delays(method_type='Metaheuristic sum_ipd delay method', debug_prints=debug_prints)
                network.calculate_qoe_metrics()

                network.delay_metrics.append(round(timer.get_elapsed_time()))
            else:
                network.delay_metrics = [0, 0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                network.save_graph(timestamp, params)
                temp_csv_row += network.delay_metrics
    
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")

        if save:    
            write_csv_row(csv_path, temp_csv_row)


# PLOT
######################################################################################################################################################
######################################################################################################################################################

if plot:
    # Load data from CSV into df_results DataFrame
    if optimize:
        df_results = pd.read_csv(csv_path, comment='#')
    else:
        csv_file_name = "germany_100_20240504161640"
        try:
            df_results = pd.read_csv(save_dir + csv_file_name+".csv", comment='#')
        except FileNotFoundError:
            print("Check the filename in the print function!")

    # draw_compare_plot(*active_models, df=df_results, x='nr_of_servers', x_label='Nr. of game servers',
    #                   plot_type='average_player_to_server_delay_', y_label='Avg. Player-to-Server Delay [ms]',
    #                   title='Average Player-to-Server Delay Comparison')
    # draw_compare_plot(*active_models, df=df_results, x='nr_of_servers', x_label='Nr. of game servers',
    #                   plot_type='average_player_to_player_delay_', y_label='Avg. Player-to-Player Delay [ms]',
    #                   title='Average Player-to-Player Delay Comparison')
    # draw_compare_plot(*active_models, df=df_results, x='nr_of_servers', x_label='Nr. of game servers',
    #                   plot_type='max_player_to_server_delay_', y_label='Max. Player-to-Server Delay [ms]',
    #                   title='Maximum Player-to-Server Delay Comparison')
    # draw_compare_plot(*active_models, df=df_results, x='nr_of_servers', x_label='Nr. of game servers',
    #                   plot_type='max_player_to_player_delay_', y_label='Max. Player-to-Player Delay [ms]',
    #                   title='Maximum Player-to-Player Delay Comparison')
    # draw_compare_plot(*active_models, df=df_results, x='nr_of_servers', x_label='Nr. of game servers',
    #                   plot_type='min_player_to_server_delay_', y_label='Avg. Player-to-Server Delay [ms]',
    #                   title='Minimum Player-to-Server Delay Comparison')
    # draw_compare_plot(*active_models, df=df_results, x='nr_of_servers', x_label='Nr. of game servers',
    #                   plot_type='min_player_to_player_delay_', y_label='Avg. Player-to-Player Delay [ms]',
    #                   title='Minimum Player-to-Player Delay Comparison')
    # draw_compare_plot(*active_models, df=df_results, x='nr_of_servers', x_label='Nr. of game servers',
    #                   plot_type='qoe_score_', y_label='Simulation time [s]',
    #                   title='QoE comparison', invert=False)
    draw_compare_plot(*active_models, df=df_results, x='nr_of_servers', x_label='Nr. of game servers',
                      plot_type='sim_time_', y_label='Simulation time [s]',
                      title='Simulation time comparison')

    plt.show()

if False:
    plt.figure(figsize=(10, 6))
    file_path = save_dir+"usa_IPD_100/"+"usa_IPD_100_9_6_20"+".gml"
    draw_graph_from_gml(file_path, 1, "(a) IPD method, 5 servers", show_edge_labels=False)

    file_path = save_dir+"usa_GEN_100/"+"usa_GEN_100_9_6_20"+".gml"
    draw_graph_from_gml(file_path, 2, "(b) GEN method, n servers", show_edge_labels=False)

    # file_path = save_dir+"cost_IPD_100/"+"cost_IPD_100_5_6_20"+".gml"
    # draw_graph_from_gml(file_path,2,"(b) IPD method, 5 servers", show_edge_labels=False)
    #plt.subplots_adjust(top=0.85, bottom=0.1)

    # plt.figure(figsize=(10, 6))
    # file_path = save_dir+"cost_SUM_100/"+"cost_SUM_100_6_6_20"+".gml"
    # draw_graph_from_gml(file_path,1,"Sum method6", show_edge_labels=False)

    # file_path = save_dir+"cost_IPD_100/"+"cost_IPD_100_6_6_20"+".gml"
    # draw_graph_from_gml(file_path,2,"IPD method6", show_edge_labels=False)

    # plt.figure(figsize=(10, 6))
    # file_path = save_dir+"cost_SUM_100/"+"cost_SUM_100_7_6_20"+".gml"
    # draw_graph_from_gml(file_path,1,"Sum method7", show_edge_labels=False)

    # file_path = save_dir+"cost_IPD_100/"+"cost_IPD_100_7_6_20"+".gml"
    # draw_graph_from_gml(file_path,2,"IPD method7", show_edge_labels=False)

    # plt.figure(figsize=(10, 6))
    # file_path = save_dir+"cost_SUM_100/"+"cost_SUM_100_8_6_20"+".gml"
    # draw_graph_from_gml(file_path,1,"Sum method8", show_edge_labels=False)

    # file_path = save_dir+"cost_IPD_100/"+"cost_IPD_100_8_6_20"+".gml"
    # draw_graph_from_gml(file_path,2,"IPD method8", show_edge_labels=False)

    # plt.figure(figsize=(10, 6))
    # file_path = save_dir+"cost_SUM_100/"+"cost_SUM_100_9_6_20"+".gml"
    # draw_graph_from_gml(file_path,1,"Sum method9", show_edge_labels=False)

    # file_path = save_dir+"cost_IPD_100/"+"cost_IPD_100_9_6_20"+".gml"
    # draw_graph_from_gml(file_path,2,"IPD method9", show_edge_labels=False)

    plt.show()