import os
import json
import logging
import functools
import api.utility as apiutil
from flask import request

class APIAuth:
    def __init__(self):
        self.logger = logging.getLogger("apiauth")
        self.key = None
        if os.path.exists("apikey.json"):
            self.load_api_key()

    def load_api_key(self):
        with open("apikey.json") as file:
            file_json = json.load(file)
            if "key" not in file_json:
                self.key = None
                self.logger.warning("API key file is incorrect. Authentication will be disabled.")
                return
            self.key = file_json["key"]

    def requires_auth(self, f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if self.key is None:
                return f(*args, **kwargs)

            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return apiutil.failure_response("Unauthorized"), 401

            token = auth_header.removeprefix("Bearer ").strip()
            if token != self.key:
                return apiutil.failure_response("Invalid API key"), 403

            return f(*args, **kwargs)
        return decorated
