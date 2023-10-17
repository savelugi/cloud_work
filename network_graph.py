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
        self.graph.add_nodes_from(nodes.keys())

    def connect_player_to_server(self, player_position, server_positions):
        # Legközelebbi szerver kiválasztása:
        distance, key = min_distance(player_position, server_positions)
        print("player position:")
        print(player_position)
        print("server_position")
        print(server_positions[key])
        self.graph.add_edge(player_position, server_positions[key], weight=distance)
    