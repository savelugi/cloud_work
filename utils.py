import random
import time
import pandas as pd
import math
import csv
import configparser
import os

def get_lat_long_range(config):
    topology = config['Topology']['topology']
    if topology == "usa":
        return (25, 47), (-123, -70)
    elif topology == "germany":
        return (47, 55), (6, 14)
    elif topology == "cost":
        return (35, 62), (-10, 28)
    else:
        print("Error: Unsupported topology")
        return None

def generate_player_params(x_range=(0, 100), y_range=(0, 100), seed=None):
    if seed is not None:
        random.seed(seed)

    x_min, x_max = x_range
    y_min, y_max = y_range
    x = round(random.uniform(x_min, x_max), 2)
    y = round(random.uniform(y_min, y_max), 2)
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

    return {
            'Longitude': y,
            'Latitude': x,
            'device_type': device_type,
            'game': game,
            'ping_preference': ping_preference,
            'video_quality_preference': video_quality_preference,
            'connected_to_server': -1
    }

def generate_players(num_players=10, x_range=(0, 100), y_range=(0, 100), seed=None):
    players = {}
    
    for i in range(int(num_players)):
        player_name = f"P{i+1}"
        player_params = generate_player_params(x_range, y_range, seed)
        
        players[player_name] = {
            'Longitude': player_params['Longitude'],
            'Latitude': player_params['Latitude'],
            'device_type': player_params['device_type'],
            'game': player_params['game'],
            'ping_preference': player_params['ping_preference'],
            'video_quality_preference': player_params['video_quality_preference'],
            'connected_to_server': player_params['connected_to_server']
        }
        seed += 1

    return players


def move_player(players:dict, player_id, new_x, new_y, debug_prints=False):
    
    if debug_prints:
        print(f"Moving player {player_id}: to X:{new_x} and Y:{new_y}")

    players[player_id]['Latitude'] = new_x
    players[player_id]['Longitude'] = new_y

    return

def move_players_randomly(players: dict, move_probability, max_move_dist, x_range=(0, 100), y_range=(0, 100), seed=None, debug_prints=False):
    if seed is not None:
        random.seed(seed)

    x_min, x_max = x_range
    y_min, y_max = y_range
    
    for player_id, player_data in players.items():
        if random.random() < move_probability:
            delta_x = random.uniform(-max_move_dist, max_move_dist)
            delta_y = random.uniform(-max_move_dist, max_move_dist)
            
            # Staying between the boundaries
            new_x = round(min(max(player_data['Latitude'] + delta_x, x_min), x_max), 2)
            new_y = round(min(max(player_data['Longitude'] + delta_y, y_min), y_max), 2)

            if debug_prints:
                if delta_x == x_min or delta_x == x_max:
                    print(f"Player {player_id} is at x boundary")
                if delta_y == y_min or delta_y == y_max:
                    print(f"Player {player_id} is at y boundary")

            move_player(players, player_id, new_x, new_y, debug_prints)

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

def get_topology_filename(config):
    if config['Topology']['topology'] in config['Scaled network topologies']:
        topology = config['Topology']['topology']
        return  os.path.join(os.path.join(os.path.dirname(os.path.realpath(__file__)), "src"),  config['Scaled network topologies'][topology])
    else:
        print("Scaled topology is not found in the config file!")
        return None
    
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
    if config['Toggles'].getboolean('gen_combined_model'):
        active_models.append('gen_combined')
    return debug_prints, optimize, save, plot, active_models

def get_toggles_from_genconfig(config):
    debug_prints = config['Toggles'].getboolean('debug')
    optimize = config['Toggles'].getboolean('optimize')
    save = config['Toggles'].getboolean('save')
    active_models = []
    if config['Toggles'].getboolean('sum_rank_single'):
        active_models.append('sum_rank_single')
    if config['Toggles'].getboolean('sum_rank_multi'):
        active_models.append('sum_rank_multi')
    if config['Toggles'].getboolean('sum_rank_unif'):
        active_models.append('sum_rank_unif')
    if config['Toggles'].getboolean('sum_tournament_single'):
        active_models.append('sum_tournament_single')
    if config['Toggles'].getboolean('sum_tournament_multi'):
        active_models.append('sum_tournament_multi')
    if config['Toggles'].getboolean('sum_tournament_unif'):
        active_models.append('sum_tournament_unif')
    if config['Toggles'].getboolean('sum_roulette_single'):
        active_models.append('sum_roulette_single')
    if config['Toggles'].getboolean('sum_roulette_multi'):
        active_models.append('sum_roulette_multi')
    if config['Toggles'].getboolean('sum_roulette_unif'):
        active_models.append('sum_roulette_unif')

    return debug_prints, optimize, save, active_models

def read_parameters_from_config(config):
    topology = config['Topology']['topology']

    param_combinations = []
    for key in config[topology]:
        param_combinations.append(tuple(map(int, config[topology][key].split(','))))

    return param_combinations

def read_parameters_from_genconfig(config):
    topology = config['Topology']['topology']

    param_combinations = []
    for key in config[topology]:
        param_combinations.append(tuple(map(float, config[topology][key].split(','))))

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

def write_csv_header(csv_path, active_models):
    header_columns = ['num_players', 'nr_of_servers', 'min_players_connected', 'max_connected_players', 'max_allowed_delay']
    
    with open(csv_path, mode='w', newline='') as file:
        writer = csv.writer(file)

        for modelname in active_models:
            header_columns += [f'average_player_to_server_delay_{modelname}', f'min_player_to_server_delay_{modelname}', f'max_player_to_server_delay_{modelname}',
                    f'average_player_to_player_delay_{modelname}', f'min_player_to_player_delay_{modelname}', f'max_player_to_player_delay_{modelname}', 
                    f'nr_of_selected_servers_{modelname}', f'qoe_score_{modelname}', f'sim_time_{modelname}']
        
        writer.writerow(header_columns)

def write_ga_csv_header(csv_path, active_models):
    header_columns = ['num_players', 'nr_of_servers', 'max_players_connected', 'mutation_rate', 'generation_size', 'tournament_size']
    
    with open(csv_path, mode='w', newline='') as file:
        writer = csv.writer(file)

        for modelname in active_models:
            header_columns += [f'average_player_to_server_delay_{modelname}', f'min_player_to_server_delay_{modelname}', f'max_player_to_server_delay_{modelname}',
                    f'average_player_to_player_delay_{modelname}', f'min_player_to_player_delay_{modelname}', f'max_player_to_player_delay_{modelname}', 
                    f'nr_of_selected_servers_{modelname}', f'qoe_score_{modelname}', f'sim_time_{modelname}']
        
        writer.writerow(header_columns)
        
def write_csv_row(csv_path, values):
    with open(csv_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(values)

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
