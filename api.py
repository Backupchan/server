import database
import serverapi
import download
import configtony
import file_manager
import stats
import logging
import functools
import json
import dataclasses
import os
import uuid
import datetime
from version import PROGRAM_VERSION
from flask import Blueprint, jsonify, request, Response

TARGET_REQUIRED_PARAMETERS = [
    "name", "backup_type", "recycle_criteria", "recycle_value", "recycle_action", "location", "name_template"
]

def failure_response(message: str) -> Response:
    """
    Returns a failure response in the form of string JSON.
    """
    resp_dict = {
        "success": False,
        "message": message
    }
    return jsonify(resp_dict)

def failure_response_param(param: str) -> Response:
    """
    Returns a failure response with the following message:
    Parameter '<param>' required
    """
    return failure_response(f"Parameter '{param}' required")

def verify_data_present(data: dict, parameters: list[str], omit: list[str] = []) -> None | tuple[Response, int]:
    for parameter in parameters:
        if parameter not in omit and parameter not in data:
            return failure_response_param(parameter), 400
    return None

class API:
    """
    Refer to API.md for documentaton on the JSON API.
    """
    def __init__(self, db: database.Database, server_api: serverapi.ServerAPI, config: configtony.Config, fm: file_manager.FileManager, stats: stats.Stats):
        self.db = db
        self.server_api = server_api
        self.fm = fm
        self.config = config
        self.stats = stats
        self.logger = logging.getLogger(__name__)

        self.blueprint = Blueprint("api", __name__)
        self.init_auth()
        self.add_routes()
    
    def init_auth(self):
        self.key = None
        if os.path.exists("apikey.json"):
            with open("apikey.json") as file:
                file_json = json.load(file)
                if "key" not in file_json:
                    self.logger.warning("API key file is incorrect. Authentication will be disabled.")
                else:
                    self.key = file_json["key"]

    def add_routes(self):
        #
        # Authentication
        #

        def requires_auth(f):
            @functools.wraps(f)
            def decorated(*args, **kwargs):
                if self.key is None:
                    return f(*args, **kwargs)
                
                auth_header = request.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    return failure_response("Unauthorized"), 401
                
                token = auth_header.removeprefix("Bearer ").strip()
                if token != self.key:
                    return failure_response("Invalid API key"), 403
                
                return f(*args, **kwargs)
            return decorated

        #
        # Target endpoints
        #

        @self.blueprint.route("/target", methods=["GET"])
        @requires_auth
        def list_targets():
            page = int(request.args.get("page", 1))
            targets = self.db.list_targets(page)
            return jsonify(success=True, targets=[dataclasses.asdict(target) for target in targets]), 200

        @self.blueprint.route("/target", methods=["POST"])
        @requires_auth
        def new_target():
            data = request.get_json()
            verify_result = verify_data_present(data, TARGET_REQUIRED_PARAMETERS)
            if verify_result is not None:
                return verify_result

            try:
                target_id = self.db.add_target(data["name"], data["backup_type"], data["recycle_criteria"], data["recycle_value"], data["recycle_action"], data["location"], data["name_template"], data["deduplicate"], data["alias"])
            except Exception as exc:
                # TODO to recognize between invalid requests and internal errors,
                #      run validation in this function.
                #      Though this would run validation twice.
                #      A solution is to manually run validate_target first, not in add_target.
                self.logger.error("Failed to add target", exc_info=exc)
                return failure_response(str(exc)), 500
            return jsonify(success=True, id=target_id), 201

        @self.blueprint.route("/target/<id>", methods=["GET"])
        @requires_auth
        def view_target(id):
            target = self.db.get_target(id)
            if target is None:
                return jsonify(success=False), 404
            backups = self.db.list_backups_target(id)
            return jsonify(success=True, target=dataclasses.asdict(target), backups=[backup.asdict() for backup in backups]), 200

        @self.blueprint.route("/target/<id>", methods=["PATCH"])
        @requires_auth
        def edit_target(id):
            target = self.db.get_target(id)
            if target is None:
                return jsonify(success=False), 404

            data = request.get_json()
            verify_result = verify_data_present(data, TARGET_REQUIRED_PARAMETERS, ["backup_type"])
            if verify_result is not None:
                return verify_result

            self.server_api.edit_target(id, data["name"], data["recycle_criteria"], data["recycle_value"], data["recycle_action"], data["location"], data["name_template"], data["deduplicate"], data["alias"])
            return jsonify(success=True), 200

        @self.blueprint.route("/target/<id>", methods=["DELETE"])
        @requires_auth
        def delete_target(id):
            data = request.get_json()
            verify_result = verify_data_present(data, ["delete_files"])
            if verify_result is not None:
                return verify_result

            self.server_api.delete_target(id, data["delete_files"])
            return jsonify(success=True), 200

        @self.blueprint.route("/target/<id>/all", methods=["DELETE"])
        @requires_auth
        def delete_target_backups(id):
            target = self.db.get_target(id)
            if target is None:
                return jsonify(success=False), 404

            data = request.get_json()
            verify_result = verify_data_present(data, ["delete_files"])
            if verify_result is not None:
                return verify_result

            self.server_api.delete_target_backups(id, data["delete_files"])
            return jsonify(success=True), 200

        #
        # Backup endpoints
        #

        @self.blueprint.route("/target/<id>/upload", methods=["POST"])
        @requires_auth
        def upload_backup(id):
            # Check if target exists
            target = self.db.get_target(id)
            if target is None:
                return jsonify(success=False), 404

            # Verify that user supplied data
            data = request.form
            verify_result = verify_data_present(data, ["manual"])
            if verify_result is not None:
                return verify_result

            is_manual = data["manual"]

            # TODO this is copied from webui.py; consider moving into filemanager or something
            #      see WebUI.move_uploaded_backup, WebUI.handle_post_upload_backup

            # Move file to a temporary location
            uploaded_file = request.files["backup_file"]
            temp_path = f"{self.config.get('temp_save_path')}/{uuid.uuid4().hex}_{uploaded_file.filename}"
            try:
                os.makedirs(self.config.get("temp_save_path"), exist_ok=True)
            except Exception as exc:
                self.logger.error("Failed to create file temp path", exc_info=exc)
                return failure_response("Failed to create file temp path"), 500

            uploaded_file.save(temp_path)

            backup_id = None

            # Create backup in the database
            try:
                backup_id = self.db.add_backup(id, is_manual)
            except Exception as exc:
                self.logger.error("Failed to add backup to database", exc_info=exc)
                return failure_response("Failed to add backup to database"), 500

            # Move backup from temp location to real location
            try:
                self.fm.add_backup(backup_id, temp_path)
            except Exception as exc:
                self.db.delete_backup(backup_id)
                self.logger.error("Failed to add backup file", exc_info=exc) # TODO log exceptions like this everywhere
                return failure_response("Failed to add backup file"), 500

            self.db.set_backup_filesize(backup_id, self.fm.get_backup_size(backup_id))
            
            return jsonify(success=True, id=backup_id), 200

        @self.blueprint.route("/backup/<id>/download", methods=["GET"])
        @requires_auth
        def download_backup(id):
            backup = self.db.get_backup(id)
            if backup is None:
                return jsonify(success=False), 404

            target = self.db.get_target(backup.target_id)
            if target is None:
                return jsonify(success=False), 404

            return send_file(download.get_download_path(backup, target, self.fm.recycle_bin_path, self.config.get("temp_save_path"), self.fm), as_attachment=True)

        @self.blueprint.route("/backup/<id>", methods=["DELETE"])
        @requires_auth
        def delete_backup(id):
            backup = self.db.get_backup(id)
            if backup is None:
                return jsonify(success=False), 404

            data = request.get_json()
            verify_result = verify_data_present(data, ["delete_files"])
            if verify_result is not None:
                return verify_result

            self.server_api.delete_backup(id, data["delete_files"])
            return jsonify(success=True), 200

        @self.blueprint.route("/backup/<id>", methods=["PATCH"])
        @requires_auth
        def recycle_backup(id):
            backup = self.db.get_backup(id)
            if backup is None:
                return jsonify(success=False), 404

            data = request.get_json()
            verify_result = verify_data_present(data, ["is_recycled"])
            if verify_result is not None:
                return verify_result

            if data["is_recycled"]:
                self.server_api.recycle_backup(id)
            else:
                self.server_api.unrecycle_backup(id)
            return jsonify(success=True), 200

        #
        # Miscellaneous endpoints
        #

        @self.blueprint.route("/recycle_bin", methods=["GET"])
        @requires_auth
        def recycle_bin():
            recycle_bin = self.db.list_recycled_backups()
            return jsonify(success=True, backups=[backup.asdict() for backup in recycle_bin]), 200

        @self.blueprint.route("/recycle_bin", methods=["DELETE"])
        @requires_auth
        def recycle_bin_clear():
            data = request.get_json()
            verify_result = verify_data_present(data, ["delete_files"])
            if verify_result is not None:
                return verify_result

            self.server_api.recycle_bin_clear(data["delete_files"])
            return jsonify(success=True), 200

        @self.blueprint.route("/log", methods=["GET"])
        @requires_auth
        def get_log():
            tail = 0
            if "tail" in request.args:
                tail = int(request.args["tail"])

            log_content = ""
            with open("./log/backupchan.log", "r") as log_file:
                if tail == 0:
                    log_content = log_file.read()
                else:
                    log_content = "".join(log_file.readlines()[-tail:])
            return jsonify(success=True, log=log_content)

        @self.blueprint.route("/stats", methods=["GET"])
        @requires_auth
        def view_stats():
            total_target_size = self.stats.total_target_size()
            total_recycle_bin_size = self.stats.total_recycle_bin_size()
            total_targets = self.db.count_targets()
            total_backups = self.db.count_backups()
            total_recycled_backups = self.db.count_recycled_backups()

            return jsonify(success=True,
                           program_version=PROGRAM_VERSION,
                           total_target_size=total_target_size,
                           total_recycle_bin_size=total_recycle_bin_size,
                           total_targets=total_targets,
                           total_backups=total_backups,
                           total_recycled_backups=total_recycled_backups
            )
