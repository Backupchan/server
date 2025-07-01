"""
Creates a configuration interface specific for the server.
"""

import config

def get_server_config():
    server_config = config.Config("./config.jsonc")
    server_config.add_option("db_path", str, "./backupchan.db")
    server_config.add_option("webui_enable", bool, True)
    server_config.add_option("web_debug", bool, False)
    server_config.add_option("temp_save_path", str, "/tmp/backupchan")
    server_config.add_option("db", dict, {})
    server_config.add_option("recycle_bin_path", str, "./Recycle-bin")
    server_config.add_option("daemon_interval", int, 60)
    server_config.add_option("webui_auth", bool, False)
    server_config.parse()
    return server_config
