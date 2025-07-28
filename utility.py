import platform
import unicodedata
import os
import re

# TODO move a few other random util functions here

SIZE_UNITS = [
    "B", "KiB", "MiB", "GiB", "TiB"
]

def humanread_file_size(size: float):
    i = 0
    while size > 1024:
        size /= 1024
        i += 1
    return f"{size:.2f} {SIZE_UNITS[i]}"

def is_printable_string(s: str) -> bool:
    for char in s:
        category = unicodedata.category(char)
        if category.startswith("C"): # control chars start with c
            return False
    return True

def is_valid_path(path: str, slash_ok: bool) -> bool:
    if platform.system() == "Windows":
        if not slash_ok and ("/" in path or "\\" in path):
            return False
        # Allow colon only as part of drive letter (like C:/ or D:\)
        # Came up when I was testing on Windows.
        drive, rest = os.path.splitdrive(path)
        return not re.search(r'[<>:"|?*]', rest)

    # Regardless of system, disallow non-printable characters for sanity.
    return is_printable_string(path) and slash_ok or (not slash_ok and "/" not in path)
