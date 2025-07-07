import database
import serverapi
import logging
import functools
import json
import dataclasses
from flask import Blueprint, jsonify, request

class API:
    """
    Refer to API.md for documentaton on the JSON API.
    """
    def __init__(self, db: database.Database, server_api: serverapi.ServerAPI):
        self.db = db
        self.server_api = server_api
        self.logger = logging.getLogger(__name__)

        self.blueprint = Blueprint("api", __name__)
        self.add_routes()

    def add_routes(self):
        # TODO impleent custom JSON error handlers
        # TODO error handling

        #
        # Authentication (TODO)
        #

        def requires_auth(f):
            @functools.wraps(f)
            def decorated(*args, **kwargs):
                return f(*args, **kwargs)
            return decorated

        #
        # Target endpoints
        #

        # TODO consider renaming into /target/list for consistency with other target endpoints
        @self.blueprint.route("/targets", methods=["GET"])
        @requires_auth
        def list_targets():
            targets = self.db.list_targets()
            return json.dumps([dataclasses.asdict(target) for target in targets])

        @self.blueprint.route("/target", methods=["POST"])
        @requires_auth
        def new_target():
            data = request.get_json()
            self.db.add_target(data["name"], data["backup_type"], data["recycle_criteria"], data["recycle_value"], data["recycle_action"], data["location"], data["name_template"])
            return jsonify(success=True), 201

        @self.blueprint.route("/target/<id>", methods=["GET"])
        @requires_auth
        def view_target(id):
            target = self.db.get_target(id)
            return json.dumps(dataclasses.asdict(target))

        @self.blueprint.route("/target/<id>", methods=["PATCH"])
        @requires_auth
        def edit_target(id):
            data = request.get_json()
            self.db.edit_target(id, data["name"], data["recycle_criteria"], data["recycle_value"], data["recycle_action"], data["location"], data["name_template"])
            return jsonify(success=True), 204

        @self.blueprint.route("/target/<id>", methods=["DELETE"])
        @requires_auth
        def delete_target(id):
            data = request.get_json()
            self.server_api.delete_target(id, data["delete_files"])
            return jsonify(success=True), 204

        @self.blueprint.route("/target/<id>/all", methods=["DELETE"])
        @requires_auth
        def delete_target_backups(id):
            data = request.get_json()
            self.server_api.delete_target_backups(id, data["delete_files"])
            return jsonify(success=True), 204

        @self.blueprint.route("/backup/<id>", methods=["DELETE"])
        @requires_auth
        def delete_backup(id):
            data = request.get_json()
            self.server_api.delete_backup(id, data["delete_files"])
            return jsonify(success=True), 204

        @self.blueprint.route("/backup/<id>", methods=["PATCH"])
        @requires_auth
        def recycle_backup(id):
            data = request.get_json()
            if data["is_recycled"]:
                self.server_api.recycle_backup(id)
            else:
                self.server_api.unrecycle_backup(id)
            return jsonify(success=True), 204

        @self.blueprint.route("/recycle_bin", methods=["GET"])
        @requires_auth
        def recycle_bin():
            recycle_bin = self.db.list_backups_is_recycled(True)
            return json.dumps([dataclasses.asdict(backup) for backup in recycle_bin])

        @self.blueprint.route("/recycle_bin", methods=["DELETE"])
        @requires_auth
        def recycle_bin_clear():
            data = request.get_json()
            self.server_api.recycle_bin_clear(data["delete_files"])
            return jsonify(success=True), 204
