import gurobipy as grb
from gurobipy import GRB
from network_graph import *


def sum_delay_optimization(network: NetworkGraph, server_positions, players, nr_of_servers, max_connected_players, max_allowed_delay):
    sum_model = grb.Model()
    # Set Gurobi parameter to suppress output
    sum_model.setParam('OutputFlag', 0)

    # Decision variables: binary variable indicating if a server is chosen
    server_selected = {}
    for server in server_positions:
        server_selected[server] = sum_model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

    # Maximum server-player delay
    max_server_player_delay = sum_model.addVar(name='max_server_player_delay')

    # Constraint: select only #nr_of_servers 
    sum_model.addConstr(grb.quicksum(server_selected[server] for server in server_positions) <= nr_of_servers)

    # Define a new set of decision variables representing connected players to servers
    connected_players = {(player, server): sum_model.addVar(vtype=GRB.BINARY, name=f"player_{player}_connected_to_{server}")
                        for player in players for server in server_positions}

    # Constraint: Limit the number of connected players to each server
    for server in server_positions:
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) <= max_connected_players * server_selected[server],
            name=f"limit_connected_players_to_server_{server}"
        )

    # Constraints to ensure players are connected only to selected servers
    for player in players:
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for server in server_positions) == 1,
            name=f"player_{player}_connected_to_one_server"
        )

    # Constraint: Limit the maximum delay between a server and a player
    for server in server_positions:
        for player in players:
            server_player_delay = network.get_shortest_path_delay(player, server)
            # Add constraint to limit maximum delay between server and player
            sum_model.addConstr(max_server_player_delay >= server_player_delay * connected_players[(player, server)])

    # Add a constraint to ensure the maximum delay is not exceeded
    sum_model.addConstr(max_server_player_delay <= max_allowed_delay)

    # Objective function: minimize total delay
    sum_model.setObjective(
        grb.quicksum(
            network.get_shortest_path_delay(player, server) * server_selected[server]
            for player in players
            for server in server_positions
        ),
        sense=GRB.MINIMIZE,
    )

    # Solve the optimization problem
    sum_model.optimize()

    if sum_model.status == GRB.OPTIMAL:
        # Initialize selected_servers_model_1 as an empty list
        selected_servers_model_1 = []
        player_server_paths_model_1 = []

        # Dictionary to store connected players for each server
        connected_players_info_model_1 = {server: [] for server in server_positions}

        # Retrieve the selected servers and connected players
        for server_idx in server_positions:
            if server_selected[server_idx].x > 0.5:
                selected_servers_model_1.append(server_idx)
                connected_players_to_server = []
                for player in players:
                    if connected_players[(player, server_idx)].x > 0.5:
                        connected_players_to_server.append(player)
                connected_players_info_model_1[server_idx] = connected_players_to_server

        # Print connected players for each server
        for server_idx, connected_players_list in connected_players_info_model_1.items():
            if connected_players_list:
                for player in connected_players_list:
                    path = network.get_shortest_path(player, server_idx)
                    player_server_paths_model_1.append((player, server_idx, path))

                print(f"To server {server_idx} connected players are: {', '.join(connected_players_list)}")
            #else:
            # print(f"To server {server_idx} no players are connected")
    else:
        print("No optimal solution found.")

    return connected_players_info_model_1, selected_servers_model_1, player_server_paths_model_1

def interplayer_delay_optimization(network: NetworkGraph, server_positions, players, nr_of_servers, max_connected_players, max_allowed_delay):
    # Create a new Gurobi model
    model = grb.Model('MinimizeMaxInterplayerDelay')
    # Set Gurobi parameter to suppress output
    model.setParam('OutputFlag', 0)

    # Decision variables: binary variable indicating if a server is chosen
    server_selected = {}
    for server in server_positions:
        server_selected[server] = model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

    # Maximum interplayer delay
    max_interplayer_delay = model.addVar(name='max_interplayer_delay')
    # Maximum server-player delay
    max_server_player_delay = model.addVar(name='max_server_player_delay')

    # Constraint: select only #nr_of_servers 
    model.addConstr(grb.quicksum(server_selected[server] for server in server_positions) <= nr_of_servers)

    # Constraint: Calculate maximum interplayer delay
    for server in server_positions:
        for player1 in players:
            for player2 in players:
                if player1 != player2:
                    interplayer_delay = (
                        network.get_shortest_path_delay(player1, server) +
                        network.get_shortest_path_delay(player2, server)
                    )
                    # Add constraint based on selected servers
                    model.addConstr(max_interplayer_delay >= interplayer_delay * server_selected[server])

    # Define a new set of decision variables representing connected players to servers
    connected_players = {(player, server): model.addVar(vtype=GRB.BINARY, name=f"player_{player}_connected_to_{server}")
                        for player in players for server in server_positions}

    # Constraint: Limit the number of connected players to each server
    for server in server_positions:
        model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) <= max_connected_players * server_selected[server],
            name=f"limit_connected_players_to_server_{server}"
        )

    # Constraints to ensure players are connected only to selected servers
    for player in players:
        model.addConstr(
            grb.quicksum(connected_players[(player, server)] for server in server_positions) == 1,
            name=f"player_{player}_connected_to_one_server"
        )

    # Constraint: Limit the maximum delay between a server and a player
    for server in server_positions:
        for player in players:
            server_player_delay = network.get_shortest_path_delay(player, server)
            # Add constraint to limit maximum delay between server and player
            model.addConstr(max_server_player_delay >= server_player_delay * connected_players[(player, server)])

    # Add a constraint to ensure the maximum delay is not exceeded
    model.addConstr(max_server_player_delay <= max_allowed_delay)

    # Objective: Minimize the maximum interplayer delay
    model.setObjective(max_interplayer_delay, GRB.MINIMIZE)

    # Solve the optimization problem
    model.optimize()

    if model.status == GRB.OPTIMAL:
        # Initialize selected_servers_model_2 as an empty list
        selected_servers_model_2 = []
        player_server_paths_model_2 = []

        # Dictionary to store connected players for each server
        connected_players_info_model_2 = {server: [] for server in server_positions}

        # Retrieve the selected servers and connected players
        for server_idx in server_positions:
            if server_selected[server_idx].x > 0.5:
                selected_servers_model_2.append(server_idx)
                connected_players_to_server = []
                for player in players:
                    if connected_players[(player, server_idx)].x > 0.5:
                        connected_players_to_server.append(player)
                connected_players_info_model_2[server_idx] = connected_players_to_server

        # Print connected players for each server
        for server_idx, connected_players_list in connected_players_info_model_2.items():
            if connected_players_list:
                for player in connected_players_list:
                    path = network.get_shortest_path(player, server_idx)
                    player_server_paths_model_2.append((player, server_idx, path))

                print(f"To server {server_idx} connected players are: {', '.join(connected_players_list)}")
            #else:
            # print(f"To server {server_idx} no players are connected")
    else:
        print("No optimal solution found.")

    return connected_players_info_model_2, selected_servers_model_2, player_server_paths_model_2

#################################################################################################
#################################################################################################

# delay_sum = 0
# min_value = float('inf')
# server_nr = None
# for server in server_positions:
#     for player in players:
#         delay = network.get_shortest_path_delay(player, server)
#         delay_sum = delay_sum + delay

#     #print(f"Delay sum if the server is in {server} = {delay_sum}")
#     if (delay_sum < min_value):
#         min_value = delay_sum
#         server_nr = server

#     delay_sum = 0

# print(f"Brute force chosen server is: {server_nr}")


#################################################################################################
#################################################################################################

# min_value = float('inf')
# server_nr = None

# for server in server_positions:
#     max_interplayer_delay = 0
#     max_delay_players = None

#     for player1 in players:
#         for player2 in players:
#             if player1 != player2:
#                 interplayer_delay = network.get_shortest_path_delay(player1, server) + network.get_shortest_path_delay(player2, server)
                    
#                 if interplayer_delay > max_interplayer_delay:
#                     max_interplayer_delay = interplayer_delay
#                     max_delay_players = (player1, player2)
    
#     if max_delay_players:
#        print(f"max_interplayer_delay is {max_interplayer_delay} if server is {server} between {max_delay_players[0]} and {max_delay_players[1]}")

#     if max_interplayer_delay < min_value:
#         min_value = max_interplayer_delay
#         server_nr = server

# if server_nr is not None:
#     print(f"The server with the minimum maximum interplayer delay is {server_nr} with a delay of {min_value}")
# else:
#     print("No valid server found.")

##########################################################################################################################################
