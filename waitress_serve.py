#!/usr/bin/python3
"""
Serve Backup-chan using waitress
"""

from waitress import serve
from main import app

# change these depending on your setup
serve(app, host='0.0.0.0', port=42069, max_request_body_size=1024 ** 3 * 10)
