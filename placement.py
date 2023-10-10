import networkx
from utils.utils import *
class ServerPlacementAlgorithm:
    def __init__(self, network_graph):
        self.graph = network_graph
    

        
    def connect_player_to_server(self, player_position, server_positions):
        # Legközelebbi szerver kiválasztása:
        distance = min_distance(player_position, server_positions) 
        
        #self.graph.add_edge(player_position, closest_server, weight=distance)
        return self.graph
    


