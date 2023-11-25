import networkx as nx
import matplotlib.pyplot as plt

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
        plt.show()
