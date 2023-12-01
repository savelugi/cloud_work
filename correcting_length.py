import networkx as nx
from utils import euclidean_distance
import math

# Read the GML file and create a graph
G = nx.read_gml("C:/Users/bbenc/OneDrive/Documents/aGraph/cloud_work/src/25_italy.gml")

# Iterate through edges to identify and correct incorrect lengths
for u, v, data in G.edges(data=True):
    # Get source and target node coordinates
    source_data = G.nodes[u]
    target_data = G.nodes[v]

    # Assuming 'Latitude' and 'Longitude' keys are used in the node attributes
    source_pos = (source_data['Latitude'], source_data['Longitude'])
    target_pos = (target_data['Latitude'], target_data['Longitude'])

    # Get current edge length
    current_length = data['length']

    # Calculate the correct length based on coordinates using euclidean_distance function
    correct_length = euclidean_distance(source_pos, target_pos)

    if current_length != correct_length:
        data['length'] = correct_length

# Save the corrected graph back to a new GML file
nx.write_gml(G, '37_cost_scaled.gml')
