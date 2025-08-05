"""
Creates a configuration interface specific for the server.
"""

import configtony

def get_server_config(defaults_only=False):
    server_config = configtony.Config(None if defaults_only else "./config.jsonc")
    server_config.add_option("db_path", str, "./backupchan.db") # Unused
    server_config.add_option("webui_enable", bool, True)
    server_config.add_option("web_debug", bool, False)
    server_config.add_option("temp_save_path", str, "/tmp/backupchan")
    server_config.add_option("db", dict, {})
    server_config.add_option("recycle_bin_path", str, "./Recycle-bin")
    server_config.add_option("recycle_job_interval", int, 3600)
    server_config.add_option("backup_filesize_job_interval", int, 7200)
    server_config.add_option("deduplicate_job_interval", int, 18000)
    server_config.add_option("webui_auth", bool, False)
    server_config.add_option("page_size", int, 10)
    if not defaults_only:
        server_config.parse()
    return server_config
