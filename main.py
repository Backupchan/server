#!/usr/bin/python3

import database
import serverconfig
import traceback
import sys
from flask import Flask, render_template, request, redirect, url_for

config = serverconfig.get_server_config()
db = database.Database(config.get("db_path"))

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
        db.edit_target(target_id, request.form["name"], request.form["backup_type"], request.form["recycle_criteria"], request.form["recycle_value"], request.form["recycle_action"], request.form["location"], request.form["name_template"])
    except Exception as exc:
        print(traceback.format_exc(), file=sys.stderr)
        return str(exc)
    return None

def handle_post_delete_target(target_id: str):
    app.logger.info(f"Handle POST delete target with data: {request.form}")
    db.delete_target(target_id, bool(request.form.get("delete_files")))

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
    return render_template("view_target.html", target=target)

@app.route("/target/<id>/upload", methods=["GET", "POST"])
def upload_backup(id):
    target = db.get_target(id)
    return render_template("upload_backup.html", target=target)

@app.route("/target/<id>/edit", methods=["GET", "POST"])
def edit_target(id):
    target = db.get_target(id)
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
    if request.method == "POST":
        handle_post_delete_target(id) # shouldn't really fail
        return redirect(url_for("list_targets"))
    return render_template("delete_target.html", target=target)

if __name__ == "__main__":
    app.run(debug=config.get("webui_debug"))
