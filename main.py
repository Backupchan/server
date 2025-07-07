#!/usr/bin/python3

import database
import file_manager
import serverapi
import serverconfig
import recycle_daemon
import stats
import webui
import logging
import threading
import json
import secrets
from flask import Flask, render_template, request, redirect, url_for, abort, session
from werkzeug.security import check_password_hash

# Set up logging for other modules
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s")

# Initializing modules
config = serverconfig.get_server_config()
db = database.Database(config.get("db_path"), config.get("db"))
file_manager = file_manager.FileManager(db, config.get("recycle_bin_path"))
server_api = serverapi.ServerAPI(db, file_manager)
stats = stats.Stats(db, file_manager)
daemon = recycle_daemon.RecycleDaemon(db, server_api, config.get("daemon_interval"))
threading.Thread(target=daemon.run).start()

# Retreive password hash if auth is enabled
password_hash = ""
if config.get("webui_auth"):
    with open("./auth.json", "r", encoding="utf-8") as auth_json:
        password_hash = json.load(auth_json)["passwd_hash"]

app = Flask(__name__)

# Make a new secret key each time the server is started.
# This does mean that everyone gets logged out everytime the server restarts.
app.secret_key = secrets.token_hex(32)

if config.get("webui_enable"):
    # Initialize Web UI
    webui = webui.WebUI(db, file_manager, server_api, daemon, stats, config, password_hash)
    app.register_blueprint(webui.blueprint)

if __name__ == "__main__":
    app.run(debug=config.get("web_debug"))
