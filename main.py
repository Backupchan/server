#!/usr/bin/python3

import database
import serverconfig
from flask import Flask, render_template, request, redirect, url_for

config = serverconfig.get_server_config()
db = database.Database(config.get("db_path"))

app = Flask(__name__)

# POST request handlers

def handle_post_new_target() -> str | None:
    # TODO add error-checking
    db.add_target(request.form["name"], request.form["backup_type"], request.form["recycle_criteria"], request.form["recycle_value"], request.form["recycle_action"], request.form["location"], request.form["name_template"])
    return None

# Endpoints

@app.route("/")
def homepage():
    targets = db.list_targets()
    return render_template("home.html", targets=targets, num_targets=db.count_targets(), num_backups=db.count_backups())

@app.route("/targets")
def list_targets():
    targets = db.list_targets()
    return render_template("list_targets.html", targets=targets, num_targets=db.count_targets())

@app.route("/target/<id>")
def view_target(id):
    target = db.get_target(id)
    return render_template("view_target.html", target=target)

@app.route("/new_target", methods=["GET", "POST"])
def new_target():
    if request.method == "POST":
        error_message = handle_post_new_target()
        if error_message is None:
            return redirect(url_for("list_targets"))
        else:
            return render_template("new_target.html", error_message=error_message)
    return render_template("new_target.html")

if __name__ == "__main__":
    app.run(debug=config.get("webui_debug"))
