from utils.utils import *
from network_graph import *
from placement import *
from visualization import *
from gurobi import *

#topology_dir = "C:/Users/bbenc/Documents/NETWORKZ/cloud_work/src/"
topology_dir = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/src/"

# Adding server nodes
network = NetworkGraph()
network.load_topology(topology_dir+"26_usa.gml")

# Getting server positions
server_positions = network.get_server_positions()

# Adding players
num_players = 10
lat_range = (25,45) # from graph
long_range = (-123, -70) # from graph
players = generate_players(num_players, long_range, lat_range)
network.add_nodes_from_keys(players)

# for player in players:
#     network.connect_player_to_server(players, player, server_positions)

model = grb.Model()
placement = model.addVars(server_positions, vtype=grb.GRB.BINARY, name="server_placement")
total_delay = model.addVar(vtype=grb.GRB.INTEGER, name="total_delay")


# Preparing positions
pos = {**server_positions, **players}

# Drawing network decisions
visualization = Visualization(network)
visualization.draw_graph(pos, server_positions, players, canvas_size=(48, 30), node_size=30, show_edge_labels=False)