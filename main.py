#!/usr/bin/python3

import database
import file_manager
import serverapi
import serverconfig
import stats
import webui
import api
import scheduled_jobs
import delayed_jobs
import seq_upload
import log
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

log.init()

#
# Initializing modules
#

config = serverconfig.get_server_config()
db = database.Database(config.get("db"), config.get("page_size"))
file_manager = file_manager.FileManager(db, config.get("recycle_bin_path"))
server_api = serverapi.ServerAPI(db, file_manager)
stats = stats.Stats(db, file_manager)
seq_upload_manager = seq_upload.SequentialUploadManager()

db.validate_schema_version()

#
# Initializing scheduled jobs
#

scheduler = scheduled_jobs.JobScheduler()
scheduler.add_job(scheduled_jobs.RecycleJob(config.get("recycle_job_interval"), db, server_api))
scheduler.add_job(scheduled_jobs.BackupFilesizeJob(config.get("backup_filesize_job_interval"), db, file_manager))
scheduler.add_job(scheduled_jobs.DeduplicateJob(config.get("deduplicate_job_interval"), db, file_manager, server_api))
scheduler.add_job(scheduled_jobs.StaleSequentialUploadJob(config.get("stale_seq_upload_job_interval"), seq_upload_manager))
scheduler.add_job(scheduled_jobs.TemporaryPurgeJob(config.get("tmp_purge_job_interval"), config.get("temp_save_path")))
scheduler.start()

#
# Initializing delayed jobs
#

manager = delayed_jobs.JobManager()

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

    webui = webui.WebUI(db, file_manager, server_api, scheduler, manager, stats, seq_upload_manager, config, password_hash, app.root_path)
    app.register_blueprint(webui.blueprint)

#
# Initialize the API
#

api = api.API(db, server_api, config, file_manager, stats, manager, scheduler, seq_upload_manager)
app.register_blueprint(api.blueprint, url_prefix="/api")

if __name__ == "__main__":
    app.run(debug=config.get("web_debug"))
