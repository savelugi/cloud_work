import networkx as nx
from utils.utils import *

class NetworkGraph:
    def __init__(self):
        self.graph = nx.Graph()

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
        try:
            delay = nx.shortest_path_length(self.graph, node1, node2, weight='length')
            return delay
        except nx.NetworkXNoPath:
            # Ha nincs útvonal a két pont között
            return float('inf')
        
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