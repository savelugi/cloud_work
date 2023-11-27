from utils import *
from network_graph import *
from visualization import *
from gurobi import *


timer = Timer()

#topology_dir = "C:/Users/bbenc/Documents/NETWORKZ/cloud_work/src/"
topology_dir = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/src/"
#file_path = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/10player_3server_60db_2000ms.gml"

# # Adding server nodes
network = NetworkGraph()
network.load_topology(topology_dir+"26_usa.gml")
# Getting server positions
server_positions = network.get_server_positions()

# Adding players
num_players = 40
lat_range = (25,45) # from graph
long_range = (-123, -70) # from graph
seed_value = 42
players = generate_players(num_players, long_range, lat_range, seed_value)
network.add_nodes_from_keys(players)

for player in players:
    network.connect_player_to_server(players, player, server_positions)

# Parameters
nr_of_servers = 4
max_connected_players = 10
max_allowed_delay = 20000


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
    calculate_delay_metrics(network, connected_players_info_model_sum, selected_servers_model_sum, method_type='Delay sum method')

timer.print_elapsed_time()

print_pattern()
#                                                    _____ _____  _____   
################################################### |_   _|  __ \|  __ \  #######################################################
###################################################   | | | |__) | |  | | #######################################################
###################################################   | | |  ___/| |  | | #######################################################
###################################################   | |_| |    | |__| | #######################################################
################################################### |_____|_|    |_____/  #######################################################

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
    calculate_delay_metrics(network, connected_players_info_model_ipd, selected_servers_model_ipd, method_type='Interplayer delay method')
    
timer.print_elapsed_time()

#                                                _____  _____  _____ _   _ _______ 
############################################### |  __ \|  __ \|_   _| \ | |__   __| ################################################
############################################### | |__) | |__) | | | |  \| |  | |    ################################################
############################################### |  ___/|  _  /  | | | . ` |  | |    ################################################
############################################### | |    | | \ \ _| |_| |\  |  | |    ################################################
############################################### |_|    |_|  \_\_____|_| \_|  |_|    ################################################
                                    
                                    
# Preparing positions
pos = {**server_positions, **players}

# Drawing network decisions
visualization = Visualization(network)

#visualization.draw_graph(pos, server_positions, players, canvas_size=(48, 30), node_size=60, show_edge_labels=True)

visualization.draw_paths(pos, player_server_paths_model_sum, server_positions, selected_servers_model_sum, players,
                        canvas_size=(48, 30), node_size=60, show_edge_labels=True, title='SUM')

visualization.draw_paths(pos, player_server_paths_model_ipd, server_positions, selected_servers_model_ipd, players,
                          canvas_size=(48, 30), node_size=60, show_edge_labels=True, title='IPD')

visualization.display_plots()