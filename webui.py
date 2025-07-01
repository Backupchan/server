import database
import file_manager
import serverapi
import recycle_daemon
import functools
import logging
import sys
import traceback
import config
import uuid
import os
import datetime
from flask import Blueprint, render_template, request, redirect, url_for, abort, session
from werkzeug.security import check_password_hash

class WebUI:
    def __init__(self, db: database.Database, fm: file_manager.FileManager, server_api: serverapi.ServerAPI, daemon: recycle_daemon.RecycleDaemon, config: config.Config, passwd_hash: str | None):
        self.db = db
        self.fm = fm
        self.server_api = server_api
        self.daemon = daemon
        self.config = config
        self.passwd_hash = passwd_hash
        self.logger = logging.getLogger(__name__)

        self.blueprint = Blueprint("webui", __name__)
        self.add_routes()

    def add_routes(self):
        #
        # Authentication
        #

        def requires_auth(f):
            @functools.wraps(f)
            def decorated(*args, **kwargs):
                if not self.config.get("webui_auth") or session.get("authed"):
                    return f(*args, **kwargs)
                return redirect("/login")
            return decorated

        @self.blueprint.route("/login", methods=["GET", "POST"])
        def login():
            if request.method == "POST":
                password = request.form["password"]
                if check_password_hash(self.passwd_hash, password):
                    session["authed"] = True
                    return redirect(url_for("webui.list_targets"))
                else:
                    return render_template("login.html", incorrect=True)
            return render_template("login.html")

        #
        # Endpoints
        #

        @self.blueprint.route("/")
        @requires_auth
        def homepage():
            return redirect(url_for("webui.list_targets"))

        @self.blueprint.route("/daemon-recheck")
        @requires_auth
        def daemon_recheck():
            self.daemon.force_recheck()
            return "Forced daemon re-check. Inspect the log for details."

        #
        # Target endpoints
        #

        @self.blueprint.route("/targets")
        @requires_auth
        def list_targets():
            targets = self.db.list_targets()
            return render_template("list_targets.html", targets=targets, num_targets=self.db.count_targets(), num_backups=self.db.count_backups())

        @self.blueprint.route("/target/new", methods=["GET", "POST"])
        @requires_auth
        def new_target():
            if request.method == "POST":
                error_message = self.handle_post_new_target()
                if error_message is None:
                    return redirect(url_for("webui.list_targets"))
                else:
                    return render_template("edit_target.html", target=None, error_message=error_message)
            return render_template("edit_target.html", target=None)

        @self.blueprint.route("/target/<id>")
        @requires_auth
        def view_target(id):
            target = self.db.get_target(id)
            if target is None:
                abort(404)
            active_backups = self.db.list_backups_target_is_recycled(id, False)
            recycled_backups = self.db.list_backups_target_is_recycled(id, True)
            return render_template("view_target.html", target=target, active_backups=active_backups, recycled_backups=recycled_backups, num_backups=len(active_backups) + len(recycled_backups), has_recycled_backups=len(recycled_backups) > 0)

        @self.blueprint.route("/target/<id>/upload", methods=["GET", "POST"])
        @requires_auth
        def upload_backup(id):
            target = self.db.get_target(id)
            if target is None:
                abort(404)
            if request.method == "POST":
                error_message = self.handle_post_upload_backup(id)
                if error_message is None:
                    return redirect(url_for("webui.view_target", id=id))
                else:
                    return render_template("upload_backup.html", target=target, error_message=error_message)
            return render_template("upload_backup.html", target=target)

        @self.blueprint.route("/target/<id>/edit", methods=["GET", "POST"])
        @requires_auth
        def edit_target(id):
            target = self.db.get_target(id)
            if target is None:
                abort(404)
            if request.method == "POST":
                error_message = self.handle_post_edit_target(id)
                if error_message is None:
                    return redirect(url_for("webui.view_target", id=id))
                else:
                    return render_template("edit_target.html", target=target, error_message=error_message)
            return render_template("edit_target.html", target=target)

        @self.blueprint.route("/target/<id>/delete", methods=["GET", "POST"])
        @requires_auth
        def delete_target(id):
            target = self.db.get_target(id)
            if target is None:
                abort(404)
            if request.method == "POST":
                self.handle_post_delete_target(id) # shouldn't really fail
                return redirect(url_for("webui.list_targets"))
            return render_template("delete_target.html", target=target)

        @self.blueprint.route("/target/<id>/delete_all", methods=["GET", "POST"])
        @requires_auth
        def delete_target_backups(id):
            target = self.db.get_target(id)
            if target is None:
                abort(404)
            if request.method == "POST":
                self.handle_post_delete_target_backups(id)
                return redirect(url_for("webui.view_target", id=id))
            return render_template("delete_target_backups.html", target=target)

        #
        # Backup endpoints
        #

        @self.blueprint.route("/backup/<id>/delete", methods=["GET", "POST"])
        @requires_auth
        def delete_backup(id):
            backup = self.db.get_backup(id)
            if backup is None:
                abort(404)
            if request.method == "POST":
                self.handle_post_delete_backup(id)
                return redirect(url_for("webui.view_target", id=backup.target_id))
            return render_template("delete_backup.html", backup=backup, target_name=self.db.get_target(backup.target_id).name)

        @self.blueprint.route("/backup/<id>/recycle", methods=["GET", "POST"])
        @requires_auth
        def recycle_backup(id):
            backup = self.db.get_backup(id)
            if backup is None:
                abort(404)
            if backup.is_recycled:
                abort(400)
            if request.method == "POST":
                self.handle_post_recycle_backup(id)
                return redirect(url_for("webui.view_target", id=backup.target_id))
            return render_template("recycle_backup.html", backup=backup, target_name=self.db.get_target(backup.target_id).name)

        @self.blueprint.route("/backup/<id>/unrecycle", methods=["GET", "POST"])
        @requires_auth
        def unrecycle_backup(id):
            backup = self.db.get_backup(id)
            if backup is None:
                abort(404)
            if not backup.is_recycled:
                abort(400)
            if request.method == "POST":
                self.handle_post_unrecycle_backup(id)
                return redirect(url_for("webui.view_target", id=backup.target_id))
            return render_template("unrecycle_backup.html", backup=backup, target_name=self.db.get_target(backup.target_id).name)
        
        @self.blueprint.route("/recycle_bin")
        @requires_auth
        def recycle_bin():
            backups = self.db.list_backups_is_recycled(True)
            backups_and_targets = []
            for backup in backups:
                backups_and_targets.append({"backup": backup, "target": self.db.get_target(backup.target_id)})
            return render_template("recycle_bin.html", backups=backups_and_targets, num_backups=len(backups))
        
        @self.blueprint.route("/recycle_bin/clear", methods=["GET", "POST"])
        @requires_auth
        def recycle_bin_clear():
            if request.method == "POST":
                self.handle_post_recycle_bin_clear()
                return redirect(url_for("webui.recycle_bin"))
            return render_template("recycle_bin_clear.html")

    #
    # POST request handlers
    #

    def handle_post_new_target(self) -> str | None:
        self.logger.info(f"Handle POST new target with data: {request.form}")
        try:
            self.db.add_target(request.form["name"], request.form["backup_type"], request.form["recycle_criteria"], request.form["recycle_value"], request.form["recycle_action"], request.form["location"], request.form["name_template"])
        except Exception as exc:
            return str(exc)
        return None

    def handle_post_edit_target(self, target_id: str) -> str | None:
        self.logger.info(f"Handle POST edit target with data: {request.form}")
        try:
            self.server_api.edit_target(target_id, request.form["name"], request.form["recycle_criteria"], request.form["recycle_value"], request.form["recycle_action"], request.form["location"], request.form["name_template"])
        except Exception as exc:
            print(traceback.format_exc(), file=sys.stderr)
            return str(exc)
        return None

    def handle_post_delete_target(self, target_id: str):
        self.logger.info(f"Handle POST delete target with data: {request.form}")
        self.server_api.delete_target(target_id, bool(request.form.get("delete_files")))

    def move_uploaded_backup(self) -> str:
        uploaded_file = request.files["backup_file"]
        temp_path = f"{self.config.get('temp_save_path')}/{uuid.uuid4().hex}_{uploaded_file.filename}"
        os.makedirs(self.config.get("temp_save_path"), exist_ok=True)
        uploaded_file.save(temp_path)
        return temp_path

    def handle_post_upload_backup(self, target_id: str) -> str | None:
        # TODO not sure if this can be extracted to server api as well
        self.logger.info(f"Handle POST upload backup with data: {request.form}")
        backup_id = ""
        try:
            backup_id = self.db.add_backup(target_id, datetime.datetime.now(), True) # Always manual via the browser
            backup_filename = self.move_uploaded_backup()
            self.logger.info(f"Uploaded file saved as {backup_filename}")
        except Exception as exc:
            self.db.delete_backup(backup_id)
            print(traceback.format_exc(), file=sys.stderr)
            return str(exc)

        try:
            self.fm.add_backup(backup_id, backup_filename)
        except Exception as exc:
            # if this fails we delete the freaking backup
            self.db.delete_backup(backup_id)
            print(traceback.format_exc(), file=sys.stderr)
            return str(exc)
        return None

    def handle_post_delete_backup(self, backup_id: str):
        self.logger.info(f"Handle POST delete backup with data: {request.form}")
        self.server_api.delete_backup(backup_id, bool(request.form.get("delete_files")))

    def handle_post_delete_target_backups(self, target_id: str):
        self.logger.info(f"Handle POST delete target backups with data: {request.form}")
        self.server_api.delete_backup(target_id, bool(request.form.get("delete_files")))

    def handle_post_recycle_backup(self, backup_id: str):
        self.logger.info(f"Handle POST recycle backup with data: {request.form}") # TODO function for logging this?
        self.server_api.recycle_backup(backup_id)

    def handle_post_unrecycle_backup(self, backup_id: str):
        self.logger.info(f"Handle POST unrecycle backup with data: {request.form}")
        self.server_api.unrecycle_backup(backup_id)

    def handle_post_recycle_bin_clear(self):
        self.logger.info(f"Handler POST recycle bin clear with data: {request.form}")
        self.server_api.recycle_bin_clear(bool(request.form.get("delete_files")))
