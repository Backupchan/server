import dataclasses
import logging
import os
import seq_upload
import api.utility as apiutil
from backupchan_server import models, utility
from api.context import APIContext
from flask import jsonify, request, Response

def check_seq_upload(seq_upload_manager: seq_upload.SequentialUploadManager, target: None | models.BackupTarget) -> None | tuple[Response, int]:
    if target is None:
        return jsonify(success=False), 404

    if not seq_upload_manager.is_processing(target.id):
        return jsonify(success=False), 400

    return None

def add_routes(context: APIContext):
    logger = logging.getLogger("apisequpload")

    @context.blueprint.route("/seq/<target_id>/begin", methods=["POST"])
    @context.auth.requires_auth
    def seq_begin(target_id: str):
        target = context.db.get_target(target_id)
        if target is None:
            return jsonify(success=False), 404

        if target.target_type != models.BackupType.MULTI:
            return jsonify(success=False, message="Cannot begin sequential upload on single-file target"), 400

        # Verify that the user passed required data
        data = request.get_json()
        verify_result = apiutil.verify_data_present(data, ["file_list", "manual"])
        if verify_result is not None:
            return verify_result

        file_list = seq_upload.SequentialFile.list_from_dicts(data["file_list"])

        create_upload_status = context.seq_upload_manager.create_upload(target.id, file_list, data["manual"])
        if create_upload_status == seq_upload.SequentialUploadCreateStatus.VALIDATION_FAILED:
            return jsonify(success=False, message="File list validation failed"), 400
        if create_upload_status == seq_upload.SequentialUploadCreateStatus.TARGET_BUSY:
            return jsonify(success=False, message="Target busy"), 400
        
        return jsonify(success=True), 200

    @context.blueprint.route("/seq/<target_id>", methods=["GET"])
    @context.auth.requires_auth
    def seq_check(target_id: str):
        target = context.db.get_target(target_id)
        if target is None:
            return jsonify(success=False), 404
        
        if not context.seq_upload_manager.is_processing(target.id):
            return jsonify(success=False), 400

        upload = context.seq_upload_manager[target.id]
        return jsonify(success=True, file_list=[dataclasses.asdict(file) for file in upload.file_list])

    @context.blueprint.route("/seq/<target_id>/upload", methods=["POST"])
    @context.auth.requires_auth
    def seq_upload_file(target_id: str):
        target = context.db.get_target(target_id)
        verify_result = context.check_seq_upload(target)
        if verify_result is not None:
            return verify_result

        # Verify that user supplied file name and path
        data = request.form
        verify_result = verify_data_present(data, ["name", "path"])
        if verify_result is not None:
            return verify_result

        sequential_file = seq_upload.SequentialFile(data["path"], data["name"], False)

        # Verify that we don't already have that file
        if context.seq_upload_manager[target.id].is_uploaded(sequential_file):
            return jsonify(success=False), 409

        # Verify that it's in the list (and mark as uploaded if it is)
        if not context.seq_upload_manager[target.id].set_uploaded_state(sequential_file, True):
            return jsonify(success=False), 400

        # Verify that they gave a file
        if "file" not in request.files:
            return jsonify(success=False, message="No file given"), 400

        try:
            rel_path = sequential_file.full_path()
            if os.path.isabs(rel_path):
                rel_path = rel_path.lstrip("/")

            file = request.files["file"]
            filename = utility.join_path(context.config.get("temp_save_path"), f"seq_{target.id}", rel_path)
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            file.save(filename)
        except Exception as exc:
            logger.error("Error during sequential upload on target {%s}", target.id, exc_info=exc)
            context.seq_upload_manager[target.id].set_uploaded_state(sequential_file, False)
            return jsonify(success=False, message=str(exc)), 500

        logger.info("Uploaded file %s to sequential upload on target {%s}", sequential_file, target.id)
        return jsonify(success=True), 200

    @context.blueprint.route("/seq/<target_id>/finish", methods=["POST"])
    @context.auth.requires_auth
    def seq_finish(target_id: str):
        target = context.db.get_target(target_id)
        verify_result = context.check_seq_upload(target)
        if verify_result is not None:
            return verify_result

        if not context.seq_upload_manager[target.id].all_uploaded():
            return jsonify(success=False), 409

        source_path = utility.join_path(context.config.get("temp_save_path"), f"seq_{target.id}")
        backup_id = context.db.add_backup(target.id, context.seq_upload_manager[target.id].manual)
        try:
            context.fm.add_backup(backup_id, [source_path])
        except Exception as exc:
            context.db.delete_backup(backup_id)
            logger.error("Error when adding sequential backup files on target {%s}", target.id, exc_info=exc)
            return jsonify(success=False, message=str(exc)), 500

        context.db.set_backup_filesize(backup_id, context.fm.get_backup_size(backup_id))
        context.seq_upload_manager.finish(target.id)

        return jsonify(success=True), 200

    @context.blueprint.route("/seq/<target_id>/terminate", methods=["POST"])
    @context.auth.requires_auth
    def seq_terminate(target_id: str):
        target = context.db.get_target(target_id)
        verify_result = context.check_seq_upload(target)
        if verify_result is not None:
            return verify_result

        context.seq_upload_manager.delete(target.id)
        return jsonify(success=True), 200

