"""
Creates a configuration interface specific for the server.
"""

import config

def get_server_config():
    server_config = config.Config("./config.jsonc")
    server_config.add_option("db_path", str, "./backupchan.db")
    server_config.add_option("webui_password", str, "123456")
    server_config.add_option("webui_debug", bool, False)
    server_config.add_option("temp_save_path", str, "/tmp/backupchan")
    server_config.add_option("db", dict, {})
    server_config.parse()
    return server_config
