# idk where else to put this so might as well be in its own file

import database
from flask import request

def parse_sort_options(kind: type[database.SortOptions]) -> database.SortOptions | None:
    column = request.args.get("s")
    if column is None:
        return None

    asc = request.args.get("a", "1") == "1"
    return kind(asc, column)
