import database
from backupchan_server import utility, models
from web.auth import WebAuth
from web.sort_options import parse_sort_options
from web.context import WebContext
from web import post_handlers
from search_query import SearchQuery
from flask import Blueprint, request, render_template, redirect, url_for

def get_target_infos(targets: list[models.BackupTarget], db: database.Database):
    target_infos = []
    for target in targets:
        backups = db.list_backups_target(target.id)
        target_infos.append(
                (target,
                 len(backups),
                 utility.humanread_file_size(sum([backup.filesize for backup in backups]))
            )
        )
    return target_infos

def add_routes(context: WebContext):
    @context.blueprint.route("/targets")
    @context.auth.requires_auth
    def list_targets():
        page = int(request.args.get("page", 1))
        sort_options = parse_sort_options(database.TargetSortOptions)
        target_list = context.db.list_targets(page, sort_options)
        targets = target_list["targets"]
        has_more = target_list["has_more"]
        target_infos = []
        for target in targets:
            backups = context.db.list_backups_target(target.id)
            target_infos.append(
                    (target,
                     len(backups),
                     utility.humanread_file_size(sum([backup.filesize for backup in backups]))
                )
            )
        return render_template("list_targets.html", targets=target_infos, num_targets=context.db.count_targets(), num_backups=context.db.count_backups(), page=page, has_more=has_more)

    @context.blueprint.route("/target/new", methods=["GET", "POST"])
    @context.auth.requires_auth
    def new_target():
        if request.method == "POST":
            error_message = post_handlers.new_target(context.db)
            if error_message is None:
                return redirect(url_for("webui.list_targets"))
            else:
                return render_template("edit_target.html", target=None, error_message=error_message)
        return render_template("edit_target.html", target=None)

    @context.blueprint.route("/target/<id>")
    @context.auth.requires_auth
    def view_target(id):
        target = context.db.get_target(id)
        if target is None:
            abort(404)
        sort_options = parse_sort_options(database.BackupSortOptions)
        active_backups = context.db.list_backups_target_is_recycled(id, False, sort_options)
        recycled_backups = context.db.list_backups_target_is_recycled(id, True, sort_options)
        return render_template(
                "view_target.html",
                target=target,
                active_backups=active_backups,
                recycled_backups=recycled_backups,
                num_backups=len(active_backups) + len(recycled_backups),
                has_recycled_backups=len(recycled_backups) > 0,
                num_recycled_backups=len(recycled_backups))

    @context.blueprint.route("/target/<id>/upload", methods=["GET", "POST"])
    @context.auth.requires_auth
    def upload_backup(id):
        target = context.db.get_target(id)
        if target is None:
            abort(404)
        if request.method == "POST":
            error_message = post_handlers.upload_backup(id, context.db, context.config, context.job_manager, context.server_api)
            if error_message is None:
                return redirect(url_for("webui.view_target", id=id))
            else:
                return render_template("upload_backup.html", target=target, error_message=error_message)
        return render_template("upload_backup.html", target=target)

    @context.blueprint.route("/target/<id>/edit", methods=["GET", "POST"])
    @context.auth.requires_auth
    def edit_target(id):
        target = context.db.get_target(id)
        if target is None:
            abort(404)
        if request.method == "POST":
            error_message = post_handlers.edit_target(id, context.server_api)
            if error_message is None:
                return redirect(url_for("webui.view_target", id=id))
            else:
                return render_template("edit_target.html", target=target, error_message=error_message)
        return render_template("edit_target.html", target=target)

    @context.blueprint.route("/target/<id>/delete", methods=["GET", "POST"])
    @context.auth.requires_auth
    def delete_target(id):
        target = context.db.get_target(id)
        if target is None:
            abort(404)
        if request.method == "POST":
            post_handlers.delete_target(id, context.server_api) # shouldn't really fail
            return redirect(url_for("webui.list_targets"))
        return render_template("delete_target.html", target=target)

    @context.blueprint.route("/target/<id>/delete_all", methods=["GET", "POST"])
    @context.auth.requires_auth
    def delete_target_backups(id):
        target = context.db.get_target(id)
        if target is None:
            abort(404)
        if request.method == "POST":
            post_handlers.delete_target_backups(id, context.server_api)
            return redirect(url_for("webui.view_target", id=id))
        return render_template("delete_target_backups.html", target=target)

    @context.blueprint.route("/target/<id>/delete_recycled", methods=["GET", "POST"])
    @context.auth.requires_auth
    def delete_target_recycled(id):
        target = context.db.get_target(id)
        if target is None:
            abort(404)
        if request.method == "POST":
            post_handlers.delete_target_recycled(id, context.server_api)
            return redirect(url_for("webui.view_target", id=id))
        return render_template("delete_target_recycled.html", target=target)

    @context.blueprint.route("/target/search")
    @context.auth.requires_auth
    def search_targets():
        name = request.args.get("name", None)
        target_type = request.args.get("type", None)
        recycle_criteria = request.args.get("recycle_criteria", None)
        recycle_action = request.args.get("recycle_action", None)
        location = request.args.get("location", None)
        name_template = request.args.get("name_template", None)
        deduplicate = True if request.args.get("deduplicate", None) == "on" else False if request.args.get("deduplicate", None) else None
        alias = request.args.get("alias", None)
        tags = request.args.get("tags", "").split()

        # If there's any search criteria, run the search and list the results.
        if name or target_type or recycle_criteria or recycle_action or location or name_template or deduplicate is not None or alias or tags:
            results = context.db.search_targets(SearchQuery(name, target_type, recycle_criteria, recycle_action, location, name_template, deduplicate, alias, tags))
            target_infos = get_target_infos(results, context.db)
            return render_template("list_targets.html", targets=target_infos, search=True, page=1, has_more=False, num_targets=len(target_infos))

        # Otherwise, show search options page.
        return render_template("search_targets.html")
