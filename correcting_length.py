import networkx as nx
from utils import euclidean_distance
import random

# Function to generate random server properties
def generate_server_properties(seed=None):
    if seed is not None:
        random.seed(seed)

    server_type = random.choice(['core', 'edge'])  # Random server type: core or edge
    if server_type == 'core':
        cpu = random.choice([32, 48, 64, 128])  # Random CPU value
        memory = random.choice([32, 64, 128, 256])  # Random memory value
        gpu = random.choices([0, 1], weights=[0.75, 0.25])[0]  # Random GPU presence: True or False
    else: #edge
        cpu = random.choice([8, 16, 32])  # Random CPU value
        memory = random.choice([8, 16, 32, 64])  # Random memory value
        gpu = False  # Random GPU presence: True or False
    return {'type': server_type, 'cpu': cpu, 'memory': memory, 'gpu': gpu}

def generate_link_properties(source, target):
    bandwidth = None
    seed = 42
    if seed is not None:
        random.seed(seed)

    if(source == 'core' and target == 'core'):
        bandwidth = '25G'
    elif (source == 'core' and target == 'edge'):
        bandwidth = '10G'
    elif (source == 'edge' and target == 'core'):
        bandwidth = '10G'
    elif (source == 'edge' and target == 'edge'):
        bandwidth = '1G'

    return bandwidth

# Read the GML file and create a graph
Graph = nx.read_gml("/Users/ebenbot/Documents/University/cloud_work/src/37_cost.gml")

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
nx.write_gml(Graph, '37_cost_scaled.gml')
