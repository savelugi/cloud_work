from utils.utils import *
from network_graph import *
from placement import *
from visualization import *
import networkx as nx

topology_dir = "C:/Users/bbenc/Documents/NETWORKZ/cloud_work/src/"
#topology_dir = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/src/"

# Adding server nodes
network = NetworkGraph()
network.load_topology(topology_dir+"26_usa.gml")

# Getting server positions
server_positions = network.get_server_positions()

# Adding players
num_players = 100
lat_range = (25,45) # from graph
long_range = (-123, -70) # from graph
players = generate_players(num_players, long_range, lat_range)
network.add_nodes_from_keys(players)

# Preparing positions
pos = {**server_positions, **players}

server_decision = ServerPlacementAlgorithm(network)
for player in players.values():
    server_decision.connect_player_to_server(player, server_positions)

#player_position = (-113.26613033172009, 34.39212026283701)
#print(distances)
#closest_server = min(distances, key=distances.get)

# Drawing network decisions
#visualization = Visualization(server_decision)
#visualization.draw_graph(pos, server_positions, players, canvas_size=(48, 30), node_size=300, show_edge_labels=False)