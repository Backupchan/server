"""
Module for accessing the database in an easy way.
"""

import mariadb
import models
import uuid
import logging
import nameformat
import platform
import re
import unicodedata
import threading
from datetime import datetime
from pathlib import Path

class DatabaseError(Exception):
    pass

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
        # Allow colon only as part of drive letter (like C:/ or D:\)
        # Came up when I was testing on Windows.
        drive, rest = os.path.splitdrive(path)
        return not re.search(r'[<>:"|?*]', rest)

    # Regardless of system, disallow non-printable characters for sanity.
    return is_printable_string(path) and slash_ok or (not slash_ok and "/" not in path)

class Database:
    """
    This class handles the communication with the database.
    It does not perform any actual file operations on backups.
    """
    def __init__(self, db_path: str, connection_config: dict):
        if connection_config == {}:
            raise DatabaseError("Database connection not configured")

        self.connection = mariadb.connect(user=connection_config["user"], password=connection_config["password"], host=connection_config["host"], port=connection_config["port"], database=connection_config["database"])
        self.cursor = self.connection.cursor()
        self.lock = threading.RLock()
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
        name_template: str,
        deduplicate: bool
    ) -> str:
        with self.lock:
            self.validate_target(name, name_template, location, None)

            target_id = str(uuid.uuid4())
            self.cursor.execute("INSERT INTO targets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (target_id, name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate))
            self.connection.commit()

            self.logger.info("Add target {%s} name: %s type: %s criteria: %s value: %s action: %s location: %s template: %s dedup: %s", target_id, name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate)
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
        deduplicate: bool
    ):
        with self.lock:
            self.validate_target(name, name_template, location, id)

            self.cursor.execute("UPDATE targets SET name = ?, recycle_criteria = ?, recycle_value = ?, recycle_action = ?, location = ?, name_template = ?, deduplicate = ? WHERE id = ?", (name, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate, id))
            self.connection.commit()

            self.logger.info("Update target {%s} name: %s criteria: %s value: %s action: %s location: %s template: %s dedup: %s", id, name, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate)

    def list_targets(self) -> list[models.BackupTarget]:
        # TODO add some way to do pagination
        with self.lock:
            self.cursor.execute("SELECT * FROM targets")
            rows = self.cursor.fetchall()
            return [models.BackupTarget(*row) for row in rows]
    
    def get_target(self, id: str) -> None | models.BackupTarget:
        """
        Returns None if the target wasn't found.
        """
        with self.lock:
            self.cursor.execute("SELECT * FROM targets WHERE id = ?", (id,)) # stupid tuple
            row = self.cursor.fetchone()
            return None if row is None else models.BackupTarget(*row)

    def delete_target(self, id: str):
        with self.lock:
            self.cursor.execute("DELETE FROM targets WHERE id = ?", (id,))
            self.connection.commit()
            self.logger.info("Delete target {%s}", id)

    def count_targets(self) -> int:
        with self.lock:
            self.cursor.execute("SELECT COUNT(*) FROM targets")
            return self.cursor.fetchone()[0]

    def delete_target_backups(self, id: str):
        with self.lock:
            self.cursor.execute("DELETE FROM backups WHERE target_id = ?", (id,))
            self.connection.commit()
            self.logger.info("Delete target backups {%s}")

    #
    # Backup methods
    #

    def add_backup(self, target_id: str, manual: bool, created_at: datetime | None = None) -> str:
        if created_at is None:
            created_at = datetime.now()
        
        with self.lock:
            # Target ID must already exist.
            self.cursor.execute("SELECT id FROM targets WHERE id = ?", (target_id,))
            if self.cursor.fetchone() is None:
                raise DatabaseError(f"Target with id '{target_id}' does not exist")

            backup_id = str(uuid.uuid4())
            self.cursor.execute("INSERT INTO backups VALUES (?, ?, ?, ?, ?, ?)", (backup_id, target_id, created_at, manual, False, 0))
            self.connection.commit()

            self.logger.info("Add backup for target {%s} created at: %s, manual: %s", target_id, str(created_at), str(manual))
            return backup_id

    def set_backup_filesize(self, backup_id: str, filesize: int):
        with self.lock:
            self.cursor.execute("UPDATE backups SET filesize = ? WHERE id = ?", (filesize, backup_id))
            self.connection.commit()

    def get_backup(self, id: str) -> None | models.Backup:
        """
        Returns None if the backups wasn't found.
        """
        with self.lock:
            self.cursor.execute("SELECT * FROM backups WHERE id = ?", (id,))
            row = self.cursor.fetchone()
            if row is None:
                return None
            return models.Backup(*row)

    def delete_backup(self, id: str):
        with self.lock:
            self.cursor.execute("DELETE from backups WHERE id = ?", (id,))
            self.connection.commit()
            self.logger.info("Delete backup {%s}", id)

    def recycle_backup(self, id: str, recycled: bool):
        with self.lock:
            self.cursor.execute("UPDATE backups SET is_recycled = ? WHERE id = ?", (recycled, id))
            self.connection.commit()
            self.logger.info("Recycle backup {%s} to %s", id, recycled)

    def list_backups(self) -> list[models.Backup]:
        with self.lock:
            self.cursor.execute("SELECT * FROM backups")
            rows = self.cursor.fetchall()
            return [models.Backup(*row) for row in rows]

    def list_backups_target(self, target_id: str) -> list[models.Backup]:
        with self.lock:
            self.cursor.execute("SELECT * FROM backups WHERE target_id = ?", (target_id,))
            rows = self.cursor.fetchall()
            return [models.Backup(*row) for row in rows]

    def list_recycled_backups(self) -> list[models.Backup]:
        with self.lock:
            self.cursor.execute("SELECT * FROM backups WHERE is_recycled = TRUE")
            rows = self.cursor.fetchall()
            return [models.Backup(*row) for row in rows]

    def list_backups_target_is_recycled(self, target_id: str, is_recycled: bool) -> list[models.Backup]:
        with self.lock:
            self.cursor.execute("SELECT * FROM backups WHERE target_id = ? AND is_recycled = ?", (target_id, is_recycled))
            rows = self.cursor.fetchall()
            return [models.Backup(*row) for row in rows]

    def count_backups(self) -> int:
        with self.lock:
            self.cursor.execute("SELECT COUNT(*) FROM backups")
            return self.cursor.fetchone()[0]

    def count_recycled_backups(self) -> int:
        with self.lock:
            self.cursor.execute("SELECT COUNT(*) FROM backups WHERE is_recycled = TRUE")
            return self.cursor.fetchone()[0]

    #
    # Miscellaneous
    #

    def validate_target(self, name: str, name_template: str, location: str, target_id: str | None):
        with self.lock:
            # The name must not be empty.
            if len(name) == 0:
                raise DatabaseError("Name of new target must not be empty")

            # Name template must contain either ID of backup or its creation date.
            if not nameformat.verify_name(name_template):
                raise DatabaseError("Filename template must contain either creation date or ID of backup")

            # Name template must be unique to this target if it shares location with another target.
            for target in self.list_targets():
                if target.name_template == name_template and target.id != target_id:
                    raise DatabaseError("Name template is not unique to this target")

            # Name template must not contain illegal characters (like '?' on Windows, or '/' on everything else).
            if not is_valid_path(name_template, False):
                raise DatabaseError("Filename template must not contain invalid characters")

            # Location must not contain illegal characters. '/' is okay.
            if not is_valid_path(location, True):
                raise DatabaseError("Target location must not contain invalid characters")

    def initialize_database(self):
        migrations_dir = Path("migrations")
        sql_files = sorted(migrations_dir.glob("*.sql"))

        for sql_file in sql_files:
            with open(sql_file, "r", encoding="utf-8") as f:
                sql = f.read()
                self.run_migration(sql_file.name, sql)

    def run_migration(self, name: str, commands: str):
        self.logger.info("Running migration: %s", name)
        for command in commands.split(";"):
            if command.strip():
                self.logger.info("Run statement: %s", command)
                self.cursor.execute(command)
        self.connection.commit()


    def __del__(self):
        self.cursor.close()
        self.connection.close()
