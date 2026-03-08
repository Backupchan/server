import database
import file_manager
import stats
import serverapi
import download
from web.auth import WebAuth
from web.sort_options import parse_sort_options
from web.context import WebContext
from web import post_handlers
from configtony import Config
from flask import Blueprint, render_template, redirect, url_for, request, send_file

def add_routes(context: WebContext):
    @context.blueprint.route("/backup/<id>/download", methods=["GET"])
    @context.auth.requires_auth
    def download_backup(id):
        backup = context.db.get_backup(id)
        if backup is None:
            abort(404)
        target = context.db.get_target(backup.target_id)
        if target is None:
            abort(404) # shouldn't happen but ok

        return send_file(download.get_download_path(backup, target, context.fm.recycle_bin_path, context.config.get("temp_save_path"), context.fm), as_attachment=True)

    @context.blueprint.route("/backup/<id>/delete", methods=["GET", "POST"])
    @context.auth.requires_auth
    def delete_backup(id):
        backup = context.db.get_backup(id)
        if backup is None:
            abort(404)
        if request.method == "POST":
            post_handlers.delete_backup(id, context.server_api)
            return redirect(url_for("webui.view_target", id=backup.target_id))
        return render_template("delete_backup.html", backup=backup, target_name=context.db.get_target(backup.target_id).name)

    @context.blueprint.route("/backup/<id>/recycle", methods=["GET", "POST"])
    @context.auth.requires_auth
    def recycle_backup(id):
        backup = context.db.get_backup(id)
        if backup is None:
            abort(404)
        if backup.is_recycled:
            abort(400)
        if request.method == "POST":
            post_handlers.recycle_backup(id, context.server_api)
            return redirect(url_for("webui.view_target", id=backup.target_id))
        return render_template("recycle_backup.html", backup=backup, target_name=context.db.get_target(backup.target_id).name)

    @context.blueprint.route("/backup/<id>/unrecycle", methods=["GET", "POST"])
    @context.auth.requires_auth
    def unrecycle_backup(id):
        backup = context.db.get_backup(id)
        if backup is None:
            abort(404)
        if not backup.is_recycled:
            abort(400)
        if request.method == "POST":
            post_handlers.unrecycle_backup(id, context.server_api)
            return redirect(url_for("webui.view_target", id=backup.target_id))
        return render_template("unrecycle_backup.html", backup=backup, target_name=context.db.get_target(backup.target_id).name)
    
    @context.blueprint.route("/recycle_bin")
    @context.auth.requires_auth
    def recycle_bin():
        sort_options = parse_sort_options(database.BackupSortOptions)
        backups = context.db.list_recycled_backups(sort_options)
        backups_and_targets = []
        for backup in backups:
            backups_and_targets.append({"backup": backup, "target": context.db.get_target(backup.target_id)})
        return render_template("recycle_bin.html", backups=backups_and_targets, num_backups=len(backups), storage=context.stats.total_recycle_bin_size())

    @context.blueprint.route("/recycle_bin/clear", methods=["GET", "POST"])
    @context.auth.requires_auth
    def recycle_bin_clear():
        if request.method == "POST":
            post_handlers.recycle_bin_clear(context.server_api)
            return redirect(url_for("webui.recycle_bin"))
        return render_template("recycle_bin_clear.html")

    @context.blueprint.route("/backup/bulk_edit", methods=["POST"])
    @context.auth.requires_auth
    def bulk_edit():
        # TODO Create a separate POST handler for this.
        # I didn't bother with one for now as this is quite complex unlike all the other ones
        post_handlers.log("bulk edit")
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
                    backups = context.db.list_backups_target_is_recycled(all_target_id, True)
                elif recycled_type == "only_active":
                    backups = context.db.list_backups_target_is_recycled(all_target_id, False)
                else:
                    backups = context.db.list_backups_target(all_target_id)
            else:
                for key, value in request.form.items():
                    if key.startswith("backup"):
                        backup_id = key[6:]
                        backups.append(context.db.get_backup(backup_id))

            if len(backups) == 0:
                return render_template("bulk_edit_confirm.html", error="No backups selected")
            if all_target_id is not None and context.db.get_target(all_target_id) is None:
                return render_template("bulk_edit_confirm.html", error="Invalid target specified")

        if execute:
            if action == "recycle":
                for backup_id in backups:
                    context.server_api.recycle_backup(backup_id)
            elif action == "unrecycle":
                for backup_id in backups:
                    context.server_api.unrecycle_backup(backup_id)
            elif action == "delete":
                for backup_id in backups:
                    context.server_api.delete_backup(backup_id, True)
            return redirect(url_for("webui.list_targets"))

        return render_template("bulk_edit_confirm.html", backups=backups, error=None, action=action, backup_ids=";".join([backup.id for backup in backups]))
