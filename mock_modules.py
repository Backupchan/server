"""
Mock versions of existing modules, for testing the JSON API.
The Web UI isn't tested in this way because: browser

They're all in one files since they're small and don't do anything meaningful.
"""

import database
import file_manager
import uuid
import logging
import threading
from backupchan_server import models
from datetime import datetime

class MockDatabase(database.Database):
    def __init__(self):
        self.targets: list[models.BackupTarget] = []
        self.backups: list[models.Backup] = []
        self.lock = threading.RLock() # since validate_target uses it
        self.logger = logging.getLogger("mockdb")
    
    def reset(self):
        self.targets = []
        self.backups = []
        self.logger.info("Reset")

    def add_target(self, name: str, target_type: models.BackupType, recycle_criteria: models.BackupRecycleCriteria, recycle_value: int | None, recycle_action: models.BackupRecycleAction | None, location: str, name_template: str, deduplicate: bool, alias: str | None) -> str:
        self.validate_target(name, name_template, location, None, alias)
        target_id = str(uuid.uuid4())
        target = models.BackupTarget(target_id, name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate, alias)
        self.targets.append(target)
        self.logger.info("Add target: %s", target)
        return target_id

    def edit_target(
        self,
        id: str,
        name: str,
        recycle_criteria: models.BackupRecycleCriteria,
        recycle_value: int | None,
        recycle_action: models.BackupRecycleAction | None,
        location: str,
        name_template: str,
        deduplicate: bool,
        alias: str | None
    ):
        self.validate_target(name, name_template, location, id, alias)
        target = self.get_target(id)
        target.name = name
        target.recycle_criteria = recycle_criteria
        target.recycle_value = recycle_value
        target.recycle_action = recycle_action
        target.location = location
        target.name_template = name_template
        target.deduplicate = deduplicate
        target.alias = alias
        self.logger.info("Edit target {%s} to %s", id, target)
    
    def get_target(self, id: str) -> models.BackupTarget:
        for target in self.targets:
            if target.id == id or target.alias == id:
                return target
        return None
    
    def list_targets(self, _ = None) -> list[models.BackupTarget]:
        return self.targets
    
    def delete_target(self, id: str):
        for target in self.targets:
            if target.id == id:
                self.targets.remove(target)
                self.logger.info("Delete target {%s}", id)
    
    def count_targets(self) -> int:
        return len(self.targets)
    
    def delete_target_backups(self, id: str):
        for backup in self.backups:
            if backup.target_id == id:
                self.backups.remove(backup)
    
    def add_backup(self, target_id: str, manual: bool, created_at: datetime | None = None) -> str:
        if created_at is None:
            created_at = datetime.now()
        
        backup_id = str(uuid.uuid4())
        backup = models.Backup(backup_id, target_id, created_at, manual, False, 123456)
        self.backups.append(backup)
        self.logger.info("Add backup %s", backup)
        return backup_id

    def set_backup_filesize(self, backup_id: str, filesize: int):
        self.get_backup(backup_id).filesize = filesize
    
    def get_backup(self, id: str) -> None | models.Backup:
        for backup in self.backups:
            if backup.id == id:
                return backup
        return None
    
    def delete_backup(self, id: str):
        self.backups.remove(self.get_backup(id))
        self.logger.info("Delete backup {%s}", id)
    
    def recycle_backup(self, id: str, recycled: bool):
        self.get_backup(id).is_recycled = recycled
        self.logger.info("Recycle backup {%s} -> %s", id, recycled)
    
    def list_backups(self) -> list[models.Backup]:
        return self.backups
    
    def list_backups_target(self, target_id: str) -> list[models.Backup]:
        backups = []
        for backup in self.backups:
            if backup.target_id == target_id:
                backups.append(backup)
        return backups
    
    def list_recycled_backups(self) -> list[models.Backup]:
        backups = []
        for backup in self.backups:
            if backup.is_recycled:
                backups.append(backup)
        return backups
    
    def list_backups_target_is_recycled(self, target_id: str, is_recycled: bool) -> list[models.Backup]:
        backups = []
        for backup in self.backups:
            if backup.target_id == target_id and backup.is_recycled == is_recycled:
                backups.append(backup)
        return backups
    
    def count_backups(self) -> int:
        return len(self.backups)
    
    def count_recycled_backups(self) -> int:
        return len(self.list_recycled_backups())
    
    def __del__(self):
        pass # Override because this does not initialize a real db connection.

class MockFileManager(file_manager.FileManager):
    def __init__(self, db: MockDatabase):
        self.db = db
        self.logger = logging.getLogger("mockfm")
    
    def add_backup(self, backup_id: str, filename: str):
        backup = self.db.get_backup(backup_id)
        if backup is None:
            raise file_manager.FileManagerError(f"Backup {backup_id} does not exist")

        target = self.db.get_target(backup.target_id)
        if target is None:
            return file_manager.FileManagerError(f"Backup {backup_id} points to nonexistent target")
        
        self.logger.info("Upload %s to backup {%s}", filename, backup_id)
    
    def delete_backup(self, backup_id: str):
        backup = self.db.get_backup(backup_id)
        if backup is None:
            raise file_manager.FileManagerError(f"Backup {backup_id} does not exist")

        target = self.db.get_target(backup.target_id)
        if target is None:
            return file_manager.FileManagerError(f"Backup {backup_id} points to nonexistent target")
        
        self.logger.info("Delete backup {%s}", backup_id)
    
    def delete_target_backups(self, target_id: str):
        target = self.db.get_target(target_id)
        if target is None:
            raise file_manager.FileManagerError(f"Target {target_id} does not exist")
        
        self.logger.info("Delete all backups for target {%s}", target_id)
    
    def update_backup_locations(self, target: models.BackupTarget, new_name_template: str, new_location: str, old_name_template: str, old_location: str):
        self.logger.info("Move target {%s} backups. Location '%s' -> '%s'; name template '%s' -> '%s'", target.id, old_location, new_location, old_name_template, new_name_template)
        self.db.validate_target(target.name, new_name_template, new_location, target.id, target.alias)
    
    def recycle_backup(self, backup_id: int):
        backup = self.db.get_backup(backup_id)
        if backup is None:
            raise file_manager.FileManagerError(f"Backup {backup_id} does not exist")

        target = self.db.get_target(backup.target_id)
        if target is None:
            raise file_manager.FileManagerError(f"Backup {backup_id} points to nonexistent target")
        
        self.logger.info("Recycle backup {%s}", backup_id)
    
    def unrecycle_backup(self, backup_id: int):
        backup = self.db.get_backup(backup_id)
        if backup is None:
            raise file_manager.FileManagerError(f"Backup {backup_id} does not exist")

        target = self.db.get_target(backup.target_id)
        if target is None:
            raise file_manager.FileManagerError(f"Backup {backup_id} points to nonexistent target")
        
        self.logger.info("Unrecycle backup {%s}", backup_id)
    
    def get_backup_size(self, backup_id: str) -> int:
        backup = self.db.get_backup(backup_id)
        if backup is None:
            raise file_manager.FileManagerError(f"Backup {backup_id} does not exist")

        target = self.db.get_target(backup.target_id)
        if target is None:
            raise file_manager.FileManagerError(f"Backup {backup_id} points to nonexistent target")

        return 123456
    
    def get_target_size(self, target_id: str) -> int:
        target = self.db.get_target(target_id)
        if target is None:
            raise file_manager.FileManagerError(f"Target {target_id} does not exist")
        
        return 123456
    
    def get_backup_list_size(self, backups: list[models.Backup]) -> int:
        return 123456
