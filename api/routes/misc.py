import logging
import log
import api.utility as apiutil
from version import PROGRAM_VERSION
from api.context import APIContext
from flask import request, jsonify

def add_routes(context: APIContext):
    logger = logging.getLogger("apimisc")

    @context.blueprint.route("/recycle_bin", methods=["GET"])
    @context.auth.requires_auth
    def recycle_bin():
        recycle_bin = context.db.list_recycled_backups()
        return jsonify(success=True, backups=[backup.asdict() for backup in recycle_bin]), 200

    @context.blueprint.route("/recycle_bin", methods=["DELETE"])
    @context.auth.requires_auth
    def recycle_bin_clear():
        data = request.get_json()
        verify_result = apiutil.verify_data_present(data, ["delete_files"])
        if verify_result is not None:
            return verify_result

        context.server_api.recycle_bin_clear(data["delete_files"])
        return jsonify(success=True), 200

    @context.blueprint.route("/log", methods=["GET"])
    @context.auth.requires_auth
    def get_log():
        tail = 0
        if "tail" in request.args:
            tail = int(request.args["tail"])

        try:
            log_content = log.read(tail)
        except Exception as exc:
            logger.error("Unable to read log", exc_info=exc)
            return jsonify(success=False, message=str(exc)), 500
        return jsonify(success=True, log=log_content)

    @context.blueprint.route("/stats", methods=["GET"])
    @context.auth.requires_auth
    def view_stats():
        total_target_size = context.stats.total_target_size()
        total_recycle_bin_size = context.stats.total_recycle_bin_size()
        total_targets = context.db.count_targets()
        total_backups = context.db.count_backups()
        total_recycled_backups = context.db.count_recycled_backups()

        return jsonify(success=True,
                       program_version=PROGRAM_VERSION,
                       total_target_size=total_target_size,
                       total_recycle_bin_size=total_recycle_bin_size,
                       total_targets=total_targets,
                       total_backups=total_backups,
                       total_recycled_backups=total_recycled_backups
        )
