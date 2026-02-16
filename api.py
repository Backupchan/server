import database
import serverapi
import download
import configtony
import file_manager
import stats
import delayed_jobs
import scheduled_jobs
import seq_upload
import log
import logging
import functools
import json
import dataclasses
import os
import uuid
import datetime
from backupchan_server import models
from version import PROGRAM_VERSION
from flask import Blueprint, jsonify, request, Response, send_file

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
    def __init__(self, db: database.Database, server_api: serverapi.ServerAPI, config: configtony.Config, fm: file_manager.FileManager, stats: stats.Stats, job_manager: delayed_jobs.JobManager, job_scheduler: scheduled_jobs.JobScheduler, seq_upload_manager: seq_upload.SequentialUploadManager):
        self.db = db
        self.server_api = server_api
        self.fm = fm
        self.config = config
        self.stats = stats
        self.job_manager = job_manager
        self.job_scheduler = job_scheduler
        self.seq_upload_manager = seq_upload_manager
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

    def check_seq_upload(self, target: None | models.BackupTarget) -> None | tuple[Response, int]:
        if target is None:
            return jsonify(success=False), 404

        if not self.seq_upload_manager.is_processing(target.id):
            return jsonify(success=False), 400

        return None


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
                target_id = self.db.add_target(data["name"], data["backup_type"], data["recycle_criteria"], data["recycle_value"], data["recycle_action"], data["location"], data["name_template"], data["deduplicate"], data["alias"], data["min_backups"])
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

            self.server_api.edit_target(id, data["name"], data["recycle_criteria"], data["recycle_value"], data["recycle_action"], data["location"], data["name_template"], data["deduplicate"], data["alias"], data["min_backups"])
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

        @self.blueprint.route("/target/<id>/recycled", methods=["DELETE"])
        @requires_auth
        def delete_target_recycled(id):
            target = self.db.get_target(id)
            if target is None:
                return jsonify(success=False), 404

            data = request.get_json()
            verify_result = verify_data_present(data, ["delete_files"])
            if verify_result is not None:
                return verify_result

            self.server_api.delete_target_recycled_backups(id, data["delete_files"])
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

            files = request.files.getlist("backup_file")
            if len(files) == 0:
                return "No files specified"
            if len(files) != 1 and target.target_type == "single":
                return "Cannot upload multiple files to a single-file target" # More likely to happen in the API if you're not careful
            filenames = []
            for file in files:
                filename = os.path.join(self.config.get("temp_save_path"), f"{uuid.uuid4().hex}_{file.filename}")
                os.makedirs(self.config.get("temp_save_path"), exist_ok=True)
                file.save(filename)
                filenames.append(filename)

            try:
                job_id = self.job_manager.run_job(delayed_jobs.UploadJob(target.id, is_manual, filenames, self.server_api))
            except Exception as exc:
                self.logger.error("Encountered error while uploading backup", exc_info=exc)
                return jsonify(success=False), 500

            return jsonify(success=True, job_id=job_id), 200

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
        # Sequential upload endpoints
        #

        @self.blueprint.route("/seq/<target_id>/begin", methods=["POST"])
        @requires_auth
        def seq_begin(target_id: str):
            target = self.db.get_target(target_id)
            if target is None:
                return jsonify(success=False), 404

            if target.target_type != models.BackupType.MULTI:
                return jsonify(success=False, message="Cannot begin sequential upload on single-file target"), 400

            # Verify that the user passed required data
            data = request.get_json()
            verify_result = verify_data_present(data, ["file_list", "manual"])
            if verify_result is not None:
                return verify_result

            file_list = seq_upload.SequentialFile.list_from_dicts(data["file_list"])

            create_upload_status = self.seq_upload_manager.create_upload(target.id, file_list, data["manual"])
            if create_upload_status == seq_upload.SequentialUploadCreateStatus.VALIDATION_FAILED:
                return jsonify(success=False, message="File list validation failed"), 400
            if create_upload_status == seq_upload.SequentialUploadCreateStatus.TARGET_BUSY:
                return jsonify(success=False, message="Target busy"), 400
            
            return jsonify(success=True), 200

        @self.blueprint.route("/seq/<target_id>", methods=["GET"])
        @requires_auth
        def seq_check(target_id: str):
            target = self.db.get_target(target_id)
            if target is None:
                return jsonify(success=False), 404
            
            if not self.seq_upload_manager.is_processing(target.id):
                return jsonify(success=False), 400

            upload = self.seq_upload_manager[target.id]
            return jsonify(success=True, file_list=[dataclasses.asdict(file) for file in upload.file_list])

        @self.blueprint.route("/seq/<target_id>/upload", methods=["POST"])
        @requires_auth
        def seq_upload_file(target_id: str):
            target = self.db.get_target(target_id)
            verify_result = self.check_seq_upload(target)
            if verify_result is not None:
                return verify_result

            # Verify that user supplied file name and path
            data = request.form
            verify_result = verify_data_present(data, ["name", "path"])
            if verify_result is not None:
                return verify_result

            sequential_file = seq_upload.SequentialFile(data["path"], data["name"], False)

            # Verify that we don't already have that file
            if self.seq_upload_manager[target.id].is_uploaded(sequential_file):
                return jsonify(success=False), 409

            # Verify that it's in the list (and mark as uploaded if it is)
            if not self.seq_upload_manager[target.id].set_uploaded_state(sequential_file, True):
                return jsonify(success=False), 400

            # Verify that they gave a file
            if "file" not in request.files:
                return jsonify(success=False, message="No file given"), 400

            try:
                rel_path = sequential_file.full_path()
                if os.path.isabs(rel_path):
                    rel_path = rel_path.lstrip("/")

                file = request.files["file"]
                filename = os.path.join(self.config.get("temp_save_path"), f"seq_{target.id}", rel_path)
                self.logger.info(f"{sequential_file.full_path()} -> {filename}")
                os.makedirs(os.path.dirname(filename), exist_ok=True)

                file.save(filename)
            except Exception as exc:
                self.logger.error("Error during sequential upload on target {%s}", target.id, exc_info=exc)
                self.seq_upload_manager[target.id].set_uploaded_state(sequential_file, False)
                return jsonify(success=False, message=str(exc)), 500

            self.logger.info("Uploaded file %s to sequential upload on target {%s}", sequential_file, target.id)
            return jsonify(success=True), 200

        @self.blueprint.route("/seq/<target_id>/finish", methods=["POST"])
        @requires_auth
        def seq_finish(target_id: str):
            target = self.db.get_target(target_id)
            verify_result = self.check_seq_upload(target)
            if verify_result is not None:
                return verify_result

            if not self.seq_upload_manager[target.id].all_uploaded():
                return jsonify(success=False), 409

            source_path = os.path.join(self.config.get("temp_save_path"), f"seq_{target.id}")
            backup_id = self.db.add_backup(target.id, self.seq_upload_manager[target.id].manual)
            try:
                self.fm.add_backup(backup_id, [source_path])
            except Exception as exc:
                self.db.delete_backup(backup_id)
                self.logger.error("Error when adding sequential backup files on target {%s}", target.id, exc_info=exc)
                return jsonify(success=False, message=str(exc)), 500

            self.db.set_backup_filesize(backup_id, self.fm.get_backup_size(backup_id))
            self.seq_upload_manager.finish(target.id)

            return jsonify(success=True), 200

        @self.blueprint.route("/seq/<target_id>/terminate", methods=["POST"])
        @requires_auth
        def seq_terminate(target_id: str):
            target = self.db.get_target(target_id)
            verify_result = self.check_seq_upload(target)
            if verify_result is not None:
                return verify_result

            self.seq_upload_manager.delete(target.id)
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

            try:
                log_content = log.read(tail)
            except Exception as exc:
                self.logger.error("Unable to read log", exc_info=exc)
                return jsonify(success=False, message=str(exc)), 500
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

        @self.blueprint.route("/jobs", methods=["GET"])
        @requires_auth
        def list_jobs():
            scheduled_json = []
            delayed_json = []

            for job in self.job_scheduler.jobs:
                scheduled_json.append({
                    "name": job.name,
                    "interval": job.interval,
                    "next_run": job.next_run
                })

            for id, job in self.job_manager.jobs.items():
                delayed_json.append({
                    "id": id,
                    "name": job.name,
                    "status": job.state.name,
                    "start_time": job.start_time,
                    "end_time": job.end_time
                })

            return jsonify(success=True, scheduled=scheduled_json, delayed=delayed_json), 200

        @self.blueprint.route("/jobs/force_run/<name>")
        @requires_auth
        def force_run_job(name: str):
            self.job_scheduler.force_run_job(name)
            return jsonify(success=True)
