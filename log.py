import logging
import os
import sys
import re
from dataclasses import dataclass

# TODO make configurable

LOG_DIRECTORY = os.path.join(".", "log")
LOG_FILE = os.path.join(LOG_DIRECTORY, "backupchan.log")

@dataclass
class LogLine:
    time: str
    module: str
    level: str
    message: str

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

def parse(log: str) -> list[LogLine]:
    lines = log.split("\n")
    log_lines = []
    for line in lines:
        if not re.match(r"\[\d+-\d+-\d+ \d+:\d+:\d+,\d+\] \[[a-z_.]+\] \[[A-Z]+\]: .*", line):
            log_lines.append(LogLine("", "", "", line))
            continue
        print(line)
        message = re.search(r": .*", line).group(0)[2:]
        info_split = line.replace(message, "").split("] [")
        time = info_split[0][1:]
        module = info_split[1]
        level = info_split[2][:-3]
        log_lines.append(LogLine(time, module, level, message))
    return log_lines
