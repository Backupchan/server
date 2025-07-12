import database
import nameformat
import models
import os
import logging
import shutil
import zipfile
import tarfile
import threading
from pathlib import Path

class FileManagerError(Exception):
    pass

ZIP_SUFFIXES = [".zip"]
TAR_SUFFIXES = [".tar"]
TAR_GZ_SUFFIXES = [".tar", ".gz"]
TAR_XZ_SUFFIXES = [".tar", ".xz"]

VALID_ARCHIVE_SUFFIXES = [
    ZIP_SUFFIXES,
    TAR_SUFFIXES,
    TAR_GZ_SUFFIXES,
    TAR_XZ_SUFFIXES
]

def is_archive_filename(filename: str) -> bool:
    suffixes = Path(filename).suffixes
    return suffixes in VALID_ARCHIVE_SUFFIXES

def extract_archive(fs_location: str, filename: str):
    suffixes = Path(filename).suffixes
    if suffixes == ZIP_SUFFIXES:
        with zipfile.ZipFile(filename, "r") as zip_file:
            zip_file.extractall(fs_location)
        return
    elif suffixes == TAR_SUFFIXES or suffixes == TAR_GZ_SUFFIXES or suffixes == TAR_XZ_SUFFIXES:
        with tarfile.TarFile(filename, "r:*") as tar_file:
            tar_file.extractall(fs_location)
        return
    raise FileManagerError("Unsupported archive format")

def get_fs_location(location: str, name_template: str, backup_id: str, backup_creation_str: str) -> str:
    return os.path.join(location, nameformat.parse(name_template, backup_id, backup_creation_str))

def get_backup_fs_location(backup: models.Backup, target: models.BackupTarget, recycle_bin_path: str) -> str:
    if backup.is_recycled:
        return get_fs_location(recycle_bin_path, target.name_template, backup.id, backup.created_at.isoformat())
    return get_fs_location(target.location, target.name_template, backup.id, backup.created_at.isoformat())

def find_single_backup_file(base_path: str) -> str | None:
    base = Path(base_path)
    parent = base.parent
    stem = base.name

    for file in parent.iterdir():
        if file.is_file() and file.stem == stem:
            return file
    return None

def get_directory_size(path: Path)-> int:
    total = 0
    for dirpath, _, filenames in os.walk(path):
        for filename in filenames:
            filepath = Path(dirpath) / filename
            if filepath.is_file():
                total += filepath.stat().st_size
    return total

class FileManager:
    def __init__(self, db: database.Database, recycle_bin_path: str):
        self.db = db
        self.recycle_bin_path = recycle_bin_path
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)

    def add_backup(self, backup_id: str, filename: str):
        with self.lock:
            self.logger.info("Start add backup operation. Backup id: {%s} filename: %s", backup_id, filename)

            #
            # Checks
            #

            backup, target = self.get_backup_and_target(backup_id)

            fs_location = get_backup_fs_location(backup, target, self.recycle_bin_path)

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
            else:
                # pull up the extremely convenient archive extractor(tm)
                extract_archive(fs_location, filename)

            self.logger.info("Finish upload")

    def delete_backup(self, backup_id: str):
        with self.lock:
            backup, target = self.get_backup_and_target(backup_id)

            self.logger.info("Deleting backup {%s}", backup_id)

            fs_location = get_backup_fs_location(backup, target, self.recycle_bin_path)
            if target.target_type == models.BackupType.SINGLE:
                base_location = self.recycle_bin_path if backup.is_recycled else target.location
                for path in Path(base_location).glob(nameformat.parse(target.name_template, backup.id, backup.created_at.isoformat())):
                    path.unlink()
            else:
                shutil.rmtree(fs_location)

    def delete_target_backups(self, target_id: str):
        with self.lock:
            target = self.get_target(target_id)

            self.logger.info("Deleting all backups for target {%s}", target_id)
            backups = self.db.list_backups_target(target_id)
            for backup in backups:
                self.delete_backup(backup.id)

    def update_backup_locations(self, target: models.BackupTarget, new_name_template: str, new_location: str, old_name_template: str, old_location: str):
        with self.lock:
            self.logger.info("Starting move backups in target {%s}. Name template: '%s' -> '%s', location: '%s' -> '%s'", target.id, old_name_template, new_name_template, old_location, new_location)
            self.db.validate_target(target.name, new_name_template, new_location, target.id)

            os.makedirs(new_location, exist_ok=True)

            for backup in self.db.list_backups_target(target.id):
                old_fs_location = get_fs_location(old_location, old_name_template, backup.id, backup.created_at.isoformat())
                new_fs_location = get_fs_location(new_location, new_name_template, backup.id, backup.created_at.isoformat())

                if backup.is_recycled:
                    # In this case, it only matters if the name template changed.
                    old_fs_location = get_fs_location(self.recycle_bin_path, old_name_template, backup.id, backup.created_at.isoformat())
                    new_fs_location = get_fs_location(self.recycle_bin_path, new_name_template, backup.id, backup.created_at.isoformat())

                if target.target_type == models.BackupType.SINGLE:
                    old_fs_location = find_single_backup_file(old_fs_location)
                    if old_fs_location is None:
                        raise FileManagerError(f"Could not find backup file for backup {backup.id}")
                    new_fs_location += "".join(Path(old_fs_location).suffixes)

                self.logger.info("Move %s -> %s", old_fs_location, new_fs_location)

                shutil.move(old_fs_location, new_fs_location)

            self.logger.info("Finished moving")

    def recycle_backup(self, backup_id: int):
        with self.lock:
            backup, target = self.get_backup_and_target(backup_id)

            self.logger.info("Recycle backup {%s}", backup_id)
            self.recycle_bin_mkdir()

            # Doing this manually since the backup might be marked as recycled or not. This module shouldn't care.
            backup_location = get_fs_location(target.location, target.name_template, backup_id, backup.created_at.isoformat())
            recycle_location = get_fs_location(self.recycle_bin_path, target.name_template, backup_id, backup.created_at.isoformat())

            if target.target_type == models.BackupType.SINGLE:
                backup_location = find_single_backup_file(backup_location)
                if backup_location is None:
                    raise FileManagerError(f"Could not find backup file for backup {backup_id}")
                recycle_location += "".join(Path(backup_location).suffixes)

            self.logger.info("Move %s -> %s", backup_location, recycle_location)

            shutil.move(backup_location, recycle_location)

            self.logger.info("Finished recycling")

    def unrecycle_backup(self, backup_id: models.Backup):
        with self.lock:
            backup, target = self.get_backup_and_target(backup_id)

            self.logger.info("Unrecycle backup {%s}", backup_id)

            backup_location = get_fs_location(self.recycle_bin_path, target.name_template, backup_id, backup.created_at.isoformat())
            original_location = get_fs_location(target.location, target.name_template, backup_id, backup.created_at.isoformat())

            if target.target_type == models.BackupType.SINGLE:
                backup_location = find_single_backup_file(backup_location)
                if backup_location is None:
                    raise FileManagerError(f"Could not find backup file for backup {backup_id}")
                original_location += "".join(Path(backup_location).suffixes)

            self.logger.info("Move %s -> %s", backup_location, original_location)

            shutil.move(backup_location, original_location)

            self.logger.info("Finished unrecycling")

    def recycle_bin_mkdir(self):
        with self.lock:
            os.makedirs(self.recycle_bin_path, exist_ok=True)

    #
    # Statistics
    # They return the value in bytes.
    #

    def get_backup_size(self, backup_id: str) -> int:
        backup, target = self.get_backup_and_target(backup_id)

        fs_location = get_backup_fs_location(backup, target, self.recycle_bin_path)

        if target.target_type == models.BackupType.SINGLE:
            fs_location = find_single_backup_file(fs_location)
            if fs_location is None:
                raise FileManagerError(f"Could not find backup file for backup {backup_id}")
            return Path(fs_location).stat().st_size

        if not os.path.exists(fs_location):
            raise FileManagerError(f"Backup {backup_id} does not exist on-disk")

        return get_directory_size(Path(fs_location))

    def get_target_size(self, target_id: str) -> int:
        target = self.get_target(target_id)

        backups = self.db.list_backups_target(target_id)
        return self.get_backup_list_size(backups)

    def get_backup_list_size(self, backups: list[models.Backup]) -> int:
        total = 0
        for backup in backups:
            total += self.get_backup_size(backup.id)
        return total

    #
    # These allow accessing things from the database while making sure nothing's broken
    #
    
    def get_backup_and_target(self, backup_id: str) -> tuple[models.Backup, models.BackupTarget]:
        backup = self.db.get_backup(backup_id)
        if backup is None:
            raise FileManagerError(f"Backup {backup_id} does not exist")

        target = self.db.get_target(backup.target_id)
        if target is None:
            raise FileManagerError(f"Backup {backup_id} points to nonexistent target")
        
        return backup, target
    
    def get_target(self, target_id: str) -> models.BackupTarget:
        target = self.db.get_target(target_id)
        if target is None:
            raise FileManagerError(f"Target {target_id} does not exists")
        return target