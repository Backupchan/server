"""
Simple configuration module.
"""

import json5
import os
from typing import TypeAlias

class ConfigException(Exception):
    pass

class Config:
    def __init__(self, file: str):
        self.file = file
        self.config = {}
        self.valid_options: dict[TypeAlias] = {}

    def add_option(self, name: str, option_type: TypeAlias, default):
        self.valid_options[name] = option_type
        if not isinstance(default, option_type):
            raise ConfigException(f"Default value for option '{name}' must be of type '{option_type}'")
        self.config[name] = default

    def parse(self):
        if not os.path.exists(self.file):
            raise ConfigException("Config file not found.")

        with open(self.file, "r", encoding="utf-8") as config_json:
            config = json5.parse(config_json.read())[0]
            for option in config:
                if option not in list(self.valid_options.keys()):
                    raise ConfigException(f"'{option}' is not a valid config option.")
                real_type = config[option]
                correct_type = self.valid_options[option]
                if not isinstance(real_type, correct_type):
                    raise ConfigException(f"Config option '{option}' must be of type '{correct_type}', not '{type(real_type)}'")
                self.config[option] = config[option]
    
    def get(self, option: str):
        return self.config[option]
