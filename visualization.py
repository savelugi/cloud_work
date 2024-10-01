import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import random
import seaborn as sns
from utils import *

model_columns = {
    "SUM": ['average_player_to_server_delay_sum', 'min_player_to_server_delay_sum', 'max_player_to_server_delay_sum',
            'average_player_to_player_delay_ipd', 'min_player_to_player_delay_sum', 'max_player_to_player_delay_sum',
            'nr_of_selected_servers_sum', 'sim_time_sum'],
    "IPD": ['average_player_to_server_delay_ipd', 'min_player_to_server_delay_ipd', 'max_player_to_server_delay_ipd',
            'average_player_to_player_delay_ipd', 'min_player_to_player_delay_ipd', 'max_player_to_player_delay_ipd',
            'nr_of_selected_servers_ipd', 'sim_time_ipd'],
    "GEN": ['average_player_to_server_delay_gen', 'min_player_to_server_delay_gen', 'max_player_to_server_delay_gen',
            'average_player_to_player_delay_gen', 'min_player_to_player_delay_gen', 'max_player_to_player_delay_gen',
            'nr_of_selected_servers_gen', 'sim_time_gen']
}

class Visualization:
    def __init__(self, network_graph):
        self.network_graph = network_graph

    def draw_graph(self, title, node_size=200, edge_width_factor=1.0, show_edge_labels=False, figsize=(10, 6)):

        graph = self.network_graph.graph
        # Get node and edge attributes for colors
        node_colors = nx.get_node_attributes(graph, 'color')
        edge_colors = nx.get_edge_attributes(graph, 'color')
        
        # Set edge widths based on edge color
        #edge_width = [2.0 * edge_width_factor if edge_colors[edge] == 'red' else 1.0 * edge_width_factor for edge in graph.edges()]
        edge_width = 1.0
        # Define node positions using Latitude and Longitude attributes
        pos = {node: (float(graph.nodes[node]['Longitude']), float(graph.nodes[node]['Latitude'])) for node in graph.nodes() if 'Latitude' in graph.nodes[node] and 'Longitude' in graph.nodes[node]}

        # Plot the graph
        plt.figure(figsize=figsize)  # Ábra méretének beállítása

        nx.draw(graph, pos, with_labels=True, node_color=list(node_colors.values()), edge_color=list(edge_colors.values()), node_size=node_size, width=edge_width)
        # Optionally display edge labels for distances
        if show_edge_labels:
            edge_labels = {(player, server): round(graph[player][server]["length"],1) for player, server in graph.edges()}
            nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels)

        plt.title(title, y=-0.01, fontsize="19")

    def draw_paths(self, player_server_paths, servers, selected_servers, players, canvas_size, node_size=200, show_edge_labels=False, title='title'):
        plt.figure(figsize=canvas_size)

        # Draw nodes for servers and players
        nx.draw_networkx_nodes(self.network_graph.graph, self.positions, nodelist=[server for server in servers if server in selected_servers],
                               node_color='yellow', node_size=2.5 * node_size)
        nx.draw_networkx_nodes(self.network_graph.graph, self.positions, nodelist=[server for server in servers if server not in selected_servers],
                               node_color='blue', node_size=2.5 * node_size)
        nx.draw_networkx_nodes(self.network_graph.graph, self.positions, nodelist=list(players.keys()), node_color='g', node_size=2.5*node_size)

        # Draw edges for the entire graph
        nx.draw_networkx_edges(self.network_graph.graph, self.positions, edgelist=self.network_graph.graph.edges(), width=1.0, alpha=0.5)

        # Optionally display edge labels for distances
        if show_edge_labels:
            edge_labels = {(player, server): round(self.network_graph.graph[player][server]["length"]) for player, server in self.network_graph.graph.edges}
            nx.draw_networkx_edge_labels(self.network_graph.graph, self.positions, edge_labels=edge_labels)

        # Draw paths for players connected to servers
        for _, _, path in player_server_paths:
            edges = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
            nx.draw_networkx_edges(self.network_graph.graph, self.positions, edgelist=edges, edge_color='red', width=2.0)

        # Add node labels
        node_labels = {node: node for node in self.network_graph.graph.nodes}
        nx.draw_networkx_labels(self.network_graph.graph, self.positions, labels=node_labels)
        # Set node labels for servers
        node_labels = {node: node if node in selected_servers else '' for node in self.network_graph.graph.nodes}
        nx.draw_networkx_labels(self.network_graph.graph, self.positions, labels=node_labels)

        # Set graph title and display
        plt.title(title)

    def draw_paths_interactively(self):
        plt.figure(figsize=(10, 6))
        # Define node positions using Latitude and Longitude attributes
        positions = {node: (float(self.network_graph.graph.nodes[node]['Longitude']), float(self.network_graph.graph.nodes[node]['Latitude'])) 
                    for node in self.network_graph.graph.nodes() if 'Latitude' in self.network_graph.graph.nodes[node] and 'Longitude' in self.network_graph.graph.nodes[node]}

        # Draw the nodes and edges of the network graph
        nx.draw(self.network_graph.graph, positions, with_labels=True, node_color='lightblue', node_size=500, font_weight='bold')

        def update_paths(frame):
            plt.clf()  # Clear the plot for each frame
            nx.draw(self.network_graph.graph, positions, with_labels=True, node_color='lightblue', node_size=500, font_weight='bold')
            
            # Generate a unique color for each path
            unique_color = '#{0:06x}'.format(random.randint(0, 0xFFFFFF))

            # Draw paths for the current frame/player with the unique color
            path = self.network_graph.player_server_paths[frame]
            edges = [(path[j], path[j + 1]) for j in range(len(path) - 1)]
            
            # Use the same color for all edges in the path
            nx.draw_networkx_edges(self.network_graph.graph, positions, edgelist=edges, edge_color=unique_color, width=4.0)

            plt.title("Paths from Players to Servers (Frame: {})".format(frame + 1))

        num_frames = len(self.network_graph.player_server_paths)

        # Create an animation
        anim = FuncAnimation(plt.gcf(), update_paths, frames=num_frames, interval=1000, repeat=False)
    
        plt.show()
        return anim  # Assign the animation object to a variable

    def display_plots(self, animation=None):
        plt.show()

def draw_graph_from_gml(file_path, title, node_size=200, edge_width_factor=1.0, show_edge_labels=False, figsize=(10, 6)):
    # Read the graph from the GML file
    graph = nx.read_gml(file_path)

    # Get node and edge attributes for colors
    node_colors = nx.get_node_attributes(graph, 'color')
    edge_colors = nx.get_edge_attributes(graph, 'color')
    
    # Set edge widths based on edge color
    edge_width = [2.0 * edge_width_factor if edge_colors[edge] == 'red' else 1.0 * edge_width_factor for edge in graph.edges()]

    # Define node positions using Latitude and Longitude attributes
    pos = {node: (float(graph.nodes[node]['Longitude']), float(graph.nodes[node]['Latitude'])) for node in graph.nodes() if 'Latitude' in graph.nodes[node] and 'Longitude' in graph.nodes[node]}

    # Plot the graph
    plt.figure(figsize=figsize)  # Ábra méretének beállítása

    nx.draw(graph, pos, with_labels=True, node_color=list(node_colors.values()), edge_color=list(edge_colors.values()), node_size=node_size, width=edge_width)
    # Optionally display edge labels for distances
    if show_edge_labels:
        edge_labels = {(player, server): round(graph[player][server]["length"],1) for player, server in graph.edges()}
        nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels)

    plt.title(title, y=-0.01, fontsize="19")


    
def draw_compare_plot(*args, df, x:str, x_label:str, plot_type:str, y_label:str, title:str, invert=True):
    mod_data = {}
    for model in args:
        mod_cols = [col for col in df.columns if model in col]
        mod_data[model] = df[['num_players', 'nr_of_servers', 'min_players_connected', 'max_connected_players', 'max_allowed_delay'] + mod_cols]

    plt.figure(figsize=(10, 6))
    for model, data in mod_data.items():
        sns.lineplot(data=data, x=x, y=plot_type+model, label=model.split('_')[-2].title() + " " + model.split('_')[-1].title() + ' Method')
    # Inverting X axis
    if invert:
        plt.gca().invert_xaxis()

    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.legend()

def draw_ga_compare_plot(*args, df, x:str, x_label:str, plot_type:str, y_label:str, title:str, invert=True, same_params=False):
    mod_data = {}
    for model in args:
        mod_cols = [col for col in df.columns if model in col]
        mod_data[model] = df[['num_players', 'nr_of_servers', 'max_players_connected', 'mutation_rate', 'generation_size', 'tournament_size'] + mod_cols]

    plt.figure(figsize=(10, 6))
    for model, data in mod_data.items():
        if not same_params:
            sns.lineplot(data=data, x=x, y=plot_type+model, label=model.split('_')[-2].title() + " " + model.split('_')[-1].title() + ' Method')
        else:
            sns.lineplot(data=data, x=[1, 2, 3, 4, 5], y=plot_type+model, label=model.split('_')[-2].title() + " " + model.split('_')[-1].title() + ' Method')   
    # Inverting X axis
    if invert:
        plt.gca().invert_xaxis()

    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.title(title)
    plt.legend()