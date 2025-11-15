import database
import file_manager
import serverapi
import scheduled_jobs
import delayed_jobs
import stats
import download
import log
import configtony
import functools
import logging
import sys
import traceback
import uuid
import os
import datetime
from version import PROGRAM_VERSION
from backupchan_server import utility
from backupchan_server import BackupType
from flask import Blueprint, render_template, request, redirect, url_for, abort, session, send_from_directory, send_file
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

def parse_sort_options(kind: type[database.SortOptions]) -> database.SortOptions | None:
    column = request.args.get("s")
    if column is None:
        return None

    asc = request.args.get("a", "1") == "1"
    return kind(asc, column)

class WebUI:
    def __init__(self, db: database.Database, fm: file_manager.FileManager, server_api: serverapi.ServerAPI, job_scheduler: scheduled_jobs.JobScheduler, job_manager: delayed_jobs.JobManager, stats: stats.Stats, config: configtony.Config, passwd_hash: str | None, root_path: str):
        self.db = db
        self.fm = fm
        self.server_api = server_api
        self.job_scheduler = job_scheduler
        self.job_manager = job_manager
        self.stats = stats
        self.config = config
        self.passwd_hash = passwd_hash
        self.root_path = root_path
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
                if not self.passwd_hash or not self.config.get("webui_auth") or session.get("authed"):
                    return f(*args, **kwargs)
                return redirect(url_for("webui.login", return_url=request.path))
            return decorated

        @self.blueprint.route("/login", methods=["GET", "POST"])
        def login():
            return_url = request.args.get("return_url")
            if request.method == "POST":
                password = request.form["password"]
                if check_password_hash(self.passwd_hash, password):
                    session["authed"] = True
                    return redirect(return_url or url_for("webui.list_targets"))
                else:
                    return render_template("login.html", incorrect=True, return_url=return_url)
            return render_template("login.html", return_url=return_url)

        #
        # Miscellaneous endpoints
        #

        @self.blueprint.route("/")
        @requires_auth
        def homepage():
            return redirect(url_for("webui.list_targets"))

        @self.blueprint.route("/favicon.ico")
        def favicon():
            return send_from_directory(os.path.join(self.root_path, "static"), "favicon.ico", mimetype="vnd.microsoft.icon")

        @self.blueprint.route("/force-run-job/<name>")
        @requires_auth
        def force_run_job(name: str):
            self.job_scheduler.force_run_job(name)
            return render_template("force_run_job.html", name=name)

        @self.blueprint.route("/stats")
        @requires_auth
        def view_stats():
            total_target_size = self.stats.total_target_size()
            total_target_size_str = utility.humanread_file_size(total_target_size)
            total_recycle_bin_size = self.stats.total_recycle_bin_size()
            total_recycle_bin_size_str = utility.humanread_file_size(total_recycle_bin_size)
            total_targets = self.db.count_targets()
            total_backups = self.db.count_backups()
            total_recycled_backups = self.db.count_recycled_backups()
            return render_template("view_stats.html",
                                   total_target_size=total_target_size_str,
                                   total_target_size_bytes=total_target_size,
                                   total_recycle_bin_size=total_recycle_bin_size_str,
                                   total_recycle_bin_size_bytes=total_recycle_bin_size,
                                   total_targets=total_targets,
                                   total_backups=total_backups,
                                   total_recycled_backups=total_recycled_backups,
                                   program_version=PROGRAM_VERSION)

        @self.blueprint.route("/log")
        @requires_auth
        def view_log():
            # TODO function for this
            tail = 0
            if "tail" in request.args:
                tail = int(request.args["tail"])
            try:
                log_content = log.read(tail)
            except Exception as exc:
                self.logger.error("Unable to read log", exc_info=exc)
                log_content = f"Could not read log file: {str(exc)}"
            return render_template("log.html", content=log_content, tail=tail)

        @self.blueprint.route("/jobs")
        @requires_auth
        def list_jobs():
            return render_template("list_jobs.html", scheduled_jobs=self.job_scheduler.jobs, delayed_jobs=self.job_manager.jobs)

        #
        # Target endpoints
        #

        @self.blueprint.route("/targets")
        @requires_auth
        def list_targets():
            page = int(request.args.get("page", 1))
            sort_options = parse_sort_options(database.TargetSortOptions)
            targets = self.db.list_targets(page, sort_options)
            target_infos = []
            for target in targets:
                backups = self.db.list_backups_target(target.id)
                target_infos.append(
                        (target,
                         len(backups),
                         utility.humanread_file_size(sum([backup.filesize for backup in backups]))
                    )
                )
            return render_template("list_targets.html", targets=target_infos, num_targets=self.db.count_targets(), num_backups=self.db.count_backups(), page=page)

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
            sort_options = parse_sort_options(database.BackupSortOptions)
            active_backups = self.db.list_backups_target_is_recycled(id, False, sort_options)
            recycled_backups = self.db.list_backups_target_is_recycled(id, True, sort_options)
            return render_template("view_target.html", target=target, active_backups=active_backups, recycled_backups=recycled_backups, num_backups=len(active_backups) + len(recycled_backups), has_recycled_backups=len(recycled_backups) > 0, num_recycled_backups=len(recycled_backups))

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

        @self.blueprint.route("/target/<id>/delete_recycled", methods=["GET", "POST"])
        @requires_auth
        def delete_target_recycled(id):
            target = self.db.get_target(id)
            if target is None:
                abort(404)
            if request.method == "POST":
                self.handle_post_delete_target_recycled(id)
                return redirect(url_for("webui.view_target", id=id))
            return render_template("delete_target_recycled.html", target=target)

        #
        # Backup endpoints
        #

        @self.blueprint.route("/backup/<id>/download", methods=["GET"])
        @requires_auth
        def download_backup(id):
            backup = self.db.get_backup(id)
            if backup is None:
                abort(404)
            target = self.db.get_target(backup.target_id)
            if target is None:
                abort(404) # shouldn't happen but ok

            return send_file(download.get_download_path(backup, target, self.fm.recycle_bin_path, self.config.get("temp_save_path"), self.fm), as_attachment=True)

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
            sort_options = parse_sort_options(database.BackupSortOptions)
            backups = self.db.list_recycled_backups(sort_options)
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

        @self.blueprint.route("/backup/bulk_edit", methods=["POST"])
        @requires_auth
        def bulk_edit():
            # TODO Create a separate POST handler for this.
            # I didn't bother with one for now as this is quite complex unlike all the other ones
            self.post_log("bulk edit")
            all_target_id = request.form.get("select_all_backups")
            execute = request.form.get("bulk_edit_execute")
            backups = []
            recycled_type = request.form.get("recycled_type")

            action = None
            if execute:
                action = request.form.get("action")
            else:
                if request.form.get("bulk_recycle") == "Recycle":
                    action = "recycle"
                elif request.form.get("bulk_unrecycle") == "Restore":
                    action = "unrecycle"
                elif request.form.get("bulk_delete") == "Delete":
                    action = "delete"
                else:
                    return render_template("bulk_edit_confirm.html", error="Invalid action specified")

            if execute:
                backups = request.form.get("backup_ids").split(";")
            else:
                if all_target_id is not None:
                    if recycled_type == "only_recycled":
                        backups = self.db.list_backups_target_is_recycled(all_target_id, True)
                    elif recycled_type == "only_active":
                        backups = self.db.list_backups_target_is_recycled(all_target_id, False)
                    else:
                        backups = self.db.list_backups_target(all_target_id)
                else:
                    for key, value in request.form.items():
                        if key.startswith("backup"):
                            backup_id = key[6:]
                            backups.append(self.db.get_backup(backup_id))

                if len(backups) == 0:
                    return render_template("bulk_edit_confirm.html", error="No backups selected")
                if all_target_id is not None and self.db.get_target(all_target_id) is None:
                    return render_template("bulk_edit_confirm.html", error="Invalid target specified")

            if execute:
                if action == "recycle":
                    for backup_id in backups:
                        self.server_api.recycle_backup(backup_id)
                elif action == "unrecycle":
                    for backup_id in backups:
                        self.server_api.unrecycle_backup(backup_id)
                elif action == "delete":
                    for backup_id in backups:
                        self.server_api.delete_backup(backup_id, True)
                return redirect(url_for("webui.list_targets"))

            return render_template("bulk_edit_confirm.html", backups=backups, error=None, action=action, backup_ids=";".join([backup.id for backup in backups]))

    #
    # POST request handlers
    #

    def handle_post_new_target(self) -> str | None:
        self.post_log("new target")

        if not "recycle_value" in request.form and request.form["recycle_criteria"] != "none":
            return "Specify a recycle value"

        try:
            self.db.add_target(request.form["name"], request.form["backup_type"], request.form["recycle_criteria"], request.form.get("recycle_value", 0), request.form.get("recycle_action", "none"), request.form["location"], request.form["name_template"], int("deduplicate" in request.form), request.form.get("alias", None) or None, request.form.get("min_backups", 0))
        except Exception as exc:
            return str(exc)
        return None

    def handle_post_edit_target(self, target_id: str) -> str | None:
        self.post_log("edit target")

        if not "recycle_value" in request.form and request.form["recycle_criteria"] != "none":
            return "Specify a recycle value"

        try:
            self.server_api.edit_target(target_id, request.form["name"], request.form["recycle_criteria"], request.form.get("recycle_value", 0), request.form.get("recycle_action", "none"), request.form["location"], request.form["name_template"], int("deduplicate" in request.form), request.form.get("alias", None) or None, request.form.get("min_backups", 0))
        except Exception as exc:
            return str(exc)
        return None

    def handle_post_delete_target(self, target_id: str):
        self.post_log("delete target")
        self.server_api.delete_target(target_id, bool(request.form.get("delete_files")))

    def handle_post_upload_backup(self, target_id: str) -> str | None:
        self.post_log("upload backup")

        # Saving the file is done separately as it gets closed after the request, but the job runs after it.
        files = request.files.getlist("backup_file")
        if len(files) == 0:
            return "No files specified"
        if len(files) != 1 and self.db.get_target(target_id).target_type == "single":
            return "Cannot upload multiple files to a single-file target" # Technically shouldn't happen but who knows
        filenames = []
        for file in files:
            filename = os.path.join(self.config.get("temp_save_path"), f"{uuid.uuid4().hex}_{file.filename}")
            os.makedirs(self.config.get("temp_save_path"), exist_ok=True)
            file.save(filename)
            filenames.append(filename)

        try:
            self.job_manager.run_job(delayed_jobs.UploadJob(target_id, True, filenames, self.server_api))
        except Exception as exc:
            print(traceback.format_exc(), file=sys.stderr)
            return str(exc)
        return None

    def handle_post_delete_backup(self, backup_id: str):
        self.post_log("delete backup")
        self.server_api.delete_backup(backup_id, bool(request.form.get("delete_files")))

    def handle_post_delete_target_backups(self, target_id: str):
        self.post_log("delete target backups")
        self.server_api.delete_target_backups(target_id, bool(request.form.get("delete_files")))

    def handle_post_delete_target_recycled(self, target_id: str):
        self.post_log("delete target recycled")
        self.server_api.delete_target_recycled_backups(target_id, bool(request.form.get("delete_files")))

    def handle_post_recycle_backup(self, backup_id: str):
        self.post_log("recycle backup")
        self.server_api.recycle_backup(backup_id)

    def handle_post_unrecycle_backup(self, backup_id: str):
        self.post_log("unrecycle backup")
        self.server_api.unrecycle_backup(backup_id)

    def handle_post_recycle_bin_clear(self):
        self.post_log("recycle bin clear")
        self.server_api.recycle_bin_clear(bool(request.form.get("delete_files")))
    
    def post_log(self, message: str):
        self.logger.info(f"Handle POST {message} with data: {request.form}")
