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
num_players = 20
lat_range = (25,45) # from graph
long_range = (-123, -70) # from graph
seed_value = 42
players = generate_players(num_players, long_range, lat_range, seed_value)
network.add_nodes_from_keys(players)

for player in players:
    network.connect_player_to_server(players, player, server_positions)

nr_of_servers = 4
max_connected_players = 10
max_allowed_delay = 20000

selected_servers_model_1 = None
selected_servers_model_2 = None
connected_players_model_1 = None
connected_players_model_2 = None

timer.start()

connected_players_info_model_1, selected_servers_model_1, player_server_paths_model_1 = sum_delay_optimization(
    network=network, 
    server_positions=server_positions,
    players=players, 
    nr_of_servers=nr_of_servers, 
    max_connected_players=max_connected_players,
    max_allowed_delay=max_allowed_delay)

timer.stop()   
timer.print_elapsed_time()

# Calculate metrics for the first Gurobi model
if selected_servers_model_1 is not None:
    calculate_delay_metrics(network, connected_players_info_model_1, selected_servers_model_1, method_type='Delay sum method')

print_pattern()

#########################################################################################################################################
#########################################################################################################################################


timer.start()

connected_players_info_model_2, selected_servers_model_2, player_server_paths_model_2 = sum_delay_optimization(
    network=network,
    server_positions=server_positions,
    players=players,
    nr_of_servers=nr_of_servers,
    max_connected_players=max_connected_players,
    max_allowed_delay=max_allowed_delay)

timer.stop()
timer.print_elapsed_time()

# Calculate metrics for the second Gurobi model
if selected_servers_model_2 is not None:
    calculate_delay_metrics(network, connected_players_info_model_2, selected_servers_model_2, method_type='Interplayer delay method')

print_pattern()
#########################################################################################################################################
#########################################################################################################################################

# Preparing positions
pos = {**server_positions, **players}
# Drawing network decisions
visualization = Visualization(network)
#visualization.draw_graph(pos, server_positions, players, canvas_size=(48, 30), node_size=60, show_edge_labels=True)
visualization.draw_paths(pos, player_server_paths_model_1, server_positions, selected_servers_model_1, players, canvas_size=(48, 30), node_size=60, show_edge_labels=True, title='SUM')
visualization.draw_paths(pos, player_server_paths_model_2, server_positions, selected_servers_model_2, players, canvas_size=(48, 30), node_size=60, show_edge_labels=True, title='IPD')
visualization.display_plots()