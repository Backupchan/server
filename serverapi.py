import database
import file_manager
import datetime
import threading
import os
import uuid
from werkzeug.datastructures import FileStorage

class ServerAPI:
    """
    Class for doing actions which require both the database and file manager involved.
    """
    def __init__(self, db: database.Database, fm: file_manager.FileManager):
        self.db = db
        self.fm = fm
        self.lock = threading.RLock()

    def edit_target(self, target_id: str, new_name: str, new_recycle_criteria: str, new_recycle_value: int, new_recycle_action: str, new_location: str, new_name_template: str, deduplicate: bool, alias: str | None):
        with self.lock:
            target = self.db.get_target(target_id)
            old_location = target.location
            old_name_template = target.name_template
            self.db.edit_target(target_id, new_name, new_recycle_criteria, new_recycle_value, new_recycle_action, new_location, new_name_template, deduplicate, alias)
            if old_name_template != new_name_template or old_location != new_location:
                self.fm.update_backup_locations(target, new_name_template, new_location, old_name_template, old_location)

    def delete_target(self, target_id: str, delete_files: bool):
        with self.lock:
            if delete_files:
                self.fm.delete_target_backups(target_id)
            self.db.delete_target(target_id)

    def delete_target_backups(self, target_id: str, delete_files: bool):
        with self.lock:
            for backup in self.db.list_backups_target(target_id):
                self.delete_backup(backup.id, delete_files)

    def upload_backup(self, target_id: str, manual: bool, filename: str) -> str:
        backup_id = self.db.add_backup(target_id, manual)

        try:
            self.fm.add_backup(backup_id, filename)
        except Exception as exc:
            self.db.delete_backup(backup_id)
            raise

        self.db.set_backup_filesize(backup_id, self.fm.get_backup_size(backup_id))
        return backup_id

    def delete_backup(self, backup_id: str, delete_files: bool):
        with self.lock:
            if delete_files:
                self.fm.delete_backup(backup_id)
            self.db.delete_backup(backup_id)

    def recycle_backup(self, backup_id: str):
        with self.lock:
            self.fm.recycle_backup(backup_id)
            self.db.recycle_backup(backup_id, True)

    def unrecycle_backup(self, backup_id: str):
        with self.lock:
            self.fm.unrecycle_backup(backup_id)
            self.db.recycle_backup(backup_id, False)

    def recycle_bin_clear(self, delete_files: bool):
        with self.lock:
            recycled_backups = self.db.list_recycled_backups()
            for backup in recycled_backups:
                self.delete_backup(backup.id, delete_files)
