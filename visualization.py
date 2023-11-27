import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import random

class Visualization:
    def __init__(self, network_graph):
        self.network_graph = network_graph

    def draw_graph(self, pos, servers, players, canvas_size, node_size=200, show_edge_labels=False):
        # Close all existing Matplotlib figures
        #plt.close('all')

        plt.figure(figsize=canvas_size)
        
        # Szerverek kirajzolása
        nx.draw_networkx_nodes(self.network_graph.graph, pos, nodelist=servers.keys(), node_color='b', node_size=2.5*node_size)
        # Játékosok kirajzolása
        nx.draw_networkx_nodes(self.network_graph.graph, pos, nodelist=players.keys(), node_color='g', node_size=node_size)

        # Élek kirajzolása
        nx.draw_networkx_edges(self.network_graph.graph, pos, edgelist=self.network_graph.graph.edges(), width=1.0, alpha=0.5)

        # Él súlyok (távolságok) hozzáadása
        if show_edge_labels:
            edge_labels = {(player, server): round(self.network_graph.graph[player][server]["length"]) for player, server in self.network_graph.graph.edges}
            nx.draw_networkx_edge_labels(self.network_graph.graph, pos, edge_labels=edge_labels)

        # Címkék hozzáadása a csomópontokhoz
        node_labels = {node: node for node in self.network_graph.graph.nodes}
        nx.draw_networkx_labels(self.network_graph.graph, pos, labels=node_labels)

        # Kirajzolás beállításai
        plt.title("Szerverek és Játékosok")

    def draw_paths(self, pos, player_server_paths, servers, selected_servers, players, canvas_size, node_size=200, show_edge_labels=False, title='title'):
        plt.figure(figsize=canvas_size)

        # Draw nodes for servers and players
        nx.draw_networkx_nodes(self.network_graph.graph, pos, nodelist=[server for server in servers if server in selected_servers],
                               node_color='yellow', node_size=2.5 * node_size)
        nx.draw_networkx_nodes(self.network_graph.graph, pos, nodelist=[server for server in servers if server not in selected_servers],
                               node_color='blue', node_size=2.5 * node_size)
        nx.draw_networkx_nodes(self.network_graph.graph, pos, nodelist=list(players.keys()), node_color='g', node_size=2.5*node_size)

        # Draw edges for the entire graph
        nx.draw_networkx_edges(self.network_graph.graph, pos, edgelist=self.network_graph.graph.edges(), width=1.0, alpha=0.5)

        # Optionally display edge labels for distances
        if show_edge_labels:
            edge_labels = {(player, server): round(self.network_graph.graph[player][server]["length"]) for player, server in self.network_graph.graph.edges}
            nx.draw_networkx_edge_labels(self.network_graph.graph, pos, edge_labels=edge_labels)

        # Draw paths for players connected to servers
        for _, _, path in player_server_paths:
            edges = [(path[i], path[i + 1]) for i in range(len(path) - 1)]
            nx.draw_networkx_edges(self.network_graph.graph, pos, edgelist=edges, edge_color='red', width=2.0)

        # Add node labels
        node_labels = {node: node for node in self.network_graph.graph.nodes}
        nx.draw_networkx_labels(self.network_graph.graph, pos, labels=node_labels)
        # Set node labels for servers
        node_labels = {node: node if node in selected_servers else '' for node in self.network_graph.graph.nodes}
        nx.draw_networkx_labels(self.network_graph.graph, pos, labels=node_labels)

        # Set graph title and display
        plt.title(title)

    def draw_paths_interactively(self, pos, player_server_paths):
        plt.figure(figsize=(8, 6))

        # Draw the nodes and edges of the network graph
        nx.draw(self.network_graph.graph, pos, with_labels=True, node_color='lightblue', node_size=500, font_weight='bold')

        def update_paths(frame):
            #plt.clf()  # Clear the plot for each frame
            nx.draw(self.network_graph.graph, pos, with_labels=True, node_color='lightblue', node_size=500, font_weight='bold')
            
            # Generate a unique color for each path
            unique_color = '#{0:06x}'.format(random.randint(0, 0xFFFFFF))

            # Draw paths for the current frame/player with the unique color
            path = player_server_paths[frame]
            edges = [(path[j], path[j + 1]) for j in range(len(path) - 1)]
            
            # Use the same color for all edges in the path
            nx.draw_networkx_edges(self.network_graph.graph, pos, edgelist=edges, edge_color=unique_color, width=2.0)

            plt.title("Paths from Players to Servers (Frame: {})".format(frame + 1))

        num_frames = len(player_server_paths)

        # Create an animation
        ani = FuncAnimation(plt.gcf(), update_paths, frames=num_frames, interval=1000, repeat=False)

    def display_plots(self):
        plt.show()