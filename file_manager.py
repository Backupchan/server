import database
import nameformat
import models
import os
import logging
import shutil
from pathlib import Path

class FileManagerError(Exception):
    pass

VALID_ARCHIVE_SUFFIXES = [
    [".zip"],
    [".tar"],
    [".tar", ".gz"],
    [".tar", ".xz"]
]

def is_archive_filename(filename: str) -> bool:
    suffixes = Path(filename).suffixes
    return suffixes in VALID_ARCHIVE_SUFFIXES

class FileManager:
    def __init__(self, db: database.Database):
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    def add_backup(self, backup_id: str, filename: str):
        self.logger.info("Start add backup operation. Backup id: {%s} filename: %s", backup_id, filename)

        #
        # Checks
        #

        backup = self.db.get_backup(backup_id)
        if backup is None:
            raise FileManagerError(f"Backup {backup_id} does not exist")

        target = self.db.get_target(backup.target_id)
        if target is None:
            return FileManagerError(f"Backup {backup_id} points to nonexistent target")

        fs_location = self.get_backup_fs_location(backup, target)

        # If it's single-file, append the extension as well.
        if target.target_type == models.BackupType.SINGLE:
            fs_location += Path(filename).suffix

        if os.path.exists(fs_location):
            return FileManagerError(f"Path {fs_location} already exists")

        self.logger.info("Will be put in %s", fs_location)

        # If it's multi-file, check the extension
        # TODO is it worth checking the file content to check if it's a real zip/tar/whatever and not an imposter?
        if target.target_type == models.BackupType.MULTI and not is_archive_filename(filename):
            return FileManagerError("Backup file is not a supported archive")

        #
        # Actual operation
        #

        self.logger.info("Checks passed. Now uploading")

        # Regardless of type, create the directory if it doesn't exist
        if target.target_type == models.BackupType.MULTI:
            os.makedirs(fs_location, exist_ok=True)
        else:
            os.makedirs(target.location, exist_ok=True)

        if target.target_type == models.BackupType.SINGLE:
            shutil.move(filename, fs_location)

        self.logger.info("Finish upload")

    def get_backup_fs_location(self, backup: models.Backup, target: models.BackupTarget) -> str:
        return os.path.join(target.location, nameformat.parse(target.name_template, backup.id, backup.created_at.isoformat()))
