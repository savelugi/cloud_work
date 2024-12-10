import networkx as nx
from utils import *

# Read the GML file and create a graph
Graph = nx.read_gml("/Users/ebenbot/Documents/University/cloud_work/src/50_germany.gml")

seed = 42

# Iterate through nodes to assign random server properties
for i, node in enumerate(Graph.nodes()):
    if 'server' not in Graph.nodes[node]:
        Graph.nodes[node]['server'] = generate_server_properties(seed+i)

# Iterate through edges to identify and correct incorrect lengths
for u, v, data in Graph.edges(data=True):
    # Get source and target node coordinates
    source = Graph.nodes[u]
    target = Graph.nodes[v]

    # Assuming 'Latitude' and 'Longitude' keys are used in the node attributes
    source_pos = (source['Latitude'], source['Longitude'])
    target_pos = (target['Latitude'], target['Longitude'])

    # Get current edge length
    current_length = data['length']

    # Calculate the correct length based on coordinates using euclidean_distance function
    correct_length = euclidean_distance(source_pos, target_pos)

    if current_length != correct_length:
        data['length'] = correct_length
    
    data['link_bandwith'] = generate_link_properties(source['server']['type'], target['server']['type'])


# Save the corrected graph back to a new GML file
nx.write_gml(Graph, '50_germany_scaled.gml')
