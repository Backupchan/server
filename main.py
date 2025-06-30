#!/usr/bin/python3

import database
import file_manager
import serverconfig
import traceback
import sys
import datetime
import uuid
import os
import logging
from flask import Flask, render_template, request, redirect, url_for, abort

# Set up logging for other modules
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s")

config = serverconfig.get_server_config()
db = database.Database(config.get("db_path"), config.get("db"))
file_manager = file_manager.FileManager(db)

app = Flask(__name__)

#
# POST request handlers
#

def handle_post_new_target() -> str | None:
    app.logger.info(f"Handle POST new target with data: {request.form}")
    try:
        db.add_target(request.form["name"], request.form["backup_type"], request.form["recycle_criteria"], request.form["recycle_value"], request.form["recycle_action"], request.form["location"], request.form["name_template"])
    except Exception as exc:
        return str(exc)
    return None

def handle_post_edit_target(target_id: str) -> str | None:
    app.logger.info(f"Handle POST edit target with data: {request.form}")
    try:
        target = db.get_target(target_id)
        old_location = target.location
        old_name_template = target.name_template
        new_location = request.form["location"]
        new_name_template = request.form["name_template"]
        db.edit_target(target_id, request.form["name"], request.form["backup_type"], request.form["recycle_criteria"], request.form["recycle_value"], request.form["recycle_action"], new_location, new_name_template)
        if old_name_template != new_name_template or old_location != old_location:
            file_manager.update_backup_locations(target, new_name_template, new_location, old_name_template, old_location)
    except Exception as exc:
        print(traceback.format_exc(), file=sys.stderr)
        return str(exc)
    return None

def handle_post_delete_target(target_id: str):
    app.logger.info(f"Handle POST delete target with data: {request.form}")
    if bool(request.form.get("delete_files")):
        file_manager.delete_target_backups(target_id)
    db.delete_target(target_id)

def move_uploaded_backup() -> str:
    uploaded_file = request.files["backup_file"]
    temp_path = f"{config.get('temp_save_path')}/{uuid.uuid4().hex}_{uploaded_file.filename}"
    os.makedirs(config.get("temp_save_path"), exist_ok=True)
    uploaded_file.save(temp_path)
    return temp_path

def handle_post_upload_backup(target_id: str) -> str | None:
    app.logger.info(f"Handle POST upload backup with data: {request.form}")
    backup_id = ""
    try:
        backup_id = db.add_backup(target_id, datetime.datetime.now(), True) # Always manual via the browser
        backup_filename = move_uploaded_backup()
        app.logger.info(f"Uploaded file saved as {backup_filename}")
    except Exception as exc:
        db.delete_backup(backup_id)
        print(traceback.format_exc(), file=sys.stderr)
        return str(exc)

    try:
        file_manager.add_backup(backup_id, backup_filename)
    except Exception as exc:
        # if this fails we delete the freaking backup
        db.delete_backup(backup_id)
        print(traceback.format_exc(), file=sys.stderr)
        return str(exc)
    return None

def handle_post_delete_backup(backup_id: str):
    app.logger.info(f"Handle POST delete backup with data: {request.form}")
    if bool(request.form.get("delete_files")):
        file_manager.delete_backup(backup_id)
    db.delete_backup(backup_id)

def handle_post_delete_target_backups(target_id: str):
    app.logger.info(f"Handle POST delete target backups with data: {request.form}")
    if bool(request.form.get("delete_files")):
        file_manager.delete_target_backups(target_id)
    db.delete_target_backups(target_id)

#
# Endpoints
#

@app.route("/")
def homepage():
    targets = db.list_targets()
    return render_template("home.html", targets=targets, num_targets=db.count_targets(), num_backups=db.count_backups())

#
# Target endpoints
#

@app.route("/targets")
def list_targets():
    targets = db.list_targets()
    return render_template("list_targets.html", targets=targets, num_targets=db.count_targets())

@app.route("/target/new", methods=["GET", "POST"])
def new_target():
    if request.method == "POST":
        error_message = handle_post_new_target()
        if error_message is None:
            return redirect(url_for("list_targets"))
        else:
            return render_template("edit_target.html", target=None, error_message=error_message)
    return render_template("edit_target.html", target=None)

@app.route("/target/<id>")
def view_target(id):
    target = db.get_target(id)
    if target is None:
        abort(404)
    backups = db.list_backups_target(id)
    return render_template("view_target.html", target=target, backups=backups, num_backups = len(backups))

@app.route("/target/<id>/upload", methods=["GET", "POST"])
def upload_backup(id):
    target = db.get_target(id)
    if target is None:
        abort(404)
    if request.method == "POST":
        error_message = handle_post_upload_backup(id)
        if error_message is None:
            return redirect(url_for("view_target", id=id))
        else:
            return render_template("upload_backup.html", target=target, error_message=error_message)
    return render_template("upload_backup.html", target=target)

@app.route("/target/<id>/edit", methods=["GET", "POST"])
def edit_target(id):
    target = db.get_target(id)
    if target is None:
        abort(404)
    if request.method == "POST":
        error_message = handle_post_edit_target(id)
        if error_message is None:
            return redirect(url_for("view_target", id=id))
        else:
            return render_template("edit_target.html", target=target, error_message=error_message)
    return render_template("edit_target.html", target=target)

@app.route("/target/<id>/delete", methods=["GET", "POST"])
def delete_target(id):
    target = db.get_target(id)
    if target is None:
        abort(404)
    if request.method == "POST":
        handle_post_delete_target(id) # shouldn't really fail
        return redirect(url_for("list_targets"))
    return render_template("delete_target.html", target=target)

@app.route("/target/<id>/delete_all", methods=["GET", "POST"])
def delete_target_backups(id):
    target = db.get_target(id)
    if target is None:
        abort(404)
    if request.method == "POST":
        handle_post_delete_target_backups(id)
        return redirect(url_for("view_target", id=id))
    return render_template("delete_target_backups.html", target=target)

#
# Backup endpoints
#

@app.route("/backup/<id>/delete", methods=["GET", "POST"])
def delete_backup(id):
    backup = db.get_backup(id)
    if backup is None:
        abort(404)
    if request.method == "POST":
        handle_post_delete_backup(id)
        return redirect(url_for("view_target", id=backup.target_id))
    return render_template("delete_backup.html", backup=backup, target_name=db.get_target(backup.target_id).name)

if __name__ == "__main__":
    app.run(debug=config.get("webui_debug"))
