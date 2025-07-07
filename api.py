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

        @self.blueprint.route("/target/new", methods=["POST"])
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

        @self.blueprint.route("/target/<id>/edit", methods=["POST"])
        @requires_auth
        def edit_target(id):
            data = request.get_json()
            self.db.edit_target(id, data["name"], data["recycle_criteria"], data["recycle_value"], data["recycle_action"], data["location"], data["name_template"])
            return jsonify(success=True), 204

        @self.blueprint.route("/target/<id>/delete", methods=["POST"])
        @requires_auth
        def delete_target(id):
            data = request.get_json()
            self.server_api.delete_target(id, data["delete_files"])
            return jsonify(success=True), 204
