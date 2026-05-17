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
        return redirect(url_for("webui.dashboard"))

    @context.blueprint.route("/favicon.ico")
    def favicon():
        return send_from_directory(utility.join_path(context.root_path, "static"), "favicon.ico", mimetype="vnd.microsoft.icon")

    @context.blueprint.route("/dashboard")
    @context.auth.requires_auth
    def dashboard():
        return None

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
        return render_template("view_stats.html", stats=context.stats, db=context.db, program_version=PROGRAM_VERSION)

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
        return render_template("list_jobs.html", job_scheduler=context.job_scheduler, job_manager=context.job_manager, seq_upload_manager=context.seq_upload_manager)
