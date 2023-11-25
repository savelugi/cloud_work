from utils.utils import *
from network_graph import *
from visualization import *
from gurobi import *
from gurobipy import GRB

timer = Timer()

#topology_dir = "C:/Users/bbenc/Documents/NETWORKZ/cloud_work/src/"
topology_dir = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/src/"
#file_path = "C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/your_graph.gml"

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

for player in players:
    network.connect_player_to_server(players, player, server_positions)


# timer.start()

# sum_model = grb.Model()

# # Decision variables: binary variable indicating if a server is chosen
# server_selected = {}
# for server in server_positions:
#     server_selected[server] = sum_model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

# # Objective function: minimize total delay
# sum_model.setObjective(
#     grb.quicksum(
#         network.get_shortest_path_delay(player, server) * server_selected[server]
#         for player in players
#         for server in server_positions
#     ),
#     sense=GRB.MINIMIZE,
# )

# # Constraint: select only one server
# sum_model.addConstr(grb.quicksum(server_selected[server] for server in server_positions) == 1)

# # Solve the optimization problem
# sum_model.optimize()

# # Retrieve the selected server
# selected_server = None
# for server in server_positions:
#     if server_selected[server].x > 0.5:
#         selected_server = server
#         break

# timer.stop()

# # Print the chosen server
# print(f"The sum gurobi method has chosen: {selected_server}")
# timer.print_elapsed_time()
# print_pattern()

############################################################################################################

# timer.start()

# ipd_model = grb.Model()

# # Decision variables: binary variable indicating if a server is chosen
# server_selected = {}
# for server in server_positions:
#     server_selected[server] = ipd_model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

# # Introduce interplayer delay variable for each pair of players
# interplayer_delay = {}
# for player1 in players:
#     for player2 in players:
#         if player1 != player2:
#             interplayer_delay[(player1, player2)] = ipd_model.addVar(lb=0.0, name=f"ipd_{player1}_{player2}")

# ipd_model.setObjective(
#     grb.quicksum(
#         interplayer_delay[(player1, player2)] 
#         for player1 in players 
#         for player2 in players 
#         if player1 != player2
#     ),
#     sense=GRB.MINIMIZE,
# )

# # Constraint: select only one server
# ipd_model.addConstr(grb.quicksum(server_selected[server] for server in server_positions) == 1)

# # Constraint: Define interplayer delay based on server selection
# for player1 in players:
#     for player2 in players:
#         if player1 != player2:
#             ipd_model.addConstr(
#                 interplayer_delay[(player1, player2)] >= network.get_shortest_path_delay(player1, player2) 
#                 * grb.quicksum(server_selected[server] 
#                 for server in server_positions),
#                 f"ipd_{player1}_{player2}_constraint"
#             )

# # Solve the optimization problem
# ipd_model.optimize()

# # Retrieve the selected server
# selected_server = None
# for server in server_positions:
#     if server_selected[server].x > 0.5:
#         selected_server = server
#         break

# print(f"Inter-player-delay gurobi has chosen: {selected_server}")
# # Calculate and print minimal interplayer delay
# minimal_delay = ipd_model.objVal
# print(f"The minimal interplayer delay is: {minimal_delay}")

# timer.stop()
# timer.print_elapsed_time()
# print_pattern()

############################################################################

timer.start()

delay_sum = 0
min_value = float('inf')
server_nr = None
for server in server_positions:
    for player in players:
        delay = network.get_shortest_path_delay(player, server)
        delay_sum = delay_sum + delay

    print(f"Delay sum if the server is in {server} = {delay_sum}")
    if (delay_sum < min_value):
        min_value = delay_sum
        server_nr = server

    delay_sum = 0
timer.stop()
timer.print_elapsed_time()
print(f"Brute force chosen server is: {server_nr}")
print_pattern()

# #################################################################################################
# timer.start()

# sum_model = grb.Model()

# n_threads = 4  # For example, using 4 threads
# sum_model.setParam('Threads', n_threads)

# # Decision variables: binary variable indicating if a server is chosen
# server_selected = {}
# for server in server_positions:
#     server_selected[server] = sum_model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

# # Objective function: minimize maximum delay between any two players
# sum_model.setObjective(
#     grb.quicksum(
#         (network.get_shortest_path_delay(player1, server) + network.get_shortest_path_delay(player2, server)) * server_selected[server]
#         for player1 in players
#         for player2 in players
#         for server in server_positions
#         if player1 != player2
#     ),
#     sense=GRB.MINIMIZE,
# )

# # Constraints: select only one server
# sum_model.addConstr(grb.quicksum(server_selected[server] for server in server_positions) == 1)

# # Solve the optimization problem
# sum_model.optimize()

# # Retrieve the selected server
# selected_server = None
# for server in server_positions:
#     if server_selected[server].x > 0.5:
#         selected_server = server
#         break

# # Calculate and print minimal interplayer delay
# minimal_delay = sum_model.objVal
# print(f"The minimal interplayer delay is: {minimal_delay}")

# timer.stop()
# timer.print_elapsed_time()
# print(f"New is: {selected_server}")
# print_pattern()

#################################################################################################

timer.start()

min_value = float('inf')
server_nr = None

for server in server_positions:
    max_interplayer_delay = 0
    max_delay_players = None

    for player1 in players:
        for player2 in players:
            if player1 != player2:
                interplayer_delay = network.get_shortest_path_delay(player1, server) + network.get_shortest_path_delay(player2, server)
                    
                if interplayer_delay > max_interplayer_delay:
                    max_interplayer_delay = interplayer_delay
                    max_delay_players = (player1, player2)
    
    if max_delay_players:
        print(f"max_interplayer_delay is {max_interplayer_delay} if server is {server} between {max_delay_players[0]} and {max_delay_players[1]}")

    if max_interplayer_delay < min_value:
        min_value = max_interplayer_delay
        server_nr = server
timer.stop()
timer.print_elapsed_time()

if server_nr is not None:
    print(f"The server with the minimum maximum interplayer delay is {server_nr} with a delay of {min_value}")
else:
    print("No valid server found.")

print_pattern()
##########################################################################################################################################


import gurobipy as gp
from gurobipy import GRB

# Create a new Gurobi model
model = gp.Model("MinInterplayerDelay")

# Decision variables
servers = server_positions  # Assuming server_positions is predefined
players = players  # Assuming players is predefined

# Variable to represent whether a server is chosen
server_chosen = model.addVars(servers, vtype=GRB.BINARY, name="server_chosen")

# Objective function
model.setObjective(gp.quicksum(server_chosen[server] for server in servers), GRB.MINIMIZE)

# Constraints
for player1 in players:
    for player2 in players:
        if player1 != player2:
            for server in servers:
                delay_var = network.get_shortest_path_delay(player1, server) + network.get_shortest_path_delay(player2, server)
                model.addConstr(delay_var >= max_interplayer_delay * server_chosen[server])

# Solve the model
model.optimize()

# Retrieve the optimal solution
selected_server = None
min_interplayer_delay = float('inf')

for server in servers:
    if server_chosen[server].x > 0.5:
        selected_server = server

print(f"The selected server is {selected_server} with a minimum interplayer delay of {min_interplayer_delay}")


# Preparing positions
pos = {**server_positions, **players}
# Drawing network decisions
visualization = Visualization(network)
visualization.draw_graph(pos, server_positions, players, canvas_size=(48, 30), node_size=60, show_edge_labels=True)