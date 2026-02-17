#!/usr/bin/python3
"""
Serve Backup-chan using waitress
"""

from waitress import serve
from main import app
import configtony

config = configtony.Config("./waitress_config.jsonc")
config.add_option("host", str, "0.0.0.0")
config.add_option("port", int, 5000)
config.add_option("max_request_body_size", int, 1024 ** 2 * 10)
config.parse()

serve(app, host=config.get("host"), port=config.get("port"), max_request_body_size=config.get("max_request_body_size"))
