import random
import time
import pandas as pd
import math
import json

def generate_players(num_players=10, x_range=(0, 100), y_range=(0, 100), seed=None):
    if seed is not None:
        random.seed(seed)

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

def euclidean_distance(pos1: tuple, pos2: tuple) -> float:
    x1, y1 = map(float, pos1)
    x2, y2 = map(float, pos2)
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

def min_distance(point, points):
    min_value = float('inf')
    key = None
    
    for iter_key, iter_point in points.items():
        cur_dist = euclidean_distance(point, iter_point)
        if cur_dist < min_value:
            min_value = cur_dist
            key = iter_key

    return min_value, key

def print_pattern():
    print("\n")
    print("#" * 100)  # Prints the '#' character 100 times
    print("#" * 100)  # Prints the '#' character 100 times
    print("#" * 100)  # Prints the '#' character 100 times
    print("\n")


class Timer:
    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.end_time = time.time()

    def get_elapsed_time(self):
        if self.start_time is None or self.end_time is None:
            return None
        return self.end_time - self.start_time

    def print_elapsed_time(self):
        elapsed_time = self.get_elapsed_time()
        if elapsed_time is not None:
            print(f"Elapsed time: {elapsed_time} seconds")
        else:
            print("Timer has not been started and stopped properly.")
