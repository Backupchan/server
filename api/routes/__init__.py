from api.context import APIContext
from api.routes import target, backup, seq_upload, misc

def add_routes(context: APIContext):
    target.add_routes(context)
    backup.add_routes(context)
    seq_upload.add_routes(context)
    misc.add_routes(context)
