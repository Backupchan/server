import database
import serverapi
import delayed_jobs
import configtony
import os
import logging
import uuid
import traceback
import sys
from backupchan_server import utility
from flask import request

def new_target(db: database.Database) -> str | None:
    log("new target")

    if not "recycle_value" in request.form and request.form["recycle_criteria"] != "none":
        return "Specify a recycle value"

    try:
        db.add_target(request.form["name"], request.form["backup_type"], request.form["recycle_criteria"], request.form.get("recycle_value", 0), request.form.get("recycle_action", "none"), request.form["location"], request.form["name_template"], int("deduplicate" in request.form), request.form.get("alias", None) or None, request.form.get("min_backups", 0), request.form.get("tags", "").split())
    except Exception as exc:
        return str(exc)
    return None

def edit_target(target_id: str, server_api: serverapi.ServerAPI) -> str | None:
    log("edit target")

    if not "recycle_value" in request.form and request.form["recycle_criteria"] != "none":
        return "Specify a recycle value"

    try:
        server_api.edit_target(target_id, request.form["name"], request.form["recycle_criteria"], request.form.get("recycle_value", 0), request.form.get("recycle_action", "none"), request.form["location"], request.form["name_template"], int("deduplicate" in request.form), request.form.get("alias", None) or None, request.form.get("min_backups", 0), request.form.get("tags", "").split())
    except Exception as exc:
        return str(exc)
    return None

def delete_target(target_id: str, server_api: serverapi.ServerAPI):
    log("delete target")
    server_api.delete_target(target_id, bool(request.form.get("delete_files")))

def upload_backup(target_id: str, db: database.Database, config: configtony.Config, job_manager: delayed_jobs.JobManager, server_api: serverapi.ServerAPI) -> str | None:
    log("upload backup")

    # Saving the file is done separately as it gets closed after the request, but the job runs after it.
    files = request.files.getlist("backup_file")
    if len(files) == 0:
        return "No files specified"
    if len(files) != 1 and db.get_target(target_id).target_type == "single":
        return "Cannot upload multiple files to a single-file target" # Technically shouldn't happen but who knows
    filenames = []
    for file in files:
        filename = utility.join_path(config.get("temp_save_path"), f"{uuid.uuid4().hex}_{file.filename}")
        os.makedirs(config.get("temp_save_path"), exist_ok=True)
        file.save(filename)
        filenames.append(filename)

    try:
        job_manager.run_job(delayed_jobs.UploadJob(target_id, True, filenames, server_api))
    except Exception as exc:
        print(traceback.format_exc(), file=sys.stderr)
        return str(exc)
    return None

def delete_backup(backup_id: str, server_api: serverapi.ServerAPI):
    log("delete backup")
    server_api.delete_backup(backup_id, bool(request.form.get("delete_files")))

def delete_target_backups(target_id: str, server_api: serverapi.ServerAPI):
    log("delete target backups")
    server_api.delete_target_backups(target_id, bool(request.form.get("delete_files")))

def delete_target_recycled(target_id: str, server_api: serverapi.ServerAPI):
    log("delete target recycled")
    server_api.delete_target_recycled_backups(target_id, bool(request.form.get("delete_files")))

def recycle_backup(backup_id: str, server_api: serverapi.ServerAPI):
    log("recycle backup")
    server_api.recycle_backup(backup_id)

def unrecycle_backup(backup_id: str, server_api: serverapi.ServerAPI):
    log("unrecycle backup")
    server_api.unrecycle_backup(backup_id)

def recycle_bin_clear(server_api: serverapi.ServerAPI):
    log("recycle bin clear")
    server_api.recycle_bin_clear(bool(request.form.get("delete_files")))

def log(message: str):
    logging.getLogger("webui_post").info(f"Handle POST {message} with data: {request.form}")
