import gurobipy as grb
from gurobipy import GRB
from network_graph import *

def sum_delay_optimization(network: NetworkGraph, server_positions, players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay, debug_prints):
    sum_model = grb.Model()
    if not debug_prints:
        # Set Gurobi parameter to suppress output
        sum_model.setParam('OutputFlag', 0)

    # Decision variables: binary variable indicating if a server is chosen
    server_selected = {}
    for server in server_positions:
        server_selected[server] = sum_model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

    # Define a new set of decision variables representing connected players to servers
    connected_players = {(player, server): sum_model.addVar(vtype=GRB.BINARY, name=f"player_{player}_connected_to_{server}")
                        for player in players for server in server_positions}

    # 1. Constraint: select only #nr_of_servers 
    sum_model.addConstr(grb.quicksum(server_selected[server] for server in server_positions) <= nr_of_servers)

    # 2. Constraints to ensure players are connected only to selected servers
    for player in players:
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for server in server_positions) == 1,
            name=f"player_{player}_connected_to_one_server"
        )
        for server in server_positions:
            sum_model.addConstr(connected_players[(player, server)] <= server_selected[server])

    # 3. Constraint: Limit the number of connected players to each server
    for server in server_positions:
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) <= max_connected_players,
            name=f"limit_connected_players_to_server_{server}"
        )
    # 4. Constraint: Ensure a minimum number of players connected to selected servers
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) >= min_players_connected * server_selected[server],
            name=f"min_connected_players_to_server_{server}"
        )

    # Objective function: minimize total delay
    sum_model.setObjective(
        grb.quicksum(
            network.get_shortest_path_delay(player, server) * connected_players[(player, server)]
            for player in players
            for server in server_positions
        ),
        sense=GRB.MINIMIZE,
    )

    # Solve the optimization problem
    sum_model.optimize()

    if sum_model.status == GRB.OPTIMAL:
        # Initialize player_server_paths_model_1 as an empty list
        player_server_paths_model_1 = []

        # Dictionary to store connected players for each server
        connected_players_info_model_1 = {server: [] for server in server_positions}

        # Retrieve the selected servers and connected players
        for server_idx in server_positions:
            if server_selected[server_idx].x > 0.5:
                connected_players_to_server = []
                for player in players:
                    if connected_players[(player, server_idx)].x > 0.5:
                        connected_players_to_server.append(player)

                        network.graph.nodes[server_idx]['server']['game_server'] = 1
                        network.graph.nodes[player]['connected_to_server'] = server_idx

                connected_players_info_model_1[server_idx] = connected_players_to_server

        if debug_prints:
            # Print connected players for each server
            for server_idx, connected_players_list in connected_players_info_model_1.items():
                if connected_players_list:
                    for player in connected_players_list:
                        path = network.get_shortest_path(player, server_idx)
                        player_server_paths_model_1.append((player, server_idx, path))

                    #print(f"To server {server_idx} connected players are: {', '.join(connected_players_list)}")
                #else:
                # print(f"To server {server_idx} no players are connected")
    else:
        print("No optimal solution found.")
        return False

    network.connected_players_info = connected_players_info_model_1
    network.player_server_paths = player_server_paths_model_1

    return True

def interplayer_delay_optimization(network: NetworkGraph, server_positions, players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay, debug_prints):
    # Create a new Gurobi model
    model = grb.Model('MinimizeMaxInterplayerDelay')
    if not debug_prints:
        # Set Gurobi parameter to suppress output
        model.setParam('OutputFlag', 0)

    # Decision variables: binary variable indicating if a server is chosen
    server_selected = {}
    for server in server_positions:
        server_selected[server] = model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

    # Maximum interplayer delay
    max_interplayer_delay = model.addVar(name='max_interplayer_delay')

    # Define a new set of decision variables representing connected players to servers
    connected_players = {(player, server): model.addVar(vtype=GRB.BINARY, name=f"player_{player}_connected_to_{server}")
                        for player in players for server in server_positions}
    
    # 1. Constraint: Calculate maximum interplayer delay
    for server in server_positions:
        for player1 in players:
            for player2 in players:
                if player1 != player2:
                    interplayer_delay = (
                        network.get_shortest_path_delay(player1, server) +
                        network.get_shortest_path_delay(player2, server)
                    )
                    # Add constraint based on selected servers
                    model.addConstr(
                        max_interplayer_delay >= interplayer_delay * (connected_players[(player1, server)] + connected_players[(player2, server)] - 1)
                    )

    # 2. Constraint: select only #nr_of_servers 
    model.addConstr(grb.quicksum(server_selected[server] for server in server_positions) <= nr_of_servers)


    # 3. Constraints to ensure players are connected only to selected servers
    for player in players:
        model.addConstr(
            grb.quicksum(connected_players[(player, server)] for server in server_positions) == 1,
            name=f"player_{player}_connected_to_one_selected_server"
        )
    for player in players:
        for server in server_positions:
            model.addConstr(connected_players[(player, server)] <= server_selected[server])

    # 4. Constraint: Limit the number of connected players to each server
    for server in server_positions:
        model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) <= max_connected_players,
            name=f"limit_connected_players_to_server_{server}"
        )

    # 5. Constraint: Ensure a minimum number of players connected to selected servers
    for server in server_positions:
        model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) >= min_players_connected * server_selected[server],
            name=f"min_connected_players_to_server_{server}"
        )

    # Objective: Minimize the maximum interplayer delay
    model.setObjective(max_interplayer_delay, GRB.MINIMIZE)

    # Solve the optimization problem
    model.optimize()

    if model.status == GRB.OPTIMAL:
        # Initialize player_server_paths_model_2 as an empty list
        player_server_paths_model_2 = []

        # Dictionary to store connected players for each server
        connected_players_info_model_2 = {server: [] for server in server_positions}

        # Retrieve the selected servers and connected players
        for server_idx in server_positions:
            if server_selected[server_idx].x > 0.5:
                connected_players_to_server = []
                for player in players:
                    if connected_players[(player, server_idx)].x > 0.5:
                        connected_players_to_server.append(player)
                        network.graph.nodes[server_idx]['server']['game_server'] = 1
                        network.graph.nodes[player]['connected_to_server'] = server_idx

                connected_players_info_model_2[server_idx] = connected_players_to_server

        if debug_prints:
            # Print connected players for each server
            for server_idx, connected_players_list in connected_players_info_model_2.items():
                if connected_players_list:
                    for player in connected_players_list:
                        path = network.get_shortest_path(player, server_idx)
                        player_server_paths_model_2.append((player, server_idx, path))

                    #print(f"To server {server_idx} connected players are: {', '.join(connected_players_list)}")
                #else:
                # print(f"To server {server_idx} no players are connected")
    else:
        print("No optimal solution found.")
        return False

    network.connected_players_info = connected_players_info_model_2
    network.player_server_paths = player_server_paths_model_2

    return True

def run_optimization(network, server_positions, players, nr_of_servers, max_connected_players, max_allowed_delay):
    connected_players_info_sum, selected_servers_sum, _ = sum_delay_optimization(
        network=network, 
        server_positions=server_positions,
        players=players, 
        nr_of_servers=nr_of_servers, 
        max_connected_players=max_connected_players,
        max_allowed_delay=max_allowed_delay)
    
    connected_players_info_ipd, selected_servers_ipd, _ = interplayer_delay_optimization(
        network=network, 
        server_positions=server_positions,
        players=players, 
        nr_of_servers=nr_of_servers, 
        max_connected_players=max_connected_players,
        max_allowed_delay=max_allowed_delay)
    
    return connected_players_info_sum, selected_servers_sum, connected_players_info_ipd, selected_servers_ipd
