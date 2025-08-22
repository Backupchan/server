import logging
import os
import sys

# TODO make configurable

LOG_DIRECTORY = os.path.join(".", "log")
LOG_FILE = os.path.join(LOG_DIRECTORY, "backupchan.log")

def init(): 
    if not os.path.isdir(LOG_DIRECTORY):
        os.mkdir(LOG_DIRECTORY)

    formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s")

    file_handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=2000000, backupCount=5)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

def read(tail: int):
    log_content = ""
    with open(LOG_FILE, "r") as log_file:
        if tail == 0:
            log_content = log_file.read()
        else:
            log_content = "".join(log_file.readlines()[-tail:])
    return log_content
