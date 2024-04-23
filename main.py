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
config = read_configuration(config_file)

topology_file = get_topology_filename(topology, config)
save_dir = get_save_dir(config)
seed_value = 42

debug_prints, optimize, save, plot, sum_model, ipd_model, gen_model = get_toggles_from_config(config)

# Adding server nodes
network = NetworkGraph()
network.load_topology(topology_file)

# Getting server positions
server_positions = network.get_server_positions()
server_list = list(network.graph.nodes)


timer = Timer()
if optimize:
    df_results = pd.DataFrame()
    
    param_combinations = read_parameters_from_config(topology, config)

    # Main loop, going through all the parameters
    for params in param_combinations:
        num_players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay = params

        # Adding server nodes
        network = NetworkGraph()
        network.load_topology(topology_file)

        # Getting server positions
        server_positions = network.get_server_positions()

        long_range, lat_range = get_lat_long_range(topology)
        players = generate_players(num_players, long_range, lat_range, seed_value)
        network.add_players(players)

        for player in players:
            network.connect_player_to_server(players, player, server_positions)
        
# SUM        
######################################################################################################################################################
######################################################################################################################################################
        if sum_model:
            if debug_prints:
                print_pattern()

            timer.start()

            connected_players_info_model_sum, player_server_paths_model_sum = sum_delay_optimization(
                network=network, 
                server_positions=server_positions,
                players=players, 
                nr_of_servers=nr_of_servers,
                min_players_connected=min_players_connected, 
                max_connected_players=max_connected_players,
                max_allowed_delay=max_allowed_delay,
                debug_prints=debug_prints)

            timer.stop()   

            # Calculate metrics for the first Gurobi model
            if connected_players_info_model_sum is not None:
                delay_metrics_model_sum, server_to_player_delays = network.calculate_delays(connected_players_info_model_sum, method_type='Delay sum method', debug_prints=debug_prints)                
                delay_metrics_model_sum.append(round(timer.get_elapsed_time()))

                qoe_conf_preferences = config['Weights']
                qoe_metrics = network.calculate_qoe_metrics(connected_players_info_model_sum, server_to_player_delays, qoe_conf_preferences)
            else:
                delay_metrics_model_sum = [0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                dir_name = topology + "_SUM_" + str(num_players)
                save_name = dir_name + "_" + str(nr_of_servers) + "_" + str(min_players_connected) + "_" + str(max_connected_players)
                folder_path = os.path.join(save_dir, dir_name)  # Assuming you want to create the folder in the current directory
                
                # Check if the directory exists, if not, create it
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                
                full_save_path = os.path.join(folder_path, save_name)
                network.save_graph(player_server_paths_model_sum, server_positions, connected_players_info_model_sum, full_save_path)
        elif debug_prints:
            print("Sum model is turned off at this optimization sequece!")

# IPD
######################################################################################################################################################
######################################################################################################################################################
        if ipd_model:
            timer.start()

            connected_players_info_model_ipd, player_server_paths_model_ipd = interplayer_delay_optimization(
                network=network,
                server_positions=server_positions,
                players=players,
                nr_of_servers=nr_of_servers,
                min_players_connected=min_players_connected,
                max_connected_players=max_connected_players,
                max_allowed_delay=max_allowed_delay,
                debug_prints=debug_prints)

            timer.stop()

            # Calculate metrics for the second Gurobi model
            if connected_players_info_model_ipd is not None:
                delay_metrics_model_ipd = network.calculate_delays(connected_players_info_model_ipd, method_type='Interplayer delay method', debug_prints=debug_prints)
                delay_metrics_model_ipd.append(timer.get_elapsed_time())
            else:
                delay_metrics_model_ipd = [0, 0, 0, 0, 0, 0, 0, 0]

            if save:
                dir_name = topology + "_IPD_" + str(num_players)
                save_name = dir_name + "_" + str(nr_of_servers) + "_" + str(min_players_connected) + "_" + str(max_connected_players)
                folder_path = os.path.join(save_dir, dir_name)  # Assuming you want to create the folder in the current directory
                

                # Check if the directory exists, if not, create it
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                
                
                full_save_path = os.path.join(folder_path, save_name)
                network.save_graph(player_server_paths_model_ipd, server_positions, connected_players_info_model_ipd, full_save_path)
        elif debug_prints:
            print("IPD model is turned off at this optimization sequece!")

        if save and sum_model and ipd_model:
            df_row = pd.DataFrame([list(params) + delay_metrics_model_sum + delay_metrics_model_ipd], columns=[
                'num_players', 'nr_of_servers', 'min_players_connected', 'max_connected_players', 'max_allowed_delay',
                'average_player_to_server_delay_sum', 'min_player_to_server_delay_sum', 'max_player_to_server_delay_sum',
                'average_player_to_player_delay_sum', 'min_player_to_player_delay_sum', 'max_player_to_player_delay_sum', 
                'nr_of_selected_servers_sum', 'sim_time_sum',
                'average_player_to_server_delay_ipd', 'min_player_to_server_delay_ipd', 'max_player_to_server_delay_ipd',
                'average_player_to_player_delay_ipd', 'min_player_to_player_delay_ipd', 'max_player_to_player_delay_ipd',
                'nr_of_selected_servers_ipd', 'sim_time_ipd'
            ])

            df_results = pd.concat([df_results, df_row])


# GENETIC
######################################################################################################################################################
######################################################################################################################################################

        if gen_model:
            best_solution, connected_players_info_model_gen, player_server_paths_model_gen = genetic_algorithm(
                network=network,
                players=list(players),
                servers=server_list,
                population_size=len(players),
                mutation_rate= 0.1,
                generations= 1000,
                max_connected_players=max_connected_players,
                max_server_nr=nr_of_servers)

            if save:
                dir_name = topology + "_GEN_" + str(num_players)
                save_name = dir_name + "_" + str(nr_of_servers) + "_" + str(min_players_connected) + "_" + str(max_connected_players)
                folder_path = os.path.join(save_dir, dir_name)  # Assuming you want to create the folder in the current directory
                
                # Check if the directory exists, if not, create it
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                
                full_save_path = os.path.join(folder_path, save_name)
                network.save_graph(player_server_paths_model_gen, server_positions, connected_players_info_model_gen, full_save_path)
    
        elif debug_prints:
           print("Genetic model is turned off at this optimization sequece!")


    if save and sum_model and ipd_model:
        # Assuming df_results is your DataFrame
        pd.set_option('display.max_rows', None)  # Show all rows
        pd.set_option('display.max_columns', None)  # Show all columns
        # Display the DataFrame
        print(df_results)

        # Save the DataFrame to a CSV file
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Get current timestamp
        csv = save_dir+topology+"_"+str(num_players)+"_"+str(timestamp)+".csv"
        latest_csv_dir = csv
        df_results.to_csv(csv, index=False)



# PLOT
######################################################################################################################################################
######################################################################################################################################################

# if plot:

#     # Assume df_results is your DataFrame containing the mentioned columns
#     # Load data from CSV into df_results DataFrame
#     if optimize:
#         df_results = pd.read_csv(latest_csv_dir)
#     else:
#         csv_file_path = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/save/"
#         csv_file_name = "cost_100_20231205230210"
#         try:
#             df_results = pd.read_csv(csv_file_path + csv_file_name+".csv")
#         except FileNotFoundError:
#             print("Check the filename in the print function!")

#     # Plotting average player-to-server delay for both methods
#     plt.figure(figsize=(10, 6))

#     plt.subplot(2, 1, 1)
#     draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
#                       y_sum='average_player_to_server_delay_sum', y_ipd='average_player_to_server_delay_ipd',
#                       y_label='Avg. Player-to-Server Delay [ms]', title='Average Player-to-Server Delay Comparison')

#     # Plotting average player-to-player delay for both methods
#     plt.subplot(2, 1, 2)
#     draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
#                       y_sum='average_player_to_player_delay_sum', y_ipd='average_player_to_player_delay_ipd',
#                       y_label='Avg. Player-to-Player Delay [ms]', title='Average Player-to-Player Delay Comparison')
#     plt.tight_layout()
    
#     plt.figure(figsize=(10, 6))
#     plt.subplot(2, 1, 1)
#     draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
#                       y_sum='max_player_to_server_delay_sum', y_ipd='max_player_to_server_delay_ipd',
#                       y_label='Max Player-to-Server Delay [ms]', title='Maximum Player-to-Server Delay Comparison')
    
#     plt.subplot(2, 1, 2)
#     draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
#                       y_sum='max_player_to_player_delay_sum', y_ipd='max_player_to_player_delay_ipd',
#                       y_label='Max Player-to-Player Delay [ms]', title='Maximum Player-to-Player Delay Comparison')
#     plt.tight_layout()
    
#     plt.figure(figsize=(10, 6))
#     plt.subplot(2,1,1)
#     draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
#                       y_sum='min_player_to_server_delay_sum', y_ipd='min_player_to_server_delay_ipd',
#                       y_label='Max Player-to-Server Delay [ms]', title='Minimum Player-to-Server Delay Comparison')

#     plt.subplot(2,1,2)
#     draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
#                       y_sum='min_player_to_player_delay_sum', y_ipd='min_player_to_player_delay_ipd',
#                       y_label='Max Player-to-Player Delay [ms]', title='Minimum Player-to-Player Delay Comparison')
#     plt.tight_layout()

#     plt.show()


# print_plot_nr = None
# if print_plot_nr is not None:
#     #num_players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay = param_combinations_usa[print_plot_nr-1]
#     # Adding server nodes
#     network = NetworkGraph()
#     network.load_topology(topology_dir+"26_usa_scaled.gml")
#     # Getting server positions
#     server_positions = network.get_server_positions()

#     print(network.get_max_server_to_server_delay(server_positions)[0])
#     print(network.get_max_server_to_server_delay(server_positions)[1])

#     players = generate_players(num_players, long_range, lat_range, seed_value)
#     network.add_players(players)

#     for player in players:
#         network.connect_player_to_server(players, player, server_positions)

#     connected_players_info_model_sum, selected_servers_model_sum, player_server_paths_model_sum = sum_delay_optimization(
#         network=network, 
#         server_positions=server_positions,
#         players=players, 
#         nr_of_servers=nr_of_servers,
#         min_players_connected=min_players_connected, 
#         max_connected_players=max_connected_players,
#         max_allowed_delay=max_allowed_delay
#     )
#     calculate_delays(network, connected_players_info_model_sum, selected_servers_model_sum, method_type='Sum delay method')
#     connected_players_info_model_ipd, selected_servers_model_ipd, player_server_paths_model_ipd = interplayer_delay_optimization(
#         network=network,
#         server_positions=server_positions,
#         players=players,
#         nr_of_servers=nr_of_servers,
#         min_players_connected=min_players_connected,
#         max_connected_players=max_connected_players,
#         max_allowed_delay=max_allowed_delay
#     )
#     calculate_delays(network, connected_players_info_model_ipd, selected_servers_model_ipd, method_type='Interplayer delay method')
#     # Preparing positions
#     pos = {**server_positions, **players}

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

if True:
    plt.figure(figsize=(10, 6))
    file_path = save_dir+"cost_SUM_100/"+"cost_SUM_100_5_6_20"+".gml"
    draw_graph_from_gml(file_path, 1, "(a) SUM method, 5 servers", show_edge_labels=False)

    file_path = save_dir+"cost_GEN_100/"+"cost_GEN_100_5_6_20"+".gml"
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