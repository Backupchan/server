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
