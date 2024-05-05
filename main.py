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
seed_value = 42

debug_prints, optimize, save, plot, active_models = get_toggles_from_config(config)

timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Get current timestamp

timer = Timer()
if optimize:
    if save:
        df_results = pd.DataFrame()
    
    param_combinations = read_parameters_from_config(config)

    # Main loop, going through all the parameters
    for params in param_combinations:
        num_players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay = params

        if save:
            df_row = pd.DataFrame([list(params)], columns=['num_players', 'nr_of_servers', 'min_players_connected', 'max_connected_players', 'max_allowed_delay'])
        
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
                network.save_graph(timestamp, params)

                sum_columns = pd.DataFrame([network.delay_metrics], columns=[
                    f'average_player_to_server_delay_{modelname}', f'min_player_to_server_delay_{modelname}', f'max_player_to_server_delay_{modelname}',
                    f'average_player_to_player_delay_{modelname}', f'min_player_to_player_delay_{modelname}', f'max_player_to_player_delay_{modelname}', 
                    f'nr_of_selected_servers_{modelname}', f'qoe_score_{modelname}', f'sim_time_{modelname}'])
                
                df_row = pd.concat([df_row, sum_columns], axis=1)

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

                ipd_columns = pd.DataFrame([network.delay_metrics], columns=[
                    f'average_player_to_server_delay_{modelname}', f'min_player_to_server_delay_{modelname}', f'max_player_to_server_delay_{modelname}',
                    f'average_player_to_player_delay_{modelname}', f'min_player_to_player_delay_{modelname}', f'max_player_to_player_delay_{modelname}',
                    f'nr_of_selected_servers_{modelname}', f'qoe_score_{modelname}', f'sim_time_{modelname}'])
                
                df_row = pd.concat([df_row, ipd_columns], axis=1)
                
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

                gen_sum_columns = pd.DataFrame([network.delay_metrics], columns=[
                    f'average_player_to_server_delay_{modelname}', f'min_player_to_server_delay_{modelname}', f'max_player_to_server_delay_{modelname}',
                    f'average_player_to_player_delay_{modelname}', f'min_player_to_player_delay_{modelname}', f'max_player_to_player_delay_{modelname}',
                    f'nr_of_selected_servers_{modelname}', f'qoe_score_{modelname}', f'sim_time_{modelname}'])
                
                df_row = pd.concat([df_row, gen_sum_columns], axis=1)
    
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

                gen_ipd_columns = pd.DataFrame([network.delay_metrics], columns=[
                    f'average_player_to_server_delay_{modelname}', f'min_player_to_server_delay_{modelname}', f'max_player_to_server_delay_{modelname}',
                    f'average_player_to_player_delay_{modelname}', f'min_player_to_player_delay_{modelname}', f'max_player_to_player_delay_{modelname}',
                    f'nr_of_selected_servers_{modelname}', f'qoe_score_{modelname}', f'sim_time_{modelname}'])
                
                df_row = pd.concat([df_row, gen_ipd_columns], axis=1)
    
        elif debug_prints:
           print(f"{modelname} model is turned off at this optimization sequece!")

        df_results = pd.concat([df_results, df_row])


    if save:
        # Assuming df_results is your DataFrame
        pd.set_option('display.max_rows', None)  # Show all rows
        pd.set_option('display.max_columns', None)  # Show all columns
        # Display the DataFrame
        print(df_row)

        # Save the DataFrame to a CSV file
        save_path = save_dir + str(timestamp) + "/"
        csv = save_path+topology+"_"+str(num_players)+"_"+str(timestamp)+".csv"
        latest_csv_dir = csv
        df_results.to_csv(csv, index=False)



# PLOT
######################################################################################################################################################
######################################################################################################################################################

if plot:
    # Load data from CSV into df_results DataFrame
    if optimize:
        df_results = pd.read_csv(latest_csv_dir, comment='#')
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


# Drawing network decisions
# visualization = Visualization(network)

# visualization.draw_graph(pos, server_positions, players, canvas_size=(48, 30), node_size=60, show_edge_labels=True)

# visualization.draw_paths(pos, player_server_paths_model_sum, server_positions, selected_servers_model_sum, players,
#                         canvas_size=(48, 30), node_size=60, show_edge_labels=True, title='SUM')

# visualization.draw_paths(pos, player_server_paths_model_ipd, server_positions, selected_servers_model_ipd, players,
#                             canvas_size=(48, 30), node_size=60, show_edge_labels=True, title='IPD')

# visualization.display_plots()

####
# network = NetworkGraph()

# network.load_topology(topology_dir+"37_cost_scaled.gml")

# # Player generation parameters
# lat_range = (35, 62) # from graph
# long_range = (-10,28) # from graph
# seed_value = 42
# num_players = 100

# # Getting server positions
# server_positions = network.get_server_positions()

# print(network.get_max_server_to_server_delay(server_positions)[0])
# print(network.get_max_server_to_server_delay(server_positions)[1])

# players = generate_players(num_players, long_range, lat_range, seed_value)
# network.add_players(players)

# for player in players:
#     network.connect_player_to_server(players, player, server_positions)

# # Preparing positions
# pos = {**server_positions, **players}
       
# # Drawing network decisions
# visualization = Visualization(network)
# visualization.draw_graph(pos, server_positions, players, canvas_size=(48, 30), node_size=60, show_edge_labels=False)
# visualization.display_plots() 

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