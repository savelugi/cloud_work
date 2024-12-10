import gurobipy as grb
from gurobipy import GRB
from network_graph import *
from globvars import logger


class BaseOptimizationModel:
    def __init__(self, network, potential_servers, players, nr_of_servers, 
                 min_players_connected, max_connected_players, debug_prints):
        self.network = network
        self.potential_servers = potential_servers
        self.players = players
        self.nr_of_servers = nr_of_servers
        self.min_players_connected = min_players_connected
        self.max_connected_players = max_connected_players
        self.debug_prints = debug_prints

        self.model = grb.Model()
        # Set Gurobi parameter to suppress output
        if not debug_prints:
            self.model.setParam('OutputFlag', 0)

        # Decision variables: binary variable indicating if a server is chosen
        self.server_selected = {
            server: self.model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")
            for server in potential_servers
        }

        # Define a new set of decision variables representing connected players to servers
        self.connected_players = {
            (player, server): self.model.addVar(vtype=GRB.BINARY, 
                                                name=f"player_{player}_connected_to_{server}")
            for player in players for server in potential_servers
        }

        
        self._add_common_constraints()

    def _add_common_constraints(self):
        # 1. Constraint: select only #nr_of_servers 
        self.model.addConstr(
            grb.quicksum(self.server_selected[server] for server in self.potential_servers) <= self.nr_of_servers
        )

        # 2. Constraints to ensure players are connected only to selected servers
        for player in self.players:
            self.model.addConstr(
                grb.quicksum(self.connected_players[(player, server)] for server in self.potential_servers) == 1
            )
            for server in self.potential_servers:
                self.model.addConstr(self.connected_players[(player, server)] <= self.server_selected[server])

        # 3. Constraint: Limit the number of connected players to each server
        for server in self.potential_servers:
            max_players = 2 * self.max_connected_players if self.network.is_core_server(server) else self.max_connected_players
            self.model.addConstr(
                grb.quicksum(self.connected_players[(player, server)] for player in self.players) <= 
                max_players * self.server_selected[server]
            )
            self.model.addConstr(
                grb.quicksum(self.connected_players[(player, server)] for player in self.players) >= 
                self.min_players_connected * self.server_selected[server]
            )

    def solve(self):
        self.model.optimize()
        if self.model.status == GRB.OPTIMAL:
            self._extract_solution()
            return True
        else:
            logger.log("No optimal solution found.", level="ERROR")
            return False

    def _extract_solution(self):
        connected_players_info = {server: [] for server in self.potential_servers}
        connected_players_info[None] = []

        player_server_paths = []

        for server_idx in self.potential_servers:
            if self.server_selected[server_idx].X > 0.5:
                connected_players_to_server = []
                for player in self.players:
                    if self.connected_players[(player, server_idx)].X > 0.5:
                        connected_players_to_server.append(player)
                        self.network.graph.nodes[server_idx]['server']['game_server'] = 1
                        self.network.graph.nodes[player]['connected_to_server'] = server_idx
                connected_players_info[server_idx] = connected_players_to_server

        for i, player in enumerate(self.players):
            assigned = False
            for server in self.potential_servers:
                if self.connected_players[(player, server)].X > 0.5:
                    self.network.previous_server_assignments[i] = server
                    assigned = True
                    break
            if not assigned:
                self.network.previous_server_assignments[i] = None

        for server_idx, connected_players_list in connected_players_info.items():
            if connected_players_list:
                for player in connected_players_list:
                    path = self.network.get_shortest_path(player, server_idx)
                    player_server_paths.append((player, server_idx, path))
        
        self.network.connected_players_info = connected_players_info
        self.network.player_server_paths = player_server_paths


class QoEOptimizationInitial(BaseOptimizationModel):
    def __init__(self, network, potential_servers, players, nr_of_game_servers, 
                 min_players_connected, max_connected_players, debug_prints):
        super().__init__(network, potential_servers, players, nr_of_game_servers, 
                         min_players_connected, max_connected_players, debug_prints)
        
        # Objective function: Maximize QoE 
        self.model.setObjective(
            grb.quicksum(
                self.network.calculate_QoE(player, server)*self.connected_players[(player, server)]
                for player in self.players for server in self.potential_servers
            ),
            sense=GRB.MAXIMIZE
        )


class QoEOptimizationMigration(BaseOptimizationModel):
    def __init__(self, network, fix_servers, dynamic_servers, players, nr_of_game_servers,
                 min_players_connected, max_connected_players, migration_cost, debug_prints):
        potential_servers = fix_servers + dynamic_servers
        self.fix_servers = fix_servers
        self.migration_cost_val = migration_cost
        super().__init__(network, potential_servers, players, nr_of_game_servers, 
                         min_players_connected, max_connected_players, debug_prints)

        # Fix szerverek aktívak maradjanak
        self.model.addConstr(
            grb.quicksum(self.server_selected[s] for s in self.fix_servers) >= len(self.fix_servers)
        )

        # Objective function: Maximize QoE while minimizing migration cost
        self.model.setObjective(
            grb.quicksum(
                self.network.calculate_QoE(p, s)*self.connected_players[(p, s)]
                for p in self.players for s in self.potential_servers
            ) - grb.quicksum(
                self.network.calculate_migration_cost(self.network.previous_server_assignments[int(p[1:]) - 1], s, self.migration_cost_val)*self.connected_players[(p, s)]
                for p in self.players for s in self.potential_servers
                if self.network.previous_server_assignments[int(p[1:]) - 1]
            ),
            sense=GRB.MAXIMIZE
        )


def sum_delay_optimization(network: NetworkGraph, server_positions, players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay, debug_prints):
    logger.log("Sum delay optimization started", print_to_console=True)
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
        if network.is_core_server(server):
            max_players = 2 * max_connected_players
        else:
            max_players = max_connected_players
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) <= max_players,
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
        ) + grb.quicksum(
            network.calculate_migration_cost(network.previous_server_assignments[int(player[1:]) - 1], server)
            for player in players
            for server in server_positions
            if network.previous_server_assignments[int(player[1:]) - 1]
        ),
        sense=GRB.MINIMIZE,
    )

    # Solve the optimization problem
    sum_model.optimize()

    if sum_model.status == GRB.OPTIMAL:
        logger.log(f"Model 'sum_delay_optimization' has found an optimal solution.", print_to_console=True)
        # Initialize player_server_paths_model_1 as an empty list
        player_server_paths_model_1 = []

        # Dictionary to store connected players for each server
        connected_players_info_model_1 = {server: [] for server in server_positions}
        connected_players_info_model_1[None] = []

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

        for player in players:
            assigned = False
            for server in server_positions:
                if connected_players[(player, server)].x > 0.5:
                    network.previous_server_assignments[int(player[1:]) - 1] = server
                    assigned = True
                    break
            if not assigned:
                network.previous_server_assignments[int(player[1:]) - 1] = None

        
            # Print connected players for each server
            for server_idx, connected_players_list in connected_players_info_model_1.items():
                if connected_players_list:
                    for player in connected_players_list:
                        path = network.get_shortest_path(player, server_idx)
                        player_server_paths_model_1.append((player, server_idx, path))
                    if debug_prints:
                        logger.log(f"To server {server_idx} connected players ({len(connected_players_list)}) are: {', '.join(connected_players_list)}", save_log=False, print_to_console=False)
                else:
                    if debug_prints:
                        logger.log(f"To server {server_idx} no players are connected", save_log=False, print_to_console=False)
    else:
        logger.log("No optimal solution found.")
        return False

    network.connected_players_info = connected_players_info_model_1
    network.player_server_paths = player_server_paths_model_1
    return True

def delay_sum_migration(network: NetworkGraph, fix_servers, edge_servers, players, nr_of_servers, min_players_connected, max_connected_players, migration_cost, debug_prints):
    logger.log("Delay sum migration optimization started", print_to_console=True)
    sum_model = grb.Model()
    if not debug_prints:
        # Set Gurobi parameter to suppress output
        sum_model.setParam('OutputFlag', 0)

    potential_servers = fix_servers + edge_servers

    # Decision variables: binary variable indicating if a server is chosen
    server_selected = {}
    for server in potential_servers:
        server_selected[server] = sum_model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

    # Define a new set of decision variables representing connected players to servers
    connected_players = {(player, server): sum_model.addVar(vtype=GRB.BINARY, name=f"player_{player}_connected_to_{server}")
                        for player in players for server in potential_servers}

    # 1. Constraint: select only #nr_of_servers 
    sum_model.addConstr(grb.quicksum(server_selected[server] for server in potential_servers) <= nr_of_servers)

    # 2. Constraints to ensure players are connected only to selected servers
    for player in players:
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for server in potential_servers) == 1,
            name=f"player_{player}_connected_to_one_server"
        )
        for server in potential_servers:
            sum_model.addConstr(connected_players[(player, server)] <= server_selected[server])

    # 3. Constraint: Limit the number of connected players to each server
    for server in potential_servers:
        if network.is_core_server(server):
            max_players = 2 * max_connected_players
        else:
            max_players = max_connected_players
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) <= max_players,
            name=f"limit_connected_players_to_server_{server}"
        )
    # 4. Constraint: Ensure a minimum number of players connected to selected servers
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) >= min_players_connected * server_selected[server],
            name=f"min_connected_players_to_server_{server}"
        )

    # 5. Constraint: Fix servers must remain active
        sum_model.addConstr(
            grb.quicksum(server_selected[server] for server in fix_servers) >= len(fix_servers),
            name=f"core_server_{server}_active"
        )
    

    # Objective function: minimize total delay
    sum_model.setObjective(
        grb.quicksum(
            network.get_shortest_path_delay(player, server) * connected_players[(player, server)]
            for player in players
            for server in potential_servers
        ) + grb.quicksum(
            network.calculate_migration_cost(network.previous_server_assignments[int(player[1:]) - 1], server, migration_cost) * connected_players[(player, server)]
            for player in players
            for server in potential_servers
            if network.previous_server_assignments[int(player[1:]) - 1]
        ),
        sense=GRB.MINIMIZE,
    )

    # Solve the optimization problem
    sum_model.optimize()

    if sum_model.status == GRB.OPTIMAL:
        logger.log(f"Model 'delay_sum_migration' has found an optimal solution.", print_to_console=True)
        # Initialize player_server_paths_model_1 as an empty list
        player_server_paths_model_1 = []

        # Dictionary to store connected players for each server
        connected_players_info_model_1 = {server: [] for server in potential_servers}
        connected_players_info_model_1[None] = []

        # Retrieve the selected servers and connected players
        for server_idx in potential_servers:
            if server_selected[server_idx].x > 0.5:
                connected_players_to_server = []
                for player in players:
                    if connected_players[(player, server_idx)].x > 0.5:
                        connected_players_to_server.append(player)

                        network.graph.nodes[server_idx]['server']['game_server'] = 1
                        network.graph.nodes[player]['connected_to_server'] = server_idx

                connected_players_info_model_1[server_idx] = connected_players_to_server

        for player in players:
            assigned = False
            for server in potential_servers:
                if connected_players[(player, server)].x > 0.5:
                    network.previous_server_assignments[int(player[1:]) - 1] = server
                    assigned = True
                    break
            if not assigned:
                network.previous_server_assignments[int(player[1:]) - 1] = None

        
            # Print connected players for each server
            for server_idx, connected_players_list in connected_players_info_model_1.items():
                if connected_players_list:
                    for player in connected_players_list:
                        path = network.get_shortest_path(player, server_idx)
                        player_server_paths_model_1.append((player, server_idx, path))
                    if debug_prints:
                        logger.log(f"To server {server_idx} connected players ({len(connected_players_list)}) are: {', '.join(connected_players_list)}", save_log=False, print_to_console=False)
                else:
                    if debug_prints:
                        logger.log(f"To server {server_idx} no players are connected", save_log=False, print_to_console=False)
    else:
        logger.log("No optimal solution found.")
        return False

    network.connected_players_info = connected_players_info_model_1
    network.player_server_paths = player_server_paths_model_1
    return True
def delay_sum_initial(network: NetworkGraph, potential_servers, players, nr_of_servers, min_players_connected, max_connected_players, debug_prints):
    logger.log("Initial Delay Sum minimalization optimization started", print_to_console=True)
    sum_model = grb.Model()
    if not debug_prints:
        # Set Gurobi parameter to suppress output
        sum_model.setParam('OutputFlag', 0)

    # Decision variables: binary variable indicating if a server is chosen
    server_selected = {}
    for server in potential_servers:
        server_selected[server] = sum_model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

    # Define a new set of decision variables representing connected players to servers
    connected_players = {(player, server): sum_model.addVar(vtype=GRB.BINARY, name=f"player_{player}_connected_to_{server}")
                        for player in players for server in potential_servers}

    # 1. Constraint: select only #nr_of_servers 
    sum_model.addConstr(grb.quicksum(server_selected[server] for server in potential_servers) <= nr_of_servers)

    # 2. Constraints to ensure players are connected only to selected servers
    for player in players:
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for server in potential_servers) == 1,
            name=f"player_{player}_connected_to_one_server"
        )
        for server in potential_servers:
            sum_model.addConstr(connected_players[(player, server)] <= server_selected[server])

    # 3. Constraint: Limit the number of connected players to each server
    for server in potential_servers:
        if network.is_core_server(server):
            max_players = 2 * max_connected_players
        else:
            max_players = max_connected_players
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) <= max_players,
            name=f"limit_connected_players_to_server_{server}"
        )
    # 4. Constraint: Ensure a minimum number of players connected to selected servers
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) >= min_players_connected * server_selected[server],
            name=f"min_connected_players_to_server_{server}"
        )

    # Objective function: minimize total delay
    sum_model.setObjective(
        grb.quicksum( network.get_shortest_path_delay(player, server) * connected_players[(player, server)] for player in players for server in potential_servers),
        sense=GRB.MINIMIZE
    )

    # Solve the optimization problem
    sum_model.optimize()

    if sum_model.status == GRB.OPTIMAL:
        logger.log(f"Model 'sum_delay_optimization' has found an optimal solution.", print_to_console=True)
        # Initialize player_server_paths_model_1 as an empty list
        player_server_paths_model_1 = []

        # Dictionary to store connected players for each server
        connected_players_info_model_1 = {server: [] for server in potential_servers}
        connected_players_info_model_1[None] = []

        # Retrieve the selected servers and connected players
        for server_idx in potential_servers:
            if server_selected[server_idx].x > 0.5:
                connected_players_to_server = []
                for player in players:
                    if connected_players[(player, server_idx)].x > 0.5:
                        connected_players_to_server.append(player)

                        network.graph.nodes[server_idx]['server']['game_server'] = 1
                        network.graph.nodes[player]['connected_to_server'] = server_idx

                connected_players_info_model_1[server_idx] = connected_players_to_server

        for player in players:
            assigned = False
            for server in potential_servers:
                if connected_players[(player, server)].x > 0.5:
                    network.previous_server_assignments[int(player[1:]) - 1] = server
                    assigned = True
                    break
            if not assigned:
                network.previous_server_assignments[int(player[1:]) - 1] = None

        
            # Print connected players for each server
            for server_idx, connected_players_list in connected_players_info_model_1.items():
                if connected_players_list:
                    for player in connected_players_list:
                        path = network.get_shortest_path(player, server_idx)
                        player_server_paths_model_1.append((player, server_idx, path))
                    if debug_prints:
                        logger.log(f"To server {server_idx} connected players ({len(connected_players_list)}) are: {', '.join(connected_players_list)}", save_log=False, print_to_console=False)
                else:
                    if debug_prints:
                        logger.log(f"To server {server_idx} no players are connected", save_log=False, print_to_console=False)
    else:
        logger.log("No optimal solution found.")
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

def interplayer_delay_initial(network: NetworkGraph, potential_servers, players, nr_of_servers, min_players_connected, max_connected_players, debug_prints):
    # Create a new Gurobi model
    model = grb.Model()
    if not debug_prints:
        # Set Gurobi parameter to suppress output
        model.setParam('OutputFlag', 0)

    # Decision variables: binary variable indicating if a server is chosen
    server_selected = {}
    for server in potential_servers:
        server_selected[server] = model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

    # Maximum interplayer delay
    max_interplayer_delay = model.addVar(name='max_interplayer_delay')

    # Define a new set of decision variables representing connected players to servers
    connected_players = {(player, server): model.addVar(vtype=GRB.BINARY, name=f"player_{player}_connected_to_{server}")
                        for player in players for server in potential_servers}
    
    # 1. Constraint: Calculate maximum interplayer delay
    for server in potential_servers:
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
    model.addConstr(grb.quicksum(server_selected[server] for server in potential_servers) <= nr_of_servers)


    # 3. Constraints to ensure players are connected only to selected servers
    for player in players:
        model.addConstr(
            grb.quicksum(connected_players[(player, server)] for server in potential_servers) == 1,
            name=f"player_{player}_connected_to_one_selected_server"
        )
    for player in players:
        for server in potential_servers:
            model.addConstr(connected_players[(player, server)] <= server_selected[server])

    # 4. Constraint: Limit the number of connected players to each server
    for server in potential_servers:
        if network.is_core_server(server):
            max_players = 2 * max_connected_players
        else:
            max_players = max_connected_players

        model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) <= max_players,
            name=f"limit_connected_players_to_server_{server}"
        )

    # 5. Constraint: Ensure a minimum number of players connected to selected servers
    for server in potential_servers:
        model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) >= min_players_connected * server_selected[server],
            name=f"min_connected_players_to_server_{server}"
        )

    # Objective: Minimize the maximum interplayer delay
    model.setObjective(max_interplayer_delay, GRB.MINIMIZE)

    # Solve the optimization problem
    model.optimize()

    if model.status == GRB.OPTIMAL:
        logger.log(f"Model 'interplayer_delay_minimization' has found an optimal solution.", print_to_console=False)
        # Initialize player_server_paths_model_1 as an empty list
        player_server_paths = []

        # Dictionary to store connected players for each server
        connected_players_info = {server: [] for server in potential_servers}
        connected_players_info[None] = []

        # Retrieve the selected servers and connected players
        for server_idx in potential_servers:
            if server_selected[server_idx].x > 0.5:
                connected_players_to_server = []
                for player in players:
                    if connected_players[(player, server_idx)].x > 0.5:
                        connected_players_to_server.append(player)

                        network.graph.nodes[server_idx]['server']['game_server'] = 1
                        network.graph.nodes[player]['connected_to_server'] = server_idx

                connected_players_info[server_idx] = connected_players_to_server

        for player in players:
            assigned = False
            for server in potential_servers:
                if connected_players[(player, server)].x > 0.5:
                    network.previous_server_assignments[int(player[1:]) - 1] = server
                    assigned = True
                    break
            if not assigned:
                network.previous_server_assignments[int(player[1:]) - 1] = None

        
            # Print connected players for each server
            for server_idx, connected_players_list in connected_players_info.items():
                if connected_players_list:
                    for player in connected_players_list:
                        path = network.get_shortest_path(player, server_idx)
                        player_server_paths.append((player, server_idx, path))
                    if debug_prints:
                        logger.log(f"To server {server_idx} connected players ({len(connected_players_list)}) are: {', '.join(connected_players_list)}", save_log=False, print_to_console=False)
                else:
                    if debug_prints:
                        logger.log(f"To server {server_idx} no players are connected", save_log=False, print_to_console=False)
    else:
        logger.log("No optimal solution found.")
        return False

    network.connected_players_info = connected_players_info
    network.player_server_paths = player_server_paths
    return True

def interplayer_delay_migration(network: NetworkGraph, fix_servers, edge_servers, players, nr_of_servers, min_players_connected, max_connected_players, migration_cost, debug_prints):
    # Create a new Gurobi model
    model = grb.Model()
    if not debug_prints:
        # Set Gurobi parameter to suppress output
        model.setParam('OutputFlag', 0)

    potential_servers = fix_servers + edge_servers

    # Decision variables: binary variable indicating if a server is chosen
    server_selected = {}
    for server in potential_servers:
        server_selected[server] = model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

    # Maximum interplayer delay
    max_interplayer_delay = model.addVar(name='max_interplayer_delay')

    # Define a new set of decision variables representing connected players to servers
    connected_players = {(player, server): model.addVar(vtype=GRB.BINARY, name=f"player_{player}_connected_to_{server}")
                        for player in players for server in potential_servers}
    
    # 1. Constraint: Calculate maximum interplayer delay
    for server in potential_servers:
        for player1 in players:
            for player2 in players:
                if player1 != player2:
                    interplayer_delay = (
                        network.get_shortest_path_delay(player1, server) +
                        network.get_shortest_path_delay(player2, server) +
                        network.calculate_migration_cost(network.previous_server_assignments[int(player1[1:]) - 1], server, migration_cost) * connected_players[(player1, server)] +
                        network.calculate_migration_cost(network.previous_server_assignments[int(player2[1:]) - 1], server, migration_cost) * connected_players[(player2, server)]
                    )
                    # Add constraint based on selected servers
                    model.addConstr(
                        max_interplayer_delay >= interplayer_delay * (connected_players[(player1, server)] + connected_players[(player2, server)] - 1)
                    )

    # 2. Constraint: select only #nr_of_servers 
    model.addConstr(grb.quicksum(server_selected[server] for server in potential_servers) <= nr_of_servers)


    # 3. Constraints to ensure players are connected only to selected servers
    for player in players:
        model.addConstr(
            grb.quicksum(connected_players[(player, server)] for server in potential_servers) == 1,
            name=f"player_{player}_connected_to_one_selected_server"
        )
    for player in players:
        for server in potential_servers:
            model.addConstr(connected_players[(player, server)] <= server_selected[server])

    # 4. Constraint: Limit the number of connected players to each server
    for server in potential_servers:
        if network.is_core_server(server):
            max_players = 2 * max_connected_players
        else:
            max_players = max_connected_players

        model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) <= max_players,
            name=f"limit_connected_players_to_server_{server}"
        )

    # 5. Constraint: Ensure a minimum number of players connected to selected servers
    for server in potential_servers:
        model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) >= min_players_connected * server_selected[server],
            name=f"min_connected_players_to_server_{server}"
        )
    # 6. Constraint: Fix servers must remain active
    model.addConstr(
        grb.quicksum(server_selected[server] for server in fix_servers) >= len(fix_servers),
        name=f"core_server_{server}_active"
    )

    # Objective: Minimize the maximum interplayer delay
    model.setObjective(max_interplayer_delay, GRB.MINIMIZE)

    # Solve the optimization problem
    model.optimize()

    # Solve the optimization problem
    model.optimize()

    if model.status == GRB.OPTIMAL:
        logger.log(f"Model 'interplayer_delay_minimization' has found an optimal solution.", print_to_console=False)
        # Initialize player_server_paths_model_1 as an empty list
        player_server_paths = []

        # Dictionary to store connected players for each server
        connected_players_info = {server: [] for server in potential_servers}
        connected_players_info[None] = []

        # Retrieve the selected servers and connected players
        for server_idx in potential_servers:
            if server_selected[server_idx].x > 0.5:
                connected_players_to_server = []
                for player in players:
                    if connected_players[(player, server_idx)].x > 0.5:
                        connected_players_to_server.append(player)

                        network.graph.nodes[server_idx]['server']['game_server'] = 1
                        network.graph.nodes[player]['connected_to_server'] = server_idx

                connected_players_info[server_idx] = connected_players_to_server

        for player in players:
            assigned = False
            for server in potential_servers:
                if connected_players[(player, server)].x > 0.5:
                    network.previous_server_assignments[int(player[1:]) - 1] = server
                    assigned = True
                    break
            if not assigned:
                network.previous_server_assignments[int(player[1:]) - 1] = None

        
            # Print connected players for each server
            for server_idx, connected_players_list in connected_players_info.items():
                if connected_players_list:
                    for player in connected_players_list:
                        path = network.get_shortest_path(player, server_idx)
                        player_server_paths.append((player, server_idx, path))
                    if debug_prints:
                        logger.log(f"To server {server_idx} connected players ({len(connected_players_list)}) are: {', '.join(connected_players_list)}", save_log=False, print_to_console=False)
                else:
                    if debug_prints:
                        logger.log(f"To server {server_idx} no players are connected", save_log=False, print_to_console=False)
    else:
        logger.log("No optimal solution found.")
        return False

    network.connected_players_info = connected_players_info
    network.player_server_paths = player_server_paths
    return True

def qoe_optimization_initial(network: NetworkGraph, potential_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, debug_prints):
    logger.log("QoE optimization started", print_to_console=True)
    sum_model = grb.Model()
    if not debug_prints:
        # Set Gurobi parameter to suppress output
        sum_model.setParam('OutputFlag', 0)

    # Decision variables: binary variable indicating if a server is chosen
    server_selected = {}
    for server in potential_servers:
        server_selected[server] = sum_model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

    # Define a new set of decision variables representing connected players to servers
    connected_players = {(player, server): sum_model.addVar(vtype=GRB.BINARY, name=f"player_{player}_connected_to_{server}")
                        for player in players for server in potential_servers}

    # 1. Constraint: select only #nr_of_servers 
    sum_model.addConstr(grb.quicksum(server_selected[server] for server in potential_servers) <= nr_of_game_servers)

    # 2. Constraints to ensure players are connected only to selected servers
    for player in players:
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for server in potential_servers) == 1,
            name=f"player_{player}_connected_to_one_server"
        )
        for server in potential_servers:
            sum_model.addConstr(connected_players[(player, server)] <= server_selected[server])

    # 3. Constraint: Limit the number of connected players to each server
    for server in potential_servers:
        if network.is_core_server(server):
            max_players = 2 * max_connected_players
        else:
            max_players = max_connected_players
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) <= max_players,
            name=f"limit_connected_players_to_server_{server}"
        )
    # 4. Constraint: Ensure a minimum number of players connected to selected servers
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) >= min_players_connected * server_selected[server],
            name=f"min_connected_players_to_server_{server}"
        )
    
    # Objective function: maximize total qoe
    sum_model.setObjective(
        grb.quicksum(
            network.calculate_QoE(player, server) * connected_players[(player, server)]
            for player in players
            for server in potential_servers
        ),
        sense=GRB.MAXIMIZE,
    )

    # Solve the optimization problem
    sum_model.optimize()

    if sum_model.status == GRB.OPTIMAL:
        logger.log(f"Model 'delay_sum_migration' has found an optimal solution.", print_to_console=True)
        # Initialize player_server_paths_model_1 as an empty list
        player_server_paths_model_1 = []

        # Dictionary to store connected players for each server
        connected_players_info_model_1 = {server: [] for server in potential_servers}
        connected_players_info_model_1[None] = []

        # Retrieve the selected servers and connected players
        for server_idx in potential_servers:
            if server_selected[server_idx].x > 0.5:
                connected_players_to_server = []
                for player in players:
                    if connected_players[(player, server_idx)].x > 0.5:
                        connected_players_to_server.append(player)

                        network.graph.nodes[server_idx]['server']['game_server'] = 1
                        network.graph.nodes[player]['connected_to_server'] = server_idx

                connected_players_info_model_1[server_idx] = connected_players_to_server

        for player in players:
            assigned = False
            for server in potential_servers:
                if connected_players[(player, server)].x > 0.5:
                    network.previous_server_assignments[int(player[1:]) - 1] = server
                    assigned = True
                    break
            if not assigned:
                network.previous_server_assignments[int(player[1:]) - 1] = None

        
            # Print connected players for each server
            for server_idx, connected_players_list in connected_players_info_model_1.items():
                if connected_players_list:
                    for player in connected_players_list:
                        path = network.get_shortest_path(player, server_idx)
                        player_server_paths_model_1.append((player, server_idx, path))
                    if debug_prints:
                        logger.log(f"To server {server_idx} connected players ({len(connected_players_list)}) are: {', '.join(connected_players_list)}", save_log=False, print_to_console=False)
                else:
                    if debug_prints:
                        logger.log(f"To server {server_idx} no players are connected", save_log=False, print_to_console=False)
    else:
        logger.log("No optimal solution found.")
        return False

    network.connected_players_info = connected_players_info_model_1
    network.player_server_paths = player_server_paths_model_1
    return True

def qoe_optimization_migration(network: NetworkGraph, fix_servers, dynamic_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, migration_cost, debug_prints):
    logger.log("QoE optimization started", print_to_console=True)
    sum_model = grb.Model()
    if not debug_prints:
        # Set Gurobi parameter to suppress output
        sum_model.setParam('OutputFlag', 0)

    potential_servers = fix_servers + dynamic_servers

    # Decision variables: binary variable indicating if a server is chosen
    server_selected = {}
    for server in potential_servers:
        server_selected[server] = sum_model.addVar(vtype=GRB.BINARY, name=f"server_{server}_selected")

    # Define a new set of decision variables representing connected players to servers
    connected_players = {(player, server): sum_model.addVar(vtype=GRB.BINARY, name=f"player_{player}_connected_to_{server}")
                        for player in players for server in potential_servers}

    # 1. Constraint: select only #nr_of_servers 
    sum_model.addConstr(grb.quicksum(server_selected[server] for server in potential_servers) <= nr_of_game_servers)

    # 2. Constraints to ensure players are connected only to selected servers
    for player in players:
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for server in potential_servers) == 1,
            name=f"player_{player}_connected_to_one_server"
        )
        for server in potential_servers:
            sum_model.addConstr(connected_players[(player, server)] <= server_selected[server])

    # 3. Constraint: Limit the number of connected players to each server
    for server in potential_servers:
        if network.is_core_server(server):
            max_players = 2 * max_connected_players
        else:
            max_players = max_connected_players
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) <= max_players,
            name=f"limit_connected_players_to_server_{server}"
        )
    # 4. Constraint: Ensure a minimum number of players connected to selected servers
        sum_model.addConstr(
            grb.quicksum(connected_players[(player, server)] for player in players) >= min_players_connected * server_selected[server],
            name=f"min_connected_players_to_server_{server}"
        )

    # 5. Constraint: Fix servers must remain active
        sum_model.addConstr(
            grb.quicksum(server_selected[server] for server in fix_servers) >= len(fix_servers),
            name=f"core_server_{server}_active"
        )
    

    # Objective function: maximize total qoe while minimizing migration cost
    sum_model.setObjective(
        grb.quicksum(
            network.calculate_QoE(player, server) * connected_players[(player, server)]
            for player in players
            for server in potential_servers
        ) - grb.quicksum(
            network.calculate_migration_cost(network.previous_server_assignments[int(player[1:]) - 1], server, migration_cost) * connected_players[(player, server)]
            for player in players
            for server in potential_servers
            if network.previous_server_assignments[int(player[1:]) - 1]
        ),
        sense=GRB.MAXIMIZE,
    )

    # Solve the optimization problem
    sum_model.optimize()

    if sum_model.status == GRB.OPTIMAL:
        logger.log(f"Model 'delay_sum_migration' has found an optimal solution.", print_to_console=True)
        # Initialize player_server_paths_model_1 as an empty list
        player_server_paths_model_1 = []

        # Dictionary to store connected players for each server
        connected_players_info_model_1 = {server: [] for server in potential_servers}
        connected_players_info_model_1[None] = []

        # Retrieve the selected servers and connected players
        for server_idx in potential_servers:
            if server_selected[server_idx].x > 0.5:
                connected_players_to_server = []
                for player in players:
                    if connected_players[(player, server_idx)].x > 0.5:
                        connected_players_to_server.append(player)

                        network.graph.nodes[server_idx]['server']['game_server'] = 1
                        network.graph.nodes[player]['connected_to_server'] = server_idx

                connected_players_info_model_1[server_idx] = connected_players_to_server

        for player in players:
            assigned = False
            for server in potential_servers:
                if connected_players[(player, server)].x > 0.5:
                    network.previous_server_assignments[int(player[1:]) - 1] = server
                    assigned = True
                    break
            if not assigned:
                network.previous_server_assignments[int(player[1:]) - 1] = None

        
            # Print connected players for each server
            for server_idx, connected_players_list in connected_players_info_model_1.items():
                if connected_players_list:
                    for player in connected_players_list:
                        path = network.get_shortest_path(player, server_idx)
                        player_server_paths_model_1.append((player, server_idx, path))
                    if debug_prints:
                        logger.log(f"To server {server_idx} connected players ({len(connected_players_list)}) are: {', '.join(connected_players_list)}", save_log=False, print_to_console=False)
                else:
                    if debug_prints:
                        logger.log(f"To server {server_idx} no players are connected", save_log=False, print_to_console=False)
    else:
        logger.log("No optimal solution found.")
        return False

    network.connected_players_info = connected_players_info_model_1
    network.player_server_paths = player_server_paths_model_1
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
