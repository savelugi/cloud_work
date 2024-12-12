import os
from datetime import datetime
import inspect

class Logger:
    LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

    def __init__(self, log_file=None, save_log=True, console_output=True, min_level="INFO"):
        self.log_file = log_file
        self.console_output = console_output
        self.save_log = save_log
        self.min_level = min_level

    def set_log_level(self, level):
        if level in self.LEVELS:
            self.min_level = level
        else:
            raise ValueError(f"Invalid log level: {level}. Available levels are: {', '.join(self.LEVELS.keys())}")

    def set_log_file(self, log_file):
        self.log_file = log_file
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

    def log(self, *args, level="INFO", save_log=None, print_to_console=None):
        if not self.log_file:
            raise ValueError("Log file path not set. Use `set_log_file` to specify it.")
        
        if self.LEVELS[level] < self.LEVELS[self.min_level]:
            return

        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        message = ' '.join(map(str, args))
        log_entry = f"{timestamp} - {level} - {message}\n"
        
        if save_log is None:
            save_log = self.save_log
        if save_log:
            with open(self.log_file, "a") as file:
                file.write(log_entry)
        
        if print_to_console is None:
            print_to_console = self.console_output
        else:
            if print_to_console is True:
                print(log_entry, end="")

    def log_function(self, *args, level="INFO", save_log=None, print_to_console=None):
        if not self.log_file:
            raise ValueError("Log file path not set. Use `set_log_file` to specify it.")

        if self.LEVELS[level] < self.LEVELS[self.min_level]:
            return  # Skip logging if the level is below the minimum level

        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        caller_frame = inspect.stack()[1]
        caller_name = caller_frame.function
        message = ' '.join(map(str, args))
        log_entry = f"{timestamp} - {level} - [{caller_name}] - {message}\n"
        
        if save_log is None:
            save_log = self.save_log
        if save_log:
            with open(self.log_file, "a") as file:
                file.write(log_entry)
        
        if print_to_console is None:
            print_to_console = self.console_output
        else:
            if print_to_console is True:
                print(log_entry, end="")