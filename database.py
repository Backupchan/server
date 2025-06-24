"""
Module for accessing the database in an easy way.
"""

import sqlite3
import models
import uuid
import nameformat
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

class Database:
    """
    This class handles the communication with the database.
    It does not perform any actual file operations on backups.
    """
    def __init__(self, db_path: str):
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.connection.cursor()

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
        name_template: str):
        # The name must not be empty.
        if len(name) == 0:
            raise DatabaseError("Name of new target must not be empty")

        # Name template must contain either ID of backup or its creation date.
        if not nameformat.verify_name(name_template):
            raise DatabaseError("Filename template must contain either creation date or ID of backup")

        # Name template must be unique to this target.
        # TODO

        # Name template must not contain illegal characters (like '?' on Windows, or '/' on everything else).
        # TODO this is os-based

        # Location must not contain illegal characters. '/' is okay.
        # TODO

        target_id = str(uuid.uuid4())
        self.cursor.execute("INSERT INTO targets VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (target_id, name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template))
        self.connection.commit()

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

    def count_targets(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM targets")
        return self.cursor.fetchone()[0]

    #
    # Backup methods
    #

    def add_backup(self, target_id: str, created_at: datetime, manual: bool):
        # Target ID must already exist.
        self.cursor.execute("SELECT id FROM targets WHERE id = ", (target_id,))
        if self.cursor.fetchone() is None:
            raise DatabaseError(f"Target with id '{target_id}' does not exist")

        created_at_str = created_at.isoformat()
        backup_id = str(uuid.uuid4())
        self.cursor.execute("INSERT INTO backups (id, target_id, created_at, manual) VALUES (?, ?, ?, ?)", (backup_id, target_id, created_at_str, manual))

    def delete_backup(self, id: str):
        self.cursor.execute("DELETE from backups WHERE id = ?", (id,))

    def list_backups(self) -> list[models.Backup]:
        self.cursor.execute("SELECT * FROM backups")
        return backups_from_rows(self.cursor.fetchall())

    def list_backups_target(self, target_id: str) -> list[models.Backup]:
        self.cursor.execute("SELECT * FROM backups WHERE target_id = ?", (target_id,))
        return backups_from_rows(self.cursor.fetchall())

    def count_backups(self) -> int:
        self.cursor.execute("SELECT COUNT(*) FROM backups")
        return self.cursor.fetchone()[0]

    def __del__(self):
        self.connection.close()
