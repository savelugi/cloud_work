import random
import time
import pandas as pd
import math
import configparser

def get_lat_long_range(topology):
    if topology == "usa":
        return (25, 45), (-123, -70)
    elif topology == "germany":
        return (47, 55), (6, 14)
    elif topology == "cost":
        return (35, 62), (-10, 28)
    else:
        print("Error: Unsupported topology")
        return None

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
        device_type = random.choice(['mobile', 'desktop'])
        game = random.choice(['NFS', 'WoW', 'CSGO'])
        if game == 'NFS':
            ping_preference = random.choice([40, 50, 60, 70, 80, 90])
            video_quality_preference = random.choice([4800, 6000, 7200, 8400])
        if game == 'WoW':
            ping_preference = random.choice([30, 40, 50, 60])
            video_quality_preference = random.choice([3600, 4800, 6000, 7200, 8400])
        if game == 'CSGO':
            ping_preference = random.choice([30, 40, 50])
            video_quality_preference = random.choice([1200, 2400, 3600, 4800])
        
        players[player_name] = {
            'Longitude': y,
            'Latitude': x,
            'device_type': device_type,
            'game': game,
            'ping_preference': ping_preference,
            'video_quality_preference': video_quality_preference
        }
    return players


def generate_servers():
    # Prediktív szerverek pozíciói
    servers = {
        "S1": (0, 0),
        "S2": (50, 50),
        "S3": (100, 100)
    }
    return servers

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

def read_configuration(config_file):
    """
    Reads in a .ini file and returns it as a parsed dictionary.

    Args:
        config_file (str): path of the config file.

    Returns:
        dict: the config in a parsed dictionary.
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def get_topology_filename(topology, config):
    if topology in config['Scaled network topologies']:
        return config['Settings']['topology_dir'] + config['Scaled network topologies'][topology]
    else:
        print("Scaled topology is not found in the config file!")
        return None
    
def get_save_dir(config):
    return config['Settings']['save_dir']

def get_toggles_from_config(config):
    debug_prints = config['Toggles'].getboolean('debug')
    optimize = config['Toggles'].getboolean('optimize')
    save = config['Toggles'].getboolean('save')
    plot = config['Toggles'].getboolean('plot')
    active_models = []
    if config['Toggles'].getboolean('ilp_sum_model'):
        active_models.append('ilp_sum')
    if config['Toggles'].getboolean('ilp_ipd_model'):
        active_models.append('ilp_ipd')
    if config['Toggles'].getboolean('gen_sum_model'):
        active_models.append('gen_sum')
    if config['Toggles'].getboolean('gen_ipd_model'):
        active_models.append('gen_ipd')
    return debug_prints, optimize, save, plot, active_models

def read_parameters_from_config(topology, config):    
    if topology not in config:
        print(f"'{topology}' not found in the {config} file.")
        return []

    param_combinations = []
    for key in config[topology]:
        param_combinations.append(tuple(map(int, config[topology][key].split(','))))

    return param_combinations

def calculate_ping_score(actual_ping, wanted_ping):
    max_point = 100
    min_point = 0
    max_ping = 1.5 * wanted_ping
    if actual_ping <= wanted_ping:
        return max_point
    elif actual_ping > max_ping:
        return min_point
    else:
        return max_point - (actual_ping - wanted_ping) * (max_point / (max_ping - wanted_ping))
    
def calculate_video_score():
    return None


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
