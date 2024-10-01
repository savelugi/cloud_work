import os
from utils import *
from network_graph import *
from visualization import *
from gurobi import *
from datetime import datetime
from mutation import *

dir_path = os.path.dirname(os.path.realpath(__file__))
save_dir = os.path.join(dir_path, "saves/")
config_file = os.path.join(dir_path, "config.ini")
config = read_configuration(config_file)

#seed_value = 42

debug_prints, optimize, save, plot, active_models = get_toggles_from_config(config)
param_combinations = read_parameters_from_config(config)
topology = config['Topology']['topology']
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")  # Get current timestamp
#save_path = save_dir + timestamp + '_' + topology + "/"

# if not os.path.exists(save_path):
#     os.makedirs(save_path)

num_players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay = param_combinations[0]
network = NetworkGraph(modelname='ilp_sum', config=config, num_gen_players=num_players)

# sum_delay_optimization(
#                 network=network, 
#                 server_positions=network.server_positions,
#                 players=network.players, 
#                 nr_of_servers=nr_of_servers,
#                 min_players_connected=min_players_connected, 
#                 max_connected_players=max_connected_players,              
#                 max_allowed_delay=max_allowed_delay,
#                 debug_prints=debug_prints)
network.color_graph()

#print
network.draw_graph(title="Graf")

#move
network.update_player_positions()

#print again
network.draw_graph(title="Graf")


network.display_plots()