from web.context import WebContext
from flask import render_template

def add_error_handlers(context: WebContext):
    @context.blueprint.errorhandler(500)
    def handle_500(error):
        return render_template("error.html", message="500 Internal Server Error", error=error), 500
