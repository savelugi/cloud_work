from utils.utils import *
from network_graph import *
from placement import *
from visualization import *
from gurobi import *

topology_dir = "C:/Users/bbenc/Documents/NETWORKZ/cloud_work/src/"
#topology_dir = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/src/"

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



# # Preparing positions
# pos = {**server_positions, **players}

# # Drawing network decisions
# visualization = Visualization(network)
# visualization.draw_graph(pos, server_positions, players, canvas_size=(48, 30), node_size=30, show_edge_labels=False)

model = grb.Model()

# Változók: Játékosok és szerverek közötti útvonal
paths = {}
for player in players:
    for server in server_positions:
        paths[(player, server)] = model.addVar(vtype=grb.GRB.BINARY, name=f"path_{player}_{server}")

# Cél: Késleltetés minimalizálása
total_delay = model.addVar(vtype=grb.GRB.CONTINUOUS, name="total_delay")

# Korlátok hozzáadása
for player in players:
    for server in server_positions:
        model.addConstr(total_delay >= paths[(player, server)] * network_map[player][server])
