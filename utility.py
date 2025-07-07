# TODO move a few other random util functions here

SIZE_UNITS = [
    "B", "KiB", "MiB", "GiB"
]

def humanread_file_size(size: float):
    i = 0
    while size > 1024:
        size /= 1024
        i += 1
    return f"{size} {SIZE_UNITS[i]}"
