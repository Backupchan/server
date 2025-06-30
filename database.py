"""
Module for accessing the database in an easy way.
"""

import sqlite3
import models
import uuid
import logging
import nameformat
import platform
import re
import unicodedata
from datetime import datetime

class DatabaseError(Exception):
    pass

def backups_from_rows(rows: list[tuple]) -> list[models.Backup]:
    # Can't use a comprehension because the created_at field is stored as a string,
    # but the model uses a datetime.
    backups = []
    for row in rows:
        created_at = datetime.fromisoformat(row[2])
        backups.append(models.Backup(row[0], row[1], created_at, row[3]))
    return backups

# TODO might be worth separating the two below functions to a separate module

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
        return not re.search(r'[<>:"|?*]', path)

    # Regardless of system, disallow non-printable characters for sanity.
    return is_printable_string(path) and slash_ok or (not slash_ok and "/" not in path)

class Database:
    """
    This class handles the communication with the database.
    It does not perform any actual file operations on backups.
    """
    def __init__(self, db_path: str):
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.logger = logging.getLogger(__name__)

    #
    # Target methods
    #

    def add_target(
        self,
        name: str,
        target_type: models.BackupType,
        recycle_criteria: models.BackupRecycleCriteria,
        recycle_value: int | None,
        recycle_action: models.BackupRecycleAction | None,
        location: str,
        name_template: str
    ):
        self.validate_target(name, name_template, location, None)

        target_id = str(uuid.uuid4())
        self.cursor.execute("INSERT INTO targets VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (target_id, name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template))
        self.connection.commit()

        self.logger.info("Add target {%s} name: %s type: %s criteria: %s value: %s action: %s location: %s template: %s", target_id, name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template)

    def edit_target(
        self,
        id: str,
        name: str,
        target_type: models.BackupType,
        recycle_criteria: models.BackupRecycleCriteria,
        recycle_value: int | None,
        recycle_action: models.BackupRecycleAction | None,
        location: str,
        name_template: str
    ):
        self.validate_target(name, name_template, location, id)

        self.cursor.execute("UPDATE targets SET name = ?, type = ?, recycle_criteria = ?, recycle_value = ?, recycle_action = ?, location = ?, name_template = ? WHERE id = ?", (name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template, id))
        self.connection.commit()

        self.logger.info("Update target {%s} name: %s type: %s criteria: %s value: %s action: %s location: %s template: %s", id, name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template)

    def list_targets(self) -> list[models.BackupTarget]:
        # TODO add some way to do pagination
        self.cursor.execute("SELECT * FROM targets")
        rows = self.cursor.fetchall()
        return [models.BackupTarget(*row) for row in rows]
    
    def get_target(self, id: str) -> None | models.BackupTarget:
        """
        Returns None if the target wasn't found.
        """
        self.cursor.execute("SELECT * FROM targets WHERE id = ?", (id,)) # stupid tuple
        row = self.cursor.fetchone()
        return None if row is None else models.BackupTarget(*row)

    def delete_target(self, id: str):
        self.cursor.execute("DELETE FROM targets WHERE id = ?", (id,))
        self.connection.commit()
        self.logger.info("Delete target {%s}", id)

    def count_targets(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM targets")
        return self.cursor.fetchone()[0]

    def delete_target_backups(self, id: str):
        self.cursor.execute("DELETE FROM backups WHERE target_id = ?", (id,))
        self.connection.commit()
        self.logger.info("Delete target backups {%s}")

    #
    # Backup methods
    #

    def add_backup(self, target_id: str, created_at: datetime, manual: bool) -> str:
        # Target ID must already exist.
        self.cursor.execute("SELECT id FROM targets WHERE id = ?", (target_id,))
        if self.cursor.fetchone() is None:
            raise DatabaseError(f"Target with id '{target_id}' does not exist")

        created_at_str = created_at.isoformat()
        backup_id = str(uuid.uuid4())
        self.cursor.execute("INSERT INTO backups (id, target_id, created_at, manual) VALUES (?, ?, ?, ?)", (backup_id, target_id, created_at_str, manual))
        self.connection.commit()

        self.logger.info("Add backup for target {%s} created at: %s, manual: %s", target_id, str(created_at), str(manual))
        return backup_id

    def get_backup(self, id: str) -> None | models.Backup:
        """
        Returns None if the backups wasn't found.
        """
        self.cursor.execute("SELECT * FROM backups WHERE id = ?", (id,))
        row = self.cursor.fetchone()
        if row is None:
            return None
        return models.Backup(row[0], row[1], datetime.fromisoformat(row[2]), row[3])

    def delete_backup(self, id: str):
        self.cursor.execute("DELETE from backups WHERE id = ?", (id,))
        self.connection.commit()
        self.logger.info("Delete backup {%s}", id)

    def list_backups(self) -> list[models.Backup]:
        self.cursor.execute("SELECT * FROM backups")
        return backups_from_rows(self.cursor.fetchall())

    def list_backups_target(self, target_id: str) -> list[models.Backup]:
        self.cursor.execute("SELECT * FROM backups WHERE target_id = ?", (target_id,))
        return backups_from_rows(self.cursor.fetchall())

    def count_backups(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM backups")
        return self.cursor.fetchone()[0]

    #
    # Miscellaneous
    #

    def validate_target(self, name: str, name_template: str, location: str, target_id: str | None):
        # The name must not be empty.
        if len(name) == 0:
            raise DatabaseError("Name of new target must not be empty")

        # Name template must contain either ID of backup or its creation date.
        if not nameformat.verify_name(name_template):
            raise DatabaseError("Filename template must contain either creation date or ID of backup")

        # Name template must be unique to this target if it shares location with another target.
        for target in self.list_targets():
            if target.location == location and target.name_template == name_template and target.id != target_id:
                raise DatabaseError("New target location collides with another target")

        # Name template must not contain illegal characters (like '?' on Windows, or '/' on everything else).
        if not is_valid_path(name_template, False):
            raise DatabaseError("Filename template must not contain invalid characters")

        # Location must not contain illegal characters. '/' is okay.
        if not is_valid_path(location, True):
            raise DatabaseError("Target location must not contain invalid characters")

    def __del__(self):
        self.connection.close()
