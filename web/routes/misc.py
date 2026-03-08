import logging
import log
from version import PROGRAM_VERSION
from backupchan_server import utility
from web.auth import WebAuth
from web.context import WebContext
from flask import Blueprint, redirect, url_for, send_from_directory, render_template, request

def add_routes(context: WebContext):
    logger = logging.getLogger("web_misc")

    @context.blueprint.route("/")
    @context.auth.requires_auth
    def homepage():
        return redirect(url_for("webui.list_targets"))

    @context.blueprint.route("/favicon.ico")
    def favicon():
        return send_from_directory(utility.join_path(context.root_path, "static"), "favicon.ico", mimetype="vnd.microsoft.icon")

    @context.blueprint.route("/force-run-job/<name>")
    @context.auth.requires_auth
    def force_run_job(name: str):
        context.job_scheduler.force_run_job(name)
        return render_template("force_run_job.html", name=name)

    @context.blueprint.route("/seq-cancel/<id>", methods=["GET", "POST"])
    @context.auth.requires_auth
    def seq_cancel(id: str):
        if request.method == "POST":
            context.seq_upload_manager.delete(id)
            return redirect(url_for("webui.list_jobs"))
        target = context.db.get_target(id)
        if not target:
            return render_template("cancel_seq_upload.html", target=target, not_found_target=True);
        if id not in context.seq_upload_manager.uploads:
            return render_template("cancel_seq_upload.html", target=target, not_found_seq=True)
        return render_template("cancel_seq_upload.html", target=target);

    @context.blueprint.route("/stats")
    @context.auth.requires_auth
    def view_stats():
        total_target_size = context.stats.total_target_size()
        total_recycle_bin_size = context.stats.total_recycle_bin_size()
        total_targets = context.db.count_targets()
        total_backups = context.db.count_backups()
        total_recycled_backups = context.db.count_recycled_backups()
        return render_template("view_stats.html",
                               total_target_size=total_target_size,
                               total_recycle_bin_size=total_recycle_bin_size,
                               total_targets=total_targets,
                               total_backups=total_backups,
                               total_recycled_backups=total_recycled_backups,
                               program_version=PROGRAM_VERSION)

    @context.blueprint.route("/log")
    @context.auth.requires_auth
    def view_log():
        # TODO function for this
        tail = 100
        if "tail" in request.args:
            tail = int(request.args["tail"])
        try:
            log_content = log.read(tail)
        except Exception as exc:
            logger.error("Unable to read log", exc_info=exc)
            log_content = f"Could not read log file: {str(exc)}"
        return render_template("log.html", content=log.parse(log_content), tail=tail)

    @context.blueprint.route("/jobs")
    @context.auth.requires_auth
    def list_jobs():
        return render_template(
                "list_jobs.html",
                scheduled_jobs=context.job_scheduler.jobs,
                delayed_jobs=context.job_manager.jobs,
                delayed_job_count=len(context.job_manager.jobs),
                seq_uploads=context.seq_upload_manager.uploads)
