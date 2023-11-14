import networkx as nx
import matplotlib.pyplot as plt
import random

def generate_players(num_players=10, x_range=(0, 100), y_range=(0, 100)):
    players = {}
    x_start, x_stop = x_range
    y_start, y_stop = y_range
    for i in range(num_players):
        player_name = f"P{i+1}"
        x = round(random.uniform(x_start, x_stop), 2)
        y = round(random.uniform(y_start, y_stop), 2)
        players[player_name] = (x, y)
    return players


def generate_servers():
    # Prediktív szerverek pozíciói
    servers = {
        "S1": (0, 0),
        "S2": (50, 50),
        "S3": (100, 100)
    }
    return servers

def distance(pos1:tuple, pos2:tuple):
    return abs(float(pos1[0]) - float(pos2[0])) + abs(float(pos1[1]) - float(pos2[1]))

def min_distance(point, points):
    min_value = float('inf')
    key = None
    
    for iter_key, iter_point in points.items():
        cur_dist = distance(point, iter_point)
        if cur_dist < min_value:
            min_value = cur_dist
            key = iter_key

    return min_value, key
