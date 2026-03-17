import dataclasses
import logging
import api.utility as apiutil
from api.context import APIContext
from flask import request, jsonify

TARGET_REQUIRED_PARAMETERS = [
    "name", "backup_type", "recycle_criteria", "recycle_value", "recycle_action", "location", "name_template"
]

def add_routes(context: APIContext):
    logger = logging.getLogger("apitargets")

    @context.blueprint.route("/target", methods=["GET"])
    @context.auth.requires_auth
    def list_targets():
        page = int(request.args.get("page", 1))
        targets = context.db.list_targets(page)["targets"]
        return jsonify(success=True, targets=[dataclasses.asdict(target) for target in targets]), 200

    @context.blueprint.route("/target", methods=["POST"])
    @context.auth.requires_auth
    def new_target():
        data = request.get_json()
        verify_result = apiutil.verify_data_present(data, TARGET_REQUIRED_PARAMETERS)
        if verify_result is not None:
            return verify_result

        try:
            target_id = context.db.add_target(data["name"], data["backup_type"], data["recycle_criteria"], data["recycle_value"], data["recycle_action"], data["location"], data["name_template"], data["deduplicate"], data["alias"], data["min_backups"], data["tags"])
        except Exception as exc:
            # TODO to recognize between invalid requests and internal errors,
            #      run validation in this function.
            #      Though this would run validation twice.
            #      A solution is to manually run validate_target first, not in add_target.
            logger.error("Failed to add target", exc_info=exc)
            return apiutil.failure_response(str(exc)), 500
        return jsonify(success=True, id=target_id), 201

    @context.blueprint.route("/target/<id>", methods=["GET"])
    @context.auth.requires_auth
    def view_target(id):
        target = context.db.get_target(id)
        if target is None:
            return jsonify(success=False), 404
        backups = context.db.list_backups_target(id)
        return jsonify(success=True, target=dataclasses.asdict(target), backups=[backup.asdict() for backup in backups]), 200

    @context.blueprint.route("/target/<id>", methods=["PATCH"])
    @context.auth.requires_auth
    def edit_target(id):
        target = context.db.get_target(id)
        if target is None:
            return jsonify(success=False), 404

        data = request.get_json()
        verify_result = apiutil.verify_data_present(data, TARGET_REQUIRED_PARAMETERS, ["backup_type"])
        if verify_result is not None:
            return verify_result

        context.server_api.edit_target(id, data["name"], data["recycle_criteria"], data["recycle_value"], data["recycle_action"], data["location"], data["name_template"], data["deduplicate"], data["alias"], data["min_backups"], data["tags"])
        return jsonify(success=True), 200

    @context.blueprint.route("/target/<id>", methods=["DELETE"])
    @context.auth.requires_auth
    def delete_target(id):
        data = request.get_json()
        verify_result = apiutil.verify_data_present(data, ["delete_files"])
        if verify_result is not None:
            return verify_result

        context.server_api.delete_target(id, data["delete_files"])
        return jsonify(success=True), 200

    @context.blueprint.route("/target/<id>/all", methods=["DELETE"])
    @context.auth.requires_auth
    def delete_target_backups(id):
        target = context.db.get_target(id)
        if target is None:
            return jsonify(success=False), 404

        data = request.get_json()
        verify_result = apiutil.verify_data_present(data, ["delete_files"])
        if verify_result is not None:
            return verify_result

        context.server_api.delete_target_backups(id, data["delete_files"])
        return jsonify(success=True), 200

    @context.blueprint.route("/target/<id>/recycled", methods=["DELETE"])
    @context.auth.requires_auth
    def delete_target_recycled(id):
        target = context.db.get_target(id)
        if target is None:
            return jsonify(success=False), 404

        data = request.get_json()
        verify_result = apiutil.verify_data_present(data, ["delete_files"])
        if verify_result is not None:
            return verify_result

        context.server_api.delete_target_recycled_backups(id, data["delete_files"])
        return jsonify(success=True), 200

    @context.blueprint.route("/target/search")
    @context.auth.requires_auth
    def search_targets():
        # TODO shared logic for getting search params
        name = request.args.get("name", None)
        target_type = request.args.get("type", None)
        recycle_criteria = request.args.get("recycle_criteria", None)
        recycle_action = request.args.get("recycle_action", None)
        location = request.args.get("location", None)
        name_template = request.args.get("name_template", None)
        deduplicate = True if request.args.get("deduplicate", None) == "on" else False if request.args.get("deduplicate", None) else None
        alias = request.args.get("alias", None)
        tags = request.args.get("tags", "").split()

        if not name and not target_type and not recycle_criteria and not recycle_action and not location and not name_template and deduplicate is None and not alias and not tags:
            return jsonify(success=False), 400

        results = context.db.search_targets(SearchQuery(name, target_type, recycle_criteria, recycle_action, location, name_template, deduplicate, alias, tags))
        return jsonify(success=True, targets=[dataclasses.asdict(target) for target in results]), 200
