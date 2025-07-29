"""
Formatter and verifier for backup filenames.
"""

import os

def verify_name(name: str) -> bool:
    return "$I" in name or "$D" in name

def parse(name: str, id: str, created_at: str, manual: bool) -> str:
    real_created_at = created_at
    if os.name == "nt":
        real_created_at = real_created_at.replace(":", "_")
    return name.replace("$I", id).replace("$D", real_created_at).replace("$M", "manual" if manual else "auto")
