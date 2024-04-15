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
    
    def add_players(self, nodes):
        for node_name, node_info in nodes.items():
            x, y = node_info['position']
            node_parameters = {
                #'Longitude': x,
                #'Latitude': y,
                'position': node_info['position'],
                'device_type': node_info['device_type'],
                'game': node_info['game'],
                'ping_preference': node_info['ping_preference'],
                'video_quality_preference': node_info['video_quality_preference']
            }
            self.graph.add_node(node_name, **node_parameters)

    
    def connect_player_to_server(self, players, player_position, server_positions):
        distance, key = min_distance(players[player_position]['position'], server_positions)
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

    def get_max_server_to_server_delay(self, servers):
        max_delay = 0
        between = ()
        for server1 in servers:
            for server2 in servers:
                if server1 != server2:
                    delay = self.get_shortest_path_delay(server1, server2)
                    if delay > max_delay:
                        max_delay = delay
                        between = (server1, server2)
        return [max_delay, between]
    
    def save_graph(self, player_server_paths, servers, connected_players_info, save_name):
        selected_servers = ()
        for server_idx, connected_players_list in connected_players_info.items():
            if connected_players_list:
                selected_servers.append(server_idx)

        # Add node colors and edge colors as attributes
        node_colors = {node: 'yellow' if node in selected_servers else 'blue' if node in servers else 'g' for node in self.graph.nodes()}
        
        # Initialize edge colors
        edge_colors = {edge: 'black' for edge in self.graph.edges()}

        # Set edge colors to red for edges in player+server_paths
        for _, _, path in player_server_paths:
            edges = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
            for edge in edges:
                edge_colors[edge] = 'red'

        # Set node and edge attributes for colors
        nx.set_node_attributes(self.graph, node_colors, 'color')
        nx.set_edge_attributes(self.graph, edge_colors, 'color')

        # Save the graph to a GML file
        nx.write_gml(self.graph, save_name+".gml")

    def calculate_qoe_metrics(self, connected_players_info, server_to_player_delay_list, config_preferences):
        player_score = {}

        ping_weight = float(config_preferences['ping_weight'])
        video_quality_weight = float(config_preferences['video_quality_weight'])


        for player, server, ping_act in server_to_player_delay_list:
            ping_pref = self.graph.nodes[player]['ping_preference']
            ping_diff_score = calculate_ping_score(ping_act, ping_pref)

            # the lower the actual ping, the bigger the ping score
            ping_act_score = 100 * 1 / ping_act

            if self.graph.nodes[server]['server']['gpu'] == '1':
                video_quality_diff_score = 0
            else:
                video_quality_diff_score = 1

            player_score[player] = (ping_weight * (ping_act_score + ping_diff_score)) + (video_quality_weight * video_quality_diff_score) 

        return player_score
        
    # Function to calculate interplayer delay metrics
    def calculate_delays(self, connected_players_info, method_type, print):
        selected_servers = []
        server_to_player_delays = []
        player_to_player_delays = []
        min_value = (0, 0, float('inf'))
        max_value = (0, 0, 0)

        for server_idx, connected_players_list in connected_players_info.items():
            if connected_players_list:
                for player in connected_players_list:
                    server_to_player_delay = self.get_shortest_path_delay(player, server_idx)
                    server_to_player_delays.append((player, server_idx, server_to_player_delay))

                selected_servers.append(server_idx)

        for i in range(len(server_to_player_delays)):
            for j in range(i + 1, len(server_to_player_delays)):
                player_1, server_1, delay_1 = server_to_player_delays[i]
                player_2, server_2, delay_2 = server_to_player_delays[j]
                if player_1 != player_2:
                    if server_1 == server_2:
                        inter_player_delay = delay_1 + delay_2

                    player_to_player_delays.append(inter_player_delay)

                    if inter_player_delay < min_value[2]:
                        min_value = (player_1, player_2, inter_player_delay)
                    if inter_player_delay > max_value[2]:
                        max_value = (player_1, player_2, inter_player_delay)

        # Calculate metrics
        delays_only = [delay for _, _, delay in server_to_player_delays]
        average_player_to_server_delay = round(sum(delays_only) / len(delays_only),2)
        min_player_to_server_delay = round(min(delays_only),2)
        max_player_to_server_delay = round(max(delays_only),2)

        average_player_to_player_delay = round(sum(player_to_player_delays) / len(player_to_player_delays),2)
        min_player_to_player_delay = round(min_value[2],2)
        max_player_to_player_delay = round(max_value[2],2)

        if print:
            # Print the metrics
            print(f"\nThe {method_type} method selected servers are: {selected_servers}")
            print(f"Average player to server delay: {average_player_to_server_delay}")
            print(f"Minimum player to server delay: {min_player_to_server_delay}")
            print(f"Maximum player to server delay: {max_player_to_server_delay}")

            print(f"\nAverage interplayer delay: {average_player_to_player_delay}")
            print(f"Maximum interplayer delay: {max_value}")
            print(f"Minimum interplayer delay: {min_value}")

        return [average_player_to_server_delay, min_player_to_server_delay, max_player_to_server_delay,
            average_player_to_player_delay, min_player_to_player_delay, max_player_to_player_delay, len(selected_servers)], server_to_player_delays
