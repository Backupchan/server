import time
import os
import logging
from enum import Enum
from dataclasses import dataclass
from backupchan_server import utility

TIMEOUT = 3600 # Inactivity timeout (1hr)

@dataclass
class SequentialFile:
    path: str
    name: str
    uploaded: bool

    def compare_full_path(self, other: "SequentialFile") -> bool:
        return self.path == other.path and self.name == other.name

    def full_path(self) -> str:
        return utility.join_path(self.path.rstrip("/"), self.name)

    @staticmethod
    def from_dict(d: dict) -> "SequentialFile":
        return SequentialFile(d["path"], d["name"], d.get("uploaded", False))

    @staticmethod
    def list_from_dicts(l: list[dict]) -> list["SequentialFile"]:
        file_list: list[SequentialFile] = []
        for d in l:
            file_list.append(SequentialFile.from_dict(d))
        return file_list

    def __str__(self) -> str:
        return f"SequentialFile({self.full_path()})"

def validate_file_list(file_list: list[SequentialFile]) -> bool:
    seen = set()
    for file in file_list:
        if not utility.is_valid_path(file.full_path(), True):
            return False
        key = (file.path, file.name)
        if key in seen:
            return False
        seen.add(key)
    return True

class SequentialUploadCreateStatus(Enum):
    OK = 0
    VALIDATION_FAILED = 1
    TARGET_BUSY = 2

class SequentialUpload:
    def __init__(self, target_id: str, file_list: list[SequentialFile], manual: bool):
        self.target_id = target_id
        self.file_list = file_list
        self.manual = manual
        self.last_activity = time.time()

    def set_uploaded_state(self, uploaded_file: SequentialFile, value: bool) -> bool:
        for file in self.file_list:
            if file.compare_full_path(uploaded_file):
                file.uploaded = value
                self.update_activity()
                return True
        return False

    def missing_files(self):
        return [file for file in self.file_list if not file.uploaded]
    
    def all_uploaded(self):
        return len(self.missing_files()) == 0

    def update_activity(self):
        self.last_activity = time.time()

    def expired(self):
        return time.time() - self.last_activity > TIMEOUT

    def is_uploaded(self, uploaded_file: SequentialFile) -> bool:
        for file in self.file_list:
            if file.compare_full_path(uploaded_file):
                return file.uploaded
        return False

    def __contains__(self, item: SequentialFile) -> bool:
        for file in self.file_list:
            if file.compare_full_path(item):
                return True
        return False

class SequentialUploadManager:
    def __init__(self):
        self.uploads: dict[str, SequentialUpload] = {}
        self.logger = logging.getLogger("seq_upload_manager")

    def create_upload(self, target_id: str, file_list: list[SequentialFile], manual: bool) -> SequentialUploadCreateStatus:
        if target_id in self.uploads:
            return SequentialUploadCreateStatus.TARGET_BUSY
        if not validate_file_list(file_list):
            return SequentialUploadCreateStatus.VALIDATION_FAILED
        self.uploads[target_id] = SequentialUpload(target_id, file_list, manual)
        self.logger.info("Created sequential upload for target {%s}", target_id)
        return SequentialUploadCreateStatus.OK

    def finish(self, target_id: str) -> bool:
        upload = self.uploads[target_id]
        if not upload.all_uploaded():
            return False
        del self.uploads[target_id]
        self.logger.info("Sequential upload for target {%s} finished", target_id)
        return True

    def delete(self, target_id: str):
        if target_id in self.uploads:
            self.logger.info("Delete sequential upload for target {%s}", target_id)
            del self.uploads[target_id]

    def is_processing(self, target_id: str) -> bool:
        return target_id in self.uploads

    def __getitem__(self, target_id: str) -> SequentialUpload:
        return self.uploads[target_id]

    def __iter__(self):
        return iter(self.uploads.copy().keys())
