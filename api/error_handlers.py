from api.context import APIContext
from flask import jsonify

def add_error_handlers(context: APIContext):
    @context.blueprint.errorhandler(500)
    def handle_500(error):
        return jsonify(success=False, message=f"{error}. Check log for more details."), 500
