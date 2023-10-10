import networkx

class ServerPlacementAlgorithm:
    def __init__(self, network_graph):
        self.graph = network_graph

    def calculate_distance(pos1, pos2):
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
    

    def connect_player_to_server(self, player_position: tuple, server_positions):
        # Legközelebbi szerver kiválasztása
        closest_server = min(server_positions, key=lambda server: abs(player_position[0] - float(server_positions[server][0])) + abs(player_position[1] - float(server_positions[server][1])))

        # Él hozzáadása a játékos és a legközelebbi szerver között
        distance = abs(player_position[0] - float(server_positions[closest_server][0])) + abs(player_position[1] - float(server_positions[closest_server][1]))
        self.graph.add_edge(player_position, closest_server, weight=distance)
    


