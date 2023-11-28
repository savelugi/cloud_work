from utils import *
from network_graph import *
from visualization import *
from gurobi import *


timer = Timer()

#topology_dir = "C:/Users/bbenc/Documents/NETWORKZ/cloud_work/src/"
topology_dir = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/src/"
#file_path = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/10player_3server_60db_2000ms.gml"

df_results = pd.DataFrame()

# Parameters
param_combinations = [
    #num_players    nr_of_servers     max_connected_players        max_allowed_delay
    (100,                6,                     20,                       1400), 
    (100,                6,                     20,                       1500),
    (100,                6,                     20,                       2500),
    (100,                6,                     20,                       3500),
    (100,                6,                     20,                       4500)
]

# Player generation parameters
lat_range = (25,45) # from graph
long_range = (-123, -70) # from graph
seed_value = 42

for params in param_combinations:
    num_players, nr_of_servers, max_connected_players, max_allowed_delay = params

    # Adding server nodes
    network = NetworkGraph()
    network.load_topology(topology_dir+"26_usa.gml")
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
        max_connected_players=max_connected_players,
        max_allowed_delay=max_allowed_delay)

    timer.stop()   

    # Calculate metrics for the first Gurobi model
    if selected_servers_model_sum is not None:
        delay_metrics_model_sum = calculate_delay_metrics(network, connected_players_info_model_sum, selected_servers_model_sum, method_type='Delay sum method')
        delay_metrics_model_sum.append(len(selected_servers_model_sum))
        delay_metrics_model_sum.append(timer.get_elapsed_time())
    else:
        delay_metrics_model_sum = [0, 0, 0, 0, 0, 0, 0, 0]


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

    df_row = pd.DataFrame([list(params) + delay_metrics_model_sum + delay_metrics_model_ipd], columns=[
        'num_players', 'nr_of_servers', 'max_connected_players', 'max_allowed_delay',
        'average_player_to_server_delay', 'min_player_to_server_delay', 'max_player_to_server_delay',
        'average_player_to_player_delay', 'min_player_to_player_delay', 'max_player_to_player_delay', 
        'nr_of_selected_servers_sum', 'sim_time_sum',
        'average_player_to_server_delay', 'min_player_to_server_delay', 'max_player_to_server_delay',
        'average_player_to_player_delay', 'min_player_to_player_delay', 'max_player_to_player_delay',
        'nr_of_selected_servers_ipd', 'sim_time_ipd'
    ])

    df_results = pd.concat([df_results, df_row])


#                                                _____  _____  _____ _   _ _______ 
###############################################  |  __ \|  __ \|_   _| \ | |__   __| ################################################
###############################################  | |__) | |__) | | | |  \| |  | |    ################################################
###############################################  |  ___/|  _  /  | | | . ` |  | |    ################################################
###############################################  | |    | | \ \ _| |_| |\  |  | |    ################################################
###############################################  |_|    |_|  \_\_____|_| \_|  |_|    ################################################
                                    
# Display the DataFrame
print(df_results)

# Save the DataFrame to a CSV file
df_results.to_csv('optimization_results.csv', index=False)
                                        
# # Preparing positions
# pos = {**server_positions, **players}

# # Drawing network decisions
# visualization = Visualization(network)

# #visualization.draw_graph(pos, server_positions, players, canvas_size=(48, 30), node_size=60, show_edge_labels=True)

# visualization.draw_paths(pos, player_server_paths_model_sum, server_positions, selected_servers_model_sum, players,
#                         canvas_size=(48, 30), node_size=60, show_edge_labels=True, title='SUM')

# visualization.draw_paths(pos, player_server_paths_model_ipd, server_positions, selected_servers_model_ipd, players,
#                           canvas_size=(48, 30), node_size=60, show_edge_labels=True, title='IPD')

# visualization.display_plots()