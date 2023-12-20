from utils import *
from network_graph import *
from visualization import *
from gurobi import *
from datetime import datetime

topology = "cost"

optimize = False
save = False
plot = True

# Parameters
param_combinations_usa = [
    #num_players    nr_of_servers    min_players_connected     max_connected_players        max_allowed_delay
    (100,                  9,                  6,                      20,                        27),
    (100,                  8,                  6,                      20,                        27),
    (100,                  7,                  6,                      20,                        27),
    (100,                  6,                  6,                      20,                        27),
    (100,                  5,                  6,                      20,                        27)]

param_combinations_germany = [
    #num_players    nr_of_servers    min_players_connected     max_connected_players        max_allowed_delay
    (100,                  10,                  4,                      32,                        23),
    (100,                  10,                  6,                      32,                        23),
    (100,                  10,                  8,                      32,                        23),
    (100,                  10,                  10,                     32,                        23),
    (100,                  10,                  12,                     32,                        23)]

param_combinations_cost = [
    #num_players    nr_of_servers    min_players_connected     max_connected_players        max_allowed_delay
    (100,                  9,                  6,                      20,                        5),
    (100,                  8,                  6,                      20,                        5),
    (100,                  7,                  6,                      20,                        5),
    (100,                  6,                  6,                      20,                        5),
    (100,                  5,                  6,                      20,                        5)]

#topology_dir = "C:/Users/bbenc/Documents/NETWORKZ/cloud_work/src/"
topology_dir = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/src/"
save_dir = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/save/"
#file_path = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/10player_3server_60db_2000ms.gml"

# Player generation parameters
if topology == "usa":
    lat_range = (25,45) # from graph
    long_range = (-123, -70) # from graph
elif topology == "germany":
    lat_range = (47, 55) # from graph
    long_range = (6, 14) # from graph
elif topology == "cost":
    lat_range = (35, 62) # from graph
    long_range = (-10,28) # from graph
else:
    print("error loading latitude and longitude")

seed_value = 42

# Adding server nodes
network = NetworkGraph()
if topology == "usa":
    network.load_topology(topology_dir+"26_usa_scaled.gml")
elif topology == "germany":
    network.load_topology(topology_dir+"50_germany_scaled.gml")
elif topology == "cost":
    network.load_topology(topology_dir+"37_cost_scaled.gml")
else:
    print("error loading topology")

# Getting server positions
server_positions = network.get_server_positions()

timer = Timer()
if optimize:
    df_results = pd.DataFrame()
    if topology == "usa":
        param_combinations = param_combinations_usa
    elif topology == "germany":
        param_combinations = param_combinations_germany
    elif topology == "cost":
        param_combinations = param_combinations_cost
    else:
        print("error loading parameters")

    for params in param_combinations:
        num_players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay = params

        # Adding server nodes
        network = NetworkGraph()
        if topology == "usa":
            network.load_topology(topology_dir+"26_usa_scaled.gml")
        elif topology == "germany":
            network.load_topology(topology_dir+"50_germany_scaled.gml")
        elif topology == "cost":
            network.load_topology(topology_dir+"37_cost_scaled.gml")
        else:
            print("error loading topology")

        # Getting server positions
        server_positions = network.get_server_positions()

        players = generate_players(num_players, long_range, lat_range, seed_value)
        network.add_nodes_from_keys(players)

        for player in players:
            network.connect_player_to_server(players, player, server_positions)


        #                                                        _____ _    _ __  __ 
        ######################################################  / ____| |  | |  \/  | ########################################################
        ###################################################### | (___ | |  | | \  / | ########################################################
        ######################################################  \___ \| |  | | |\/| | ########################################################
        ######################################################  ____) | |__| | |  | | ########################################################
        ###################################################### |_____/ \____/|_|  |_| ########################################################
        print_pattern()
        timer.start()

        connected_players_info_model_sum, selected_servers_model_sum, player_server_paths_model_sum = sum_delay_optimization(
            network=network, 
            server_positions=server_positions,
            players=players, 
            nr_of_servers=nr_of_servers,
            min_players_connected=min_players_connected, 
            max_connected_players=max_connected_players,
            max_allowed_delay=max_allowed_delay)

        timer.stop()   

        # Calculate metrics for the first Gurobi model
        if selected_servers_model_sum is not None:
            delay_metrics_model_sum = calculate_delay_metrics(network, connected_players_info_model_sum, selected_servers_model_sum, method_type='Delay sum method')
            delay_metrics_model_sum.append(len(selected_servers_model_sum))
            delay_metrics_model_sum.append(round(timer.get_elapsed_time()))
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
            network.save_graph(player_server_paths_model_sum, server_positions, selected_servers_model_sum, full_save_path)

        #                                                    _____ _____  _____   
        ################################################### |_   _|  __ \|  __ \   #######################################################
        ###################################################   | | | |__) | |  | |  #######################################################
        ###################################################   | | |  ___/| |  | |  #######################################################
        ###################################################   | |_| |    | |__| |  #######################################################
        ################################################### |_____|_|    |_____/   #######################################################

        timer.start()

        connected_players_info_model_ipd, selected_servers_model_ipd, player_server_paths_model_ipd = interplayer_delay_optimization(
            network=network,
            server_positions=server_positions,
            players=players,
            nr_of_servers=nr_of_servers,
            min_players_connected=min_players_connected,
            max_connected_players=max_connected_players,
            max_allowed_delay=max_allowed_delay)

        timer.stop()

        # Calculate metrics for the second Gurobi model
        if selected_servers_model_ipd is not None:
            delay_metrics_model_ipd = calculate_delay_metrics(network, connected_players_info_model_ipd, selected_servers_model_ipd, method_type='Interplayer delay method')
            delay_metrics_model_ipd.append(len(selected_servers_model_ipd))
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
            network.save_graph(player_server_paths_model_ipd, server_positions, selected_servers_model_ipd, full_save_path)
        if save:
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

    if save:
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

#                                                 _____  _____  _____ _   _ _______ 
###############################################  |  __ \|  __ \|_   _| \ | |__   __| ################################################
###############################################  | |__) | |__) | | | |  \| |  | |    ################################################
###############################################  |  ___/|  _  /  | | | . ` |  | |    ################################################
###############################################  | |    | | \ \ _| |_| |\  |  | |    ################################################
###############################################  |_|    |_|  \_\_____|_| \_|  |_|    ################################################



if plot:

    # Assume df_results is your DataFrame containing the mentioned columns
    # Load data from CSV into df_results DataFrame
    if optimize:
        df_results = pd.read_csv(latest_csv_dir)
    else:
        csv_file_path = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/save/"
        csv_file_name = "cost_100_20231205230210"
        try:
            df_results = pd.read_csv(csv_file_path + csv_file_name+".csv")
        except FileNotFoundError:
            print("Check the filename in the print function!")

    # Plotting average player-to-server delay for both methods
    plt.figure(figsize=(10, 6))

    plt.subplot(2, 1, 1)
    draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
                      y_sum='average_player_to_server_delay_sum', y_ipd='average_player_to_server_delay_ipd',
                      y_label='Avg. Player-to-Server Delay [ms]', title='Average Player-to-Server Delay Comparison')

    # Plotting average player-to-player delay for both methods
    plt.subplot(2, 1, 2)
    draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
                      y_sum='average_player_to_player_delay_sum', y_ipd='average_player_to_player_delay_ipd',
                      y_label='Avg. Player-to-Player Delay [ms]', title='Average Player-to-Player Delay Comparison')
    plt.tight_layout()
    
    plt.figure(figsize=(10, 6))
    plt.subplot(2, 1, 1)
    draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
                      y_sum='max_player_to_server_delay_sum', y_ipd='max_player_to_server_delay_ipd',
                      y_label='Max Player-to-Server Delay [ms]', title='Maximum Player-to-Server Delay Comparison')
    
    plt.subplot(2, 1, 2)
    draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
                      y_sum='max_player_to_player_delay_sum', y_ipd='max_player_to_player_delay_ipd',
                      y_label='Max Player-to-Player Delay [ms]', title='Maximum Player-to-Player Delay Comparison')
    plt.tight_layout()
    
    plt.figure(figsize=(10, 6))
    plt.subplot(2,1,1)
    draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
                      y_sum='min_player_to_server_delay_sum', y_ipd='min_player_to_server_delay_ipd',
                      y_label='Max Player-to-Server Delay [ms]', title='Minimum Player-to-Server Delay Comparison')

    plt.subplot(2,1,2)
    draw_compare_plot(df_results, x='nr_of_servers', x_label='Nr. of game servers', 
                      y_sum='min_player_to_player_delay_sum', y_ipd='min_player_to_player_delay_ipd',
                      y_label='Max Player-to-Player Delay [ms]', title='Minimum Player-to-Player Delay Comparison')
    plt.tight_layout()

    plt.show()


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
#     network.add_nodes_from_keys(players)

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
#     calculate_delay_metrics(network, connected_players_info_model_sum, selected_servers_model_sum, method_type='Sum delay method')
#     connected_players_info_model_ipd, selected_servers_model_ipd, player_server_paths_model_ipd = interplayer_delay_optimization(
#         network=network,
#         server_positions=server_positions,
#         players=players,
#         nr_of_servers=nr_of_servers,
#         min_players_connected=min_players_connected,
#         max_connected_players=max_connected_players,
#         max_allowed_delay=max_allowed_delay
#     )
#     calculate_delay_metrics(network, connected_players_info_model_ipd, selected_servers_model_ipd, method_type='Interplayer delay method')
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
# network.add_nodes_from_keys(players)

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
    file_path = save_dir+"cost_SUM_100/"+"cost_SUM_100_5_6_20"+".gml"
    draw_graph_from_gml(file_path,1,"(a) SUM method, 5 servers", show_edge_labels=False)

    file_path = save_dir+"cost_IPD_100/"+"cost_IPD_100_5_6_20"+".gml"
    draw_graph_from_gml(file_path,2,"(b) IPD method, 5 servers", show_edge_labels=False)
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