from web.context import WebContext
from web.routes import misc, target, backup

def add_routes(context: WebContext):
    misc.add_routes(context)
    target.add_routes(context)
    backup.add_routes(context)
