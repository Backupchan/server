"""
Formatter and verifier for backup filenames.
"""

def verify_name(name: str) -> bool:
    return "$I" in name or "$D" in name

def parse(name: str, id: str, created_at: str) -> str:
    return name.replace("$I", id).replace("$D", created_at)
