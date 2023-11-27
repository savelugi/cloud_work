import networkx as nx
from utils import *

class NetworkGraph:
    def __init__(self):
        self.graph = nx.Graph()
        self.delay_cache = {}  # Initialize an empty cache

    def load_topology(self, topology_dir):
        self.graph =  nx.read_gml(topology_dir)

    def get_server_positions(self):
        server_positions = {}
        for node in self.graph.nodes(data=True):
            node_id = node[0]
            node_data = node[1]
            if 'Latitude' in node_data and 'Longitude' in node_data:
                latitude = float(node_data['Latitude'])
                longitude = float(node_data['Longitude'])
                server_positions[node_id] = (longitude, latitude)  # A pozíció sorrendje longitude, latitude
        return server_positions
    
    def add_nodes_from_keys(self, nodes):
        for node_name, coordinates in nodes.items():
            x, y = coordinates
            self.graph.add_node(node_name, Latitude=x, Longitude=y)
    
    def connect_player_to_server(self, players, player_position, server_positions):
        distance, key = min_distance(players[player_position], server_positions)
        key_list = list(server_positions.keys())
        self.graph.add_edge(player_position, key_list[int(key)], length=distance)

    def get_shortest_path_delay(self, node1, node2):
        # Check if the delay for the given nodes is already cached
        cached_delay = self.delay_cache.get((node1, node2))
        if cached_delay is not None:
            return cached_delay
        
        try:
            delay = nx.shortest_path_length(self.graph, node1, node2, weight='length')
            # Cache the computed delay for future use
            self.delay_cache[(node1, node2)] = delay
            self.delay_cache[(node2, node1)] = delay  # Assuming symmetric delays
            return delay
        except nx.NetworkXNoPath:
            # If there's no path between the nodes, cache it as infinite delay
            self.delay_cache[(node1, node2)] = float('inf')
            self.delay_cache[(node2, node1)] = float('inf')
            return float('inf')
    
    def get_shortest_path(self, node1, node2):
        try:
            path = nx.shortest_path(self.graph, node1, node2)
            return path
        except nx.NetworkXNoPath:
            print(f"No path between {node1} and {node2}!")
        
    def print_path_delay(self, node1, node2):
        try:
            delay = nx.shortest_path_length(self.graph, node1, node2, weight='length')
            print(f"delay {node1} <---> {node2} = {delay}")
            return delay
        except nx.NetworkXNoPath:
            # Ha nincs útvonal a két pont között
            return float('inf')

    def get_nodes(self):
        return(self.graph.nodes())
    
    def get_edges(self):
        return list(self.graph.edges())
    
    def print_node_positions(self):
        for node_id, position in self.graph.nodes(data=True):
            print(f"{node_id} : {position}")

    def print_edge_positions(self):
        for edge in self.graph.edges(data=True):
            print(f"{edge[0]} - {edge[1]} : {edge[2]}")
    
    def print_graph_positions(self):
        print("Nodes:")
        self.print_node_positions()

        print("\nEdges:")
        self.print_edge_positions()

    def save_graph_into_gml(self, file_path):
        nx.write_gml(self.graph, file_path)

    # Function to calculate interplayer delay metrics
def calculate_delay_metrics(self, connected_players_info, selected_servers, method_type):
    server_to_player_delays = []
    player_to_player_delays = []
    min_value = (0, 0, float('inf'))
    max_value = (0, 0, 0)

    for server_idx, connected_players_list in connected_players_info.items():
        if server_idx:
            for player in connected_players_list:
                server_to_player_delay = self.get_shortest_path_delay(player, server_idx)
                server_to_player_delays.append((player, server_idx, server_to_player_delay))

    for i in range(len(server_to_player_delays)):
        for j in range(i + 1, len(server_to_player_delays)):
            player_1, server_1, delay_1 = server_to_player_delays[i]
            player_2, server_2, delay_2 = server_to_player_delays[j]
            if player_1 != player_2:
                if server_1 != server_2:
                    ser_to_serv_delay = self.get_shortest_path_delay(server_1, server_2)
                    inter_player_delay = delay_1 + ser_to_serv_delay + delay_2
                else:
                    inter_player_delay = delay_1 + delay_2

                player_to_player_delays.append(inter_player_delay)

                if inter_player_delay < min_value[2]:
                    min_value = (player_1, player_2, inter_player_delay)
                if inter_player_delay > max_value[2]:
                    max_value = (player_1, player_2, inter_player_delay)

    # Calculate metrics
    delays_only = [delay for _, _, delay in server_to_player_delays]
    average_player_to_server_delay = sum(delays_only) / len(delays_only)
    average_player_to_player_delay = sum(player_to_player_delays) / len(player_to_player_delays)
    min_player_to_server_delay = min(delays_only)
    max_player_to_server_delay = max(delays_only)

    # Print the metrics
    print(f"\nThe {method_type} method selected servers are: {selected_servers}")
    print(f"Average player to server delay: {average_player_to_server_delay}")
    print(f"Minimum player to server delay: {min_player_to_server_delay}")
    print(f"Maximum player to server delay: {max_player_to_server_delay}")

    print(f"\nAverage interplayer delay: {average_player_to_player_delay}")
    print(f"Maximum interplayer delay: {max_value}")
    print(f"Minimum interplayer delay: {min_value}")