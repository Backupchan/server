#!/usr/bin/python3

import database
import file_manager
import serverapi
import serverconfig
import stats
import webui
import api
import jobs
import logging
import logging.handlers
import json
import secrets
import os
import sys
from flask import Flask, render_template, request, redirect, url_for, abort, session
from werkzeug.security import check_password_hash

#
# Set up logging for other modules
#

# TODO make log configurable

if not os.path.isdir("./log"):
    os.mkdir("./log")

formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s")

file_handler = logging.handlers.RotatingFileHandler("log/backupchan.log", maxBytes=2000000, backupCount=5)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

#
# Initializing modules
#

config = serverconfig.get_server_config()
db = database.Database(config.get("db"), config.get("page_size"))
file_manager = file_manager.FileManager(db, config.get("recycle_bin_path"))
server_api = serverapi.ServerAPI(db, file_manager)
stats = stats.Stats(db, file_manager)

db.validate_schema_version()

#
# Initializing scheduled jobs
#

scheduler = jobs.JobScheduler()
scheduler.add_job(jobs.RecycleJob(config.get("recycle_job_interval"), db, server_api))
scheduler.add_job(jobs.BackupFilesizeJob(config.get("backup_filesize_job_interval"), db, file_manager))
scheduler.add_job(jobs.DeduplicateJob(config.get("deduplicate_job_interval"), db, file_manager, server_api))
scheduler.start()

#
# Retreive password hash if auth is enabled
#

password_hash = ""
if config.get("webui_auth"):
    try:
        with open("./auth.json", "r", encoding="utf-8") as auth_json:
            password_hash = json.load(auth_json)["passwd_hash"]
    except FileNotFoundError:
        logging.getLogger().error("WebUI authentication enabled, but no auth.json file found. Authentication will be disabled.")
    except json.JSONDecodeError as exc:
        logging.getLogger().error(f"Failed to parse auth.json: {exc}. Authentication will be disabled.")

app = Flask(__name__)

#
# Make a new secret key each time the server is started.
# This does mean that everyone gets logged out everytime the server restarts.
# (except if you're using the client as that uses the api key which is static)
#
app.secret_key = secrets.token_hex(32)

if config.get("webui_enable"):
    #
    # Initialize Web UI
    #

    webui = webui.WebUI(db, file_manager, server_api, scheduler, stats, config, password_hash, app.root_path)
    app.register_blueprint(webui.blueprint)

#
# Initialize the API
#

api = api.API(db, server_api, config, file_manager, stats)
app.register_blueprint(api.blueprint, url_prefix="/api")

if __name__ == "__main__":
    app.run(debug=config.get("web_debug"))
