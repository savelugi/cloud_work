import gurobipy as grb
from gurobipy import GRB
from network_graph import *
from globvars import logger


class BaseOptimizationModel:
    def __init__(self, network, potential_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, debug_prints):
        self.network = network
        self.potential_servers = potential_servers
        self.players = players
        self.nr_of_game_servers = nr_of_game_servers
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
        # 1. Constraint: select only nr_of_servers 
        self.model.addConstr(
            grb.quicksum(self.server_selected[server] for server in self.potential_servers) <= self.nr_of_game_servers
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

class DelaySumInitialOptimization(BaseOptimizationModel):
    def __init__(self, network, potential_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, debug_prints):
        super().__init__(network, potential_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, debug_prints)
        
        # Objective function: minimize sum of delays
        self.model.setObjective(
            grb.quicksum(
                self.network.get_shortest_path_delay(player, server) * self.connected_players[(player, server)]
                for player in self.players for server in self.potential_servers
            ),
            sense=GRB.MINIMIZE
        )

class DelaySumMigrationOptimization(BaseOptimizationModel):
    def __init__(self, network, fix_servers, dynamic_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, migration_cost, debug_prints):
        potential_servers = fix_servers + dynamic_servers
        self.fix_servers = fix_servers
        self.migration_cost_val = migration_cost
        
        super().__init__(network, potential_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, debug_prints)
        
        # Constraint: fix servers must remain selected
        self.model.addConstr(
            grb.quicksum(self.server_selected[server] for server in self.fix_servers) >= len(self.fix_servers)
        )
        
        self.model.setObjective(
            grb.quicksum(
                self.network.get_shortest_path_delay(player, server) * self.connected_players[(player, server)]
                for player in self.players for server in self.potential_servers
            ) + grb.quicksum(
                self.network.calculate_migration_cost(self.network.previous_server_assignments[int(player[1:]) - 1], server, self.migration_cost_val) * self.connected_players[(player, server)]
                for player in self.players for server in self.potential_servers
                if self.network.previous_server_assignments[int(player[1:]) - 1]
            ),
            sense=GRB.MINIMIZE
        )


class InterplayerDelayInitialOptimization(BaseOptimizationModel):
    def __init__(self, network, potential_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, debug_prints):
        super().__init__(network, potential_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, debug_prints)
        
        self.max_interplayer_delay = self.model.addVar(name='max_interplayer_delay')

        for s in self.potential_servers:
            for p1 in self.players:
                for p2 in self.players:
                    if p1 != p2:
                        interplayer_delay = (
                            self.network.get_shortest_path_delay(p1, s) + 
                            self.network.get_shortest_path_delay(p2, s)
                        )
                        self.model.addConstr(
                            self.max_interplayer_delay >= interplayer_delay * (self.connected_players[(p1, s)] + self.connected_players[(p2, s)] - 1)
                        )

        self.model.setObjective(self.max_interplayer_delay, GRB.MINIMIZE)

class InterplayerDelayMigrationOptimization(BaseOptimizationModel):
    def __init__(self, network, fix_servers, dynamic_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, migration_cost, debug_prints):
        potential_servers = fix_servers + dynamic_servers
        self.fix_servers = fix_servers
        self.migration_cost_val = migration_cost

        super().__init__(network, potential_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, debug_prints)
        
        self.max_interplayer_delay = self.model.addVar(name='max_interplayer_delay')

        # Fix servers must remain selected
        self.model.addConstr(
            grb.quicksum(self.server_selected[s] for s in self.fix_servers) >= len(self.fix_servers)
        )

        for s in self.potential_servers:
            for p1 in self.players:
                for p2 in self.players:
                    if p1 != p2:
                        interplayer_delay = (
                            self.network.get_shortest_path_delay(p1, s) +
                            self.network.get_shortest_path_delay(p2, s) +
                            self.network.calculate_migration_cost(self.network.previous_server_assignments[int(p1[1:]) - 1], s, self.migration_cost_val)*self.connected_players[(p1, s)] +
                            self.network.calculate_migration_cost(self.network.previous_server_assignments[int(p2[1:]) - 1], s, self.migration_cost_val)*self.connected_players[(p2, s)]
                        )
                        self.model.addConstr(
                            self.max_interplayer_delay >= interplayer_delay * (self.connected_players[(p1, s)] + self.connected_players[(p2, s)] - 1)
                        )

        self.model.setObjective(self.max_interplayer_delay, GRB.MINIMIZE)

class QoEOptimizationInitial(BaseOptimizationModel):
    def __init__(self, network, potential_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, debug_prints):
        super().__init__(network, potential_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, debug_prints)
        
        # Objective function: Maximize QoE 
        self.model.setObjective(
            grb.quicksum(
                self.network.calculate_QoE(player, server) * self.connected_players[(player, server)]
                for player in self.players for server in self.potential_servers
            ),
            sense=GRB.MAXIMIZE
        )

class QoEOptimizationMigration(BaseOptimizationModel):
    def __init__(self, network, fix_servers, dynamic_servers, players, nr_of_game_servers, min_players_connected, max_connected_players, migration_cost, debug_prints):
        potential_servers = fix_servers + dynamic_servers
        self.fix_servers = fix_servers
        self.migration_cost_val = migration_cost
        super().__init__(network, potential_servers, players, nr_of_game_servers,  min_players_connected, max_connected_players, debug_prints)

        # Fix servers must remain selected
        self.model.addConstr(
            grb.quicksum(self.server_selected[s] for s in self.fix_servers) >= len(self.fix_servers)
        )

        # Objective function: Maximize QoE while minimizing migration cost
        self.model.setObjective(
            grb.quicksum(
                self.network.calculate_QoE(player, server) * self.connected_players[(player, server)]
                for player in self.players for server in self.potential_servers
            ) - grb.quicksum(
                self.network.calculate_migration_cost(self.network.previous_server_assignments[int(p[1:]) - 1], s, self.migration_cost_val) * self.connected_players[(p, s)]
                for p in self.players for s in self.potential_servers
                if self.network.previous_server_assignments[int(p[1:]) - 1]
            ),
            sense=GRB.MAXIMIZE
        )