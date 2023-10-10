import networkx as nx
import matplotlib.pyplot as plt

class Visualization:
    def __init__(self, network_graph):
        self.network_graph = network_graph

    
    def draw_graph(self, pos, servers, players, canvas_size, node_size=200, show_edge_labels=False):
        plt.figure(figsize=canvas_size)
        
        # Szerverek kirajzolása
        nx.draw_networkx_nodes(self.network_graph, pos, nodelist=servers.keys(), node_color='b', node_size=2.5*node_size, label="Servers")
        # Játékosok kirajzolása
        nx.draw_networkx_nodes(self.network_graph, pos, nodelist=players.keys(), node_color='g', node_size=node_size, label="Players")

        # Élek kirajzolása
        nx.draw_networkx_edges(self.network_graph, pos, edgelist=G.edges(), width=1.0, alpha=0.5)

        # Él súlyok (távolságok) hozzáadása
        if show_edge_labels:
            edge_labels = {(player, server): G[player][server]["weight"] for player, server in G.edges}
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)

        # Címkék hozzáadása a csomópontokhoz
        node_labels = {node: node for node in G.nodes}
        nx.draw_networkx_labels(G, pos, labels=node_labels)

        # Kirajzolás beállításai
        plt.title("Szerverek és Játékosok")
        plt.show()
