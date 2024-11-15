import networkx as nx
import os
from utils import *
import matplotlib.pyplot as plt
import globvars
from globvars import logger

class NetworkGraph:
    def __init__(self, modelname="", config=None, num_gen_players=0):
        self.modelname = modelname
        self.delay_cache = {}  # Initialize an empty cache
        self.connected_players_info = {}
        self.player_server_paths = []
        self.delay_metrics = []
        self.previous_server_to_player_delays = None
        self.server_to_player_delays = []
        self.previous_selected_servers = None
        self.selected_servers = []
        self.best_solution = []
        self.previous_server_assignments = []
        
        if config is None:
            self.graph = nx.Graph()
            self.server_positions = self.get_server_positions()
        else:
            self.seed = int(config['Weights']['seed'])
            self.config = config
            topology_file = get_topology_filename(config)
            self.graph = nx.read_gml(topology_file)
            self.server_positions = self.get_server_positions()
            self._only_servers = list(self.graph.nodes)
            self.edge_servers = self.get_edge_servers()
            

            ranges = get_lat_long_range(config)
            if ranges is not None:
                self.long_range, self.lat_range = ranges
            else:
                print("Error: Unsupported topology")        
            if num_gen_players > 0:
                self.num_players = num_gen_players
                self.players = generate_players(num_gen_players, self.long_range, self.lat_range, self.seed)
                self.add_players_to_graph(self.players)
                self.connect_players_to_closest_servers(self.players)
                self.previous_server_assignments = [None] * len(self.players) * 10


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
                server_positions[node_id] = (longitude, latitude)
        return server_positions
    
    def get_closest_servers(self, node):
        closest_servers = []
        neighbours = list(self.graph.neighbors(node))

        if neighbours is None:
            print("Node has no neighbours!")
            return None
        
        for neighbour in neighbours:
            if neighbour.isdigit():
                closest_servers.append(neighbour)
                
        return closest_servers
    
    def add_random_player_to_graph(self, player=None, seed=None):
        if seed is not None:
            random.seed(seed)
        # if player name wasn't given, we increment the last player name
        if player is None:
            player_keys = list(self.players.keys())
            player = f"P{int(player_keys[-1][1:]) + 1}"

        player_params = generate_player_params(self.long_range, self.lat_range, seed)
        
        self.graph.add_node(player, **player_params)
        
        self.players[player] = {
            'Longitude': player_params['Longitude'],
            'Latitude': player_params['Latitude'],
            'device_type': player_params['device_type'],
            'game': player_params['game'],
            'ping_preference': player_params['ping_preference'],
            'video_quality_preference': player_params['video_quality_preference'],
            'connected_to_server': player_params['connected_to_server']
        }

        self.connect_player_to_closest_server(player, self.server_positions)
        self.clear_delay_cache()
        self.server_to_player_delays.append((player, None, None))
        logger.log_function(f"Added player {player} to the network graph!")

    
    def add_players_to_graph(self, nodes):
        for node_name, node_info in nodes.items():
            node_parameters = {
                'Longitude': node_info['Longitude'],
                'Latitude': node_info['Latitude'],                
                'device_type': node_info['device_type'],
                'game': node_info['game'],
                'ping_preference': node_info['ping_preference'],
                'video_quality_preference': node_info['video_quality_preference'],
                'connected_to_server': node_info['connected_to_server']
            }
            self.graph.add_node(node_name, **node_parameters)

    def remove_player_from_graph(self, player, debug_prints=False):
        if debug_prints:
            logger.log_function(f"Trying to remove player {player} from the network graph!")
        #TODO: check if we need to remove anything else from the network structures
        if self.remove_player_from_player_dictionary(player, debug_prints=True) is False:
            return
        self.remove_server_player_delays(player)
        self.graph.remove_node(player)
        logger.log_function(f"Removed player {player} from the network graph!")

        
    def connect_players_to_closest_servers(self, players):
        for player in players:
            self.connect_player_to_closest_server(player, self.server_positions)

    
    def connect_player_to_closest_server(self, player, server_positions):
        distance, key = min_distance((self.graph.nodes[player]['Longitude'], self.graph.nodes[player]['Latitude']), server_positions)
        key_list = list(server_positions.keys())
        closest_server = key_list[int(key)]

        # we check if the player is already connected to the closest server, 
        # if not we remove the old connection and connect the new closest
        current_server = None
        neighbours = list(self.graph.neighbors(player))

        if neighbours:
            current_server = neighbours[0]

        if current_server:
            if current_server != closest_server:
                self.graph.remove_edge(player, current_server)
                self.graph.add_edge(player, closest_server, length=distance)
            else:
                return
        else:
            self.graph.add_edge(player, closest_server, length=distance)

    def is_edge_server(self, server):
        if self.graph.nodes[server]['server']['type'] == "edge":
            return True
        else:
            return False
        
    def get_edge_servers(self):
        edge_servers = []
        for server in self._only_servers:
            if self.is_edge_server(server):
                edge_servers.append(server)
        
        return edge_servers
                
    def update_player_positions(self, debug_prints, seed):
        moved_players = move_players_randomly(
                                    players=self.players, 
                                    move_probability=0.3, 
                                    max_move_dist=10, 
                                    x_range=self.long_range, 
                                    y_range=self.lat_range, 
                                    seed=seed, 
                                    debug_prints=debug_prints)

        for player_id, player_data in moved_players.items():
            self.graph.nodes[player_id]['Longitude'] = player_data['Longitude']
            self.graph.nodes[player_id]['Latitude'] = player_data['Latitude']

        self.connect_players_to_closest_servers(moved_players)
        self.color_graph()
        self.clear_delay_cache()

    def move_player_horizontally(self, player_id, dist):
        x_min, x_max = self.lat_range

        # Staying between the boundaries
        new_x = min(max(self.graph.nodes[player_id]['Longitude'] + dist, x_min), x_max)
        
        if new_x != x_max or new_x != x_min:
            globvars.move_counter += 1

            logger.log_function(
                f"Moving player {player_id}: from ({round(self.graph.nodes[player_id]['Longitude'], 2)}, "
                f"{round(self.graph.nodes[player_id]['Latitude'], 2)}) to ({round(new_x, 2)}, "
                f"{round(self.graph.nodes[player_id]['Latitude'], 2)})"
            )

        self.graph.nodes[player_id]['Longitude'] = new_x
        self.connect_player_to_closest_server(player_id, self.server_positions)
        self.clear_delay_cache()
      


    def move_player_vertically(self, player_id, dist):
        y_min, y_max = self.long_range

        # Staying between the boundaries
        new_y = min(max(self.graph.nodes[player_id]['Latitude'] + dist, y_min), y_max)
        
        if new_y != y_max or new_y != y_min:
            globvars.move_counter += 1

            logger.log_function(
                f"Moving player {player_id}: from ({round(self.graph.nodes[player_id]['Longitude'], 2)}, "
                f"{round(self.graph.nodes[player_id]['Latitude'], 2)}) to "
                f"({round(self.graph.nodes[player_id]['Longitude'], 2)}, {round(new_y, 2)})"
            )


        self.graph.nodes[player_id]['Latitude'] = new_y

        self.connect_player_to_closest_server(player_id, self.server_positions)
        self.clear_delay_cache()

    def move_player_diagonally(self, player_id, dist):
        # needed for correct counting
        old_move_counter = globvars.move_counter

        if player_id not in self.players:
            logger.log_function(f"Player {player_id} is not amongst the players returning!")
            return
        
        self.move_player_horizontally(player_id, dist)
        self.move_player_vertically(player_id, dist)

        # count diagonal move as one
        if globvars.move_counter - old_move_counter == 2:
            globvars.move_counter -= 1

    def migrate_edge_servers_if_beneficial(self, player):
       # TODO: very csunya, ne igy csinald!#############
        from mutation import convert_ILP_to_chromosome, chromosome_to_uniform_population

        current_server = self.graph.nodes[player]['connected_to_server']

        if self.server_to_player_delays is None:
            print("Server to player delays wasn't calculated yet!")
            return
        
        for playerinlist, server, latency in self.server_to_player_delays:
            if player == playerinlist:
                current_latency = latency

        
        chromosome_to_uniform_population(convert_ILP_to_chromosome(self.server_to_player_delays))


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

    def clear_delay_cache(self):
        # this can be done better (deleting only the moved players from the delay cache)
        return(self.delay_cache.clear())
    
    def clear_game_servers(self):
        # this can be done better if we are clearing only the field from the moved servers
        # the game_server is initialized to -1 so by setting it to 0 we know that it was a game server at some point
        for srv_idx in self._only_servers:
            if self.graph.nodes[srv_idx]['server']['game_server'] == 1:
                self.graph.nodes[srv_idx]['server']['game_server'] = 0
            

    def print_path_delay(self, node1, node2):
        try:
            delay = nx.shortest_path_length(self.graph, node1, node2, weight='length')
            print(f"delay {node1} <---> {node2} = {delay}")
            return delay
        except nx.NetworkXNoPath:
            # Ha nincs útvonal a két pont között
            return float('inf')

    def get_nodes(self, data=False):
        return(self.graph.nodes(data=data))
    
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
    
    def set_player_server_metrics(self, solution):
        connected_players_to_server = {}
        for player_index, server_index in enumerate(solution):
            if server_index not in connected_players_to_server:
                connected_players_to_server[server_index] = []

            if server_index != -1:
                connected_players_to_server[server_index].append(f"P{player_index+1}")
                self.graph.nodes[str(server_index)]['server']['game_server'] = 1
                self.graph.nodes[f"P{player_index+1}"]['connected_to_server'] = server_index


        player_server_paths = []
        for server_idx, connected_players_list in connected_players_to_server.items():
            if connected_players_list:
                for player in connected_players_list:
                    path = self.get_shortest_path(player, server_idx)
                    player_server_paths.append((player, server_idx, path))

        self.connected_players_info = connected_players_to_server
        self.player_server_paths = player_server_paths

    def calculate_player_migrations(self):
        if not self.previous_server_to_player_delays:
            return 0
        
        migration_count = 0

        for curr_player, curr_server, _ in self.server_to_player_delays:
            for prev_player, prev_server, _ in self.previous_server_to_player_delays:
                if prev_player == curr_player and prev_server != curr_server:
                    migration_count += 1

        return migration_count
    
    def calculate_server_migrations(self):
        if not self.previous_selected_servers:
            return 0
            
        migration_count = 0

        set_prev = set(self.previous_selected_servers)
        set_curr = set(self.selected_servers)

        migration_count = len(set_curr.symmetric_difference(set_prev))

        return migration_count
    
    def calculate_migration_cost(self, old_server, new_server):
        migration_cost_multiplier = 100000

        if old_server:
            if old_server != new_server:
                return self.get_shortest_path_delay(old_server, new_server) * migration_cost_multiplier
            else:
                return 0
        else:
            #this is the case when a new player was added recently to the network, and it is being connected to a server
            return 0

    
    def save_graph(self, save_name, params):
        save_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "saves/")
        topology = self.config['Topology']['topology']

        save_path = save_dir + save_name + '_' + topology + "/"

        num_players, nr_of_servers, min_players_connected, max_connected_players, max_allowed_delay = params

        dir_name = topology + '_' + self.modelname + '_' + str(num_players)
        save_name = dir_name + "_" + str(nr_of_servers) + "_" + str(min_players_connected) + "_" + str(max_connected_players)
        folder_path = os.path.join(save_path, dir_name)  # Assuming you want to create the folder in the current directory
        
        # Check if the directory exists, if not, create it
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        full_save_path = os.path.join(folder_path, save_name)

        # Color the graph nodes and edges before saving
        self.color_graph()

        # Save the graph to a GML file
        nx.write_gml(self.graph, full_save_path+".gml")

        return save_path
    
    def color_graph(self):
        selected_servers = []
        for server_idx, connected_players_list in self.connected_players_info.items():
            if connected_players_list:
                selected_servers.append(server_idx)

        # Add node colors and edge colors as attributes
        node_colors = {}
        for node in self.graph.nodes():
            if node in selected_servers:
                node_colors[node] = 'red'
            elif node in self._only_servers:
                node_colors[node] = 'blue'
            else:
                node_colors[node] = 'green'
        
        # Initialize edge colors
        edge_colors = {edge: 'black' for edge in self.graph.edges()}

        # Set edge colors to red for edges in player+server_paths
        for _, _, path in self.player_server_paths:
            edges = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
            for edge in edges:
                edge_colors[edge] = 'red'

        # Set node and edge attributes for colors
        nx.set_node_attributes(self.graph, node_colors, 'color')
        nx.set_edge_attributes(self.graph, edge_colors, 'color')


    def save_ga_graph(self, save_name, params):
        save_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "saves/")
        topology = self.config['Topology']['topology']

        save_path = save_dir  + 'ga' + save_name + '_' + topology + "/"

        num_players, nr_of_servers, max_players_connected, mutation_rate, generation_size, tournament_size = params

        dir_name = topology + '_' + self.modelname + '_' + str(num_players)
        save_name = dir_name + "_" + str(mutation_rate) + "_" + str(generation_size) + "_" + str(nr_of_servers)
        folder_path = os.path.join(save_path, dir_name)  # Assuming you want to create the folder in the current directory
        
        # Check if the directory exists, if not, create it
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        full_save_path = os.path.join(folder_path, save_name)

        selected_servers = []
        for server_idx, connected_players_list in self.connected_players_info.items():
            if connected_players_list:
                selected_servers.append(server_idx)

        # Add node colors and edge colors as attributes
        node_colors = {node: 'yellow' if node in selected_servers else 'blue' if node in self._only_servers else 'green' for node in self.graph.nodes()}
        
        # Initialize edge colors
        edge_colors = {edge: 'black' for edge in self.graph.edges()}

        # Set edge colors to red for edges in player+server_paths
        for _, _, path in self.player_server_paths:
            edges = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
            for edge in edges:
                edge_colors[edge] = 'red'

        # Set node and edge attributes for colors
        nx.set_node_attributes(self.graph, node_colors, 'color')
        nx.set_edge_attributes(self.graph, edge_colors, 'color')

        # Save the graph to a GML file
        nx.write_gml(self.graph, full_save_path+".gml")

        return save_path

    def calculate_qoe_metrics(self):
        player_scores = 0
        config_preferences = self.config['Weights']
        ping_weight = float(config_preferences['ping_weight'])
        video_quality_weight = float(config_preferences['video_quality_weight'])


        for player, server, ping_act in self.server_to_player_delays:
            ping_pref = self.graph.nodes[player]['ping_preference']
            ping_diff_score = calculate_ping_score(ping_act, ping_pref)

            # the lower the actual ping, the bigger the ping score
            ping_act_score = 100 * 1 / ping_act

            if self.graph.nodes[server]['server']['gpu'] == '1':
                video_quality_diff_score = 0
            else:
                video_quality_diff_score = 1

            player_scores += (ping_weight * (ping_act_score + ping_diff_score)) + (video_quality_weight * video_quality_diff_score) 

        self.delay_metrics.append(player_scores)
        return True
        
    # Function to calculate interplayer delay metrics
    def calculate_delays(self, method_type, debug_prints):
        self.previous_server_to_player_delays = self.server_to_player_delays
        self.previous_selected_servers = self.selected_servers

        selected_servers = []
        server_to_player_delays = []
        player_to_player_delays = []
        min_value = (0, 0, float('inf'))
        max_value = (0, 0, 0)
        #PLAYER_LOC = 1, DELAY_LOC = 3
        SERVER_LOC = 2
        

        for server_idx, connected_players_list in self.connected_players_info.items():
            if connected_players_list:
                selected_servers.append(server_idx)

                for player in connected_players_list:
                    server_to_player_delay = self.get_shortest_path_delay(player, server_idx)
                    server_to_player_delays.append((player, server_idx, server_to_player_delay))

                if debug_prints:
                    logger.log(f"To server {server_idx} connected players are: {', '.join(connected_players_list)}")

        for i in range(len(server_to_player_delays)):
            for j in range(i + 1, len(server_to_player_delays)):
                player_1, server_1, delay_1 = server_to_player_delays[i]
                player_2, server_2, delay_2 = server_to_player_delays[j]
                if player_1 != player_2:
                    if server_1 == server_2:
                        inter_player_delay = delay_1 + delay_2
                        player_to_player_delays.append(inter_player_delay)

                        if inter_player_delay < min_value[SERVER_LOC]:
                            min_value = (player_1, player_2, inter_player_delay)
                        if inter_player_delay > max_value[SERVER_LOC]:
                            max_value = (player_1, player_2, inter_player_delay)

        # Calculate metrics
        delays_only = [delay for _, _, delay in server_to_player_delays]
        average_player_to_server_delay = round(sum(delays_only) / len(delays_only),2)
        min_player_to_server_delay = round(min(delays_only),2)
        max_player_to_server_delay = round(max(delays_only),2)

        average_player_to_player_delay = round(sum(player_to_player_delays) / len(player_to_player_delays),2)
        min_player_to_player_delay = round(min_value[2],2)
        max_player_to_player_delay = round(max_value[2],2)

        self.delay_metrics = [average_player_to_server_delay, min_player_to_server_delay, max_player_to_server_delay,
                              average_player_to_player_delay, min_player_to_player_delay, max_player_to_player_delay,
                              len(selected_servers)]
        self.server_to_player_delays = server_to_player_delays
        self.selected_servers = selected_servers

        if debug_prints:
            # Log the metrics
            logger.log(f"The {method_type} method selected servers are: {selected_servers}")
            logger.log(f"Average player to server delay: {average_player_to_server_delay}")
            logger.log(f"Minimum player to server delay: {min_player_to_server_delay}")
            logger.log(f"Maximum player to server delay: {max_player_to_server_delay}")
            logger.log(f"Average interplayer delay: {average_player_to_player_delay}")
            logger.log(f"Maximum interplayer delay: {max_value}")
            logger.log(f"Minimum interplayer delay: {min_value}")
            logger.log(f"Number of player migrations: {self.calculate_player_migrations()}")
            logger.log(f"Number of server migrations: {self.calculate_server_migrations()}")

        logger.log(f"{method_type} optimization finished.")
        logger.log('--------------------------------------------------------------')


        return True
        
    def calculate_player_server_connections_from_gml(self):
        connected_players_to_server = {}
        player_server_paths = []

        for node in self.graph.nodes():
            if 'server' in self.graph.nodes[node]:
                server_data = self.graph.nodes[node]['server']
                if 'game_server' in server_data and server_data['game_server'] == 1:
                    if node not in connected_players_to_server:
                        connected_players_to_server[node] = []
        
        for node_id, node_attrs in self.graph.nodes(data=True):
            if 'connected_to_server' in node_attrs:
                connected_server_id = node_attrs['connected_to_server']
                connected_players_to_server[connected_server_id].append(node_id)


        for server_idx, connected_players_list in connected_players_to_server.items():
            if connected_players_list:
                for player in connected_players_list:
                    path = self.get_shortest_path(player, server_idx)
                    player_server_paths.append((player, server_idx, path))

        self.connected_players_info = connected_players_to_server
        self.player_server_paths = player_server_paths
        return True
    
    def remove_server_player_delays(self, player):
        for player_id, server, delay in self.server_to_player_delays:
            if player_id == player:
                self.server_to_player_delays.remove((player_id, server, delay))
                # maybe this should be removed too
                #self.player_server_paths.remove((player_id, server, self.get_shortest_path(player, server)))
                return
            
        # We shouldn't get here
        print(f"Player {player} wasn't found in the list!")

    def remove_player_from_player_dictionary(self, player, debug_prints=None):
        #Returns True if the player was found and removed
        removed_player = self.players.pop(player, None)
        if removed_player is None:
            if debug_prints:
                logger.log_function(f"Player {player} wasn't found in the player dictionary!")
            return False
        else:
            return True
    

    def draw_graph(self, title, node_size=200, edge_width_factor=1.0, show_edge_labels=False, figsize=(10, 6), save=False, save_dir=None):

        graph = self.graph
        # Get node and edge attributes for colors
        node_colors = nx.get_node_attributes(graph, 'color')
        edge_colors = nx.get_edge_attributes(graph, 'color')
        
        # Set edge widths based on edge color
        edge_width = [2.0 * edge_width_factor if edge_colors[edge] == 'red' else 1.0 * edge_width_factor for edge in graph.edges()]
        
        # Define node positions and sizes using Latitude, Longitude, and server type attributes
        pos = {}
        node_sizes = []
        for server in self._only_servers:
            if graph.nodes[server]['server']['type'] == 'core':
                node_sizes.append(node_size * 5)
            elif graph.nodes[server]['server']['type'] == 'edge':
                node_sizes.append(node_size * 3)
            # get the lat and long values for plot drawing
            if 'Latitude' in graph.nodes[server] and 'Longitude' in graph.nodes[server]:
                pos[server] = (float(graph.nodes[server]['Longitude']), float(graph.nodes[server]['Latitude']))


        for player_idx, _ in self.players.items():
            node_sizes.append(node_size)
            # get the lat and long values for plot drawing
            if 'Latitude' in graph.nodes[player_idx] and 'Longitude' in graph.nodes[player_idx]:
                pos[player_idx] = (float(graph.nodes[player_idx]['Longitude']), float(graph.nodes[player_idx]['Latitude']))


        # Plot the graph
        plt.figure(figsize=figsize)  # Ábra méretének beállítása

        nx.draw(graph, pos, with_labels=True, node_color=list(node_colors.values()), edge_color=list(edge_colors.values()), node_size=node_sizes, width=edge_width)
        # Optionally display edge labels for distances
        if show_edge_labels:
            edge_labels = {(player, server): round(graph[player][server]["length"],1) for player, server in graph.edges()}
            nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels)

        plt.title(title, y=-0.01, fontsize="19")
        if save:
            plt.savefig(save_dir + '/' + title + '.png')

    def display_plots(self):
        plt.show()
