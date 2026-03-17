import logging
import uuid
import os
import delayed_jobs
import download
import api.utility as apiutil
from backupchan_server import utility
from api.context import APIContext
from flask import jsonify, request

def add_routes(context: APIContext):
    logger = logging.getLogger("apibackup")

    @context.blueprint.route("/target/<id>/upload", methods=["POST"])
    @context.auth.requires_auth
    def upload_backup(id):
        # Check if target exists
        target = context.db.get_target(id)
        if target is None:
            return jsonify(success=False), 404

        # Verify that user supplied data
        data = request.form
        verify_result = apiutil.verify_data_present(data, ["manual"])
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
            filename = utility.join_path(context.config.get("temp_save_path"), f"{uuid.uuid4().hex}_{file.filename}")
            os.makedirs(context.config.get("temp_save_path"), exist_ok=True)
            file.save(filename)
            filenames.append(filename)

        try:
            job_id = context.job_manager.run_job(delayed_jobs.UploadJob(target.id, is_manual, filenames, context.server_api))
        except Exception as exc:
            logger.error("Encountered error while uploading backup", exc_info=exc)
            return jsonify(success=False), 500

        return jsonify(success=True, job_id=job_id), 200

    @context.blueprint.route("/backup/<id>/download", methods=["GET"])
    @context.auth.requires_auth
    def download_backup(id):
        backup = context.db.get_backup(id)
        if backup is None:
            return jsonify(success=False), 404

        target = context.db.get_target(backup.target_id)
        if target is None:
            return jsonify(success=False), 404

        return send_file(download.get_download_path(backup, target, context.fm.recycle_bin_path, context.config.get("temp_save_path"), context.fm), as_attachment=True)

    @context.blueprint.route("/backup/<id>", methods=["DELETE"])
    @context.auth.requires_auth
    def delete_backup(id):
        backup = context.db.get_backup(id)
        if backup is None:
            return jsonify(success=False), 404

        data = request.get_json()
        verify_result = apiutil.verify_data_present(data, ["delete_files"])
        if verify_result is not None:
            return verify_result

        context.server_api.delete_backup(id, data["delete_files"])
        return jsonify(success=True), 200

    @context.blueprint.route("/backup/<id>", methods=["PATCH"])
    @context.auth.requires_auth
    def recycle_backup(id):
        backup = context.db.get_backup(id)
        if backup is None:
            return jsonify(success=False), 404

        data = request.get_json()
        verify_result = apiutil.verify_data_present(data, ["is_recycled"])
        if verify_result is not None:
            return verify_result

        if data["is_recycled"]:
            context.server_api.recycle_backup(id)
        else:
            context.server_api.unrecycle_backup(id)
        return jsonify(success=True), 200
