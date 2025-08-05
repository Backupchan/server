"""
Module for accessing the database in an easy way.
"""

import mariadb
import uuid
import logging
import platform
import re
import unicodedata
import threading
import os
from datetime import datetime
from pathlib import Path
from backupchan_server import models
from backupchan_server import nameformat
from backupchan_server import utility

class DatabaseError(Exception):
    pass

class Database:
    """
    This class handles the communication with the database.
    It does not perform any actual file operations on backups.
    """

    CURRENT_SCHEMA_VERSION = 9

    def __init__(self, connection_config: dict, page_size: int = 10):
        if connection_config == {}:
            raise DatabaseError("Database connection not configured")

        self.connection = mariadb.connect(user=connection_config["user"], password=connection_config["password"], host=connection_config["host"], port=connection_config["port"], database=connection_config["database"])
        self.cursor = self.connection.cursor()
        self.page_size = page_size
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)

    #
    # Schema version methods
    #

    def get_schema_version(self):
        self.cursor.execute("SELECT version FROM schema_versions ORDER BY version DESC LIMIT 1;")
        return self.cursor.fetchone()[0]

    def validate_schema_version(self):
        try:
            if self.get_schema_version() != Database.CURRENT_SCHEMA_VERSION:
                raise DatabaseError("Schema version mismatch, update Backup-chan.")
        except mariadb.ProgrammingError as exc:
            if "schema_versions' doesn't exist" in str(exc):
                raise DatabaseError("bro ur version so ancient you don't even have schema versions. update now")
            raise

    #
    # Target methods
    # ID parameter accepts alias as well.
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
        deduplicate: bool,
        alias: str | None
    ) -> str:
        with self.lock:
            self.validate_target(name, name_template, location, None, alias)

            target_id = str(uuid.uuid4())
            self.cursor.execute("INSERT INTO targets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (target_id, name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate, alias))
            self.connection.commit()

            self.logger.info("Add target {%s} name: %s type: %s criteria: %s value: %s action: %s location: %s template: %s dedup: %s alias: %s", target_id, name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate, alias)
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
        with self.lock:
            target = self.get_target(id)
            if target is None:
                raise DatabaseError(f"Target with id or alias {id} does not exist")

            target_id = target.id
            self.validate_target(name, name_template, location, target_id, alias)

            self.cursor.execute("UPDATE targets SET name = ?, recycle_criteria = ?, recycle_value = ?, recycle_action = ?, location = ?, name_template = ?, deduplicate = ?, alias = ? WHERE id = ? OR alias = ?", (name, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate, alias, id, id))
            self.connection.commit()

            self.logger.info("Update target {%s} name: %s criteria: %s value: %s action: %s location: %s template: %s dedup: %s alias: %s", target_id, name, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate, alias)

    def list_targets(self, page: int = 1) -> list[models.BackupTarget]:
        offset = (page - 1) * self.page_size
        with self.lock:
            self.cursor.execute("SELECT * FROM targets LIMIT ? OFFSET ?", (self.page_size, offset))
            rows = self.cursor.fetchall()
            return [models.BackupTarget(*row) for row in rows]

    def list_targets_all(self) -> list[models.BackupTarget]:
        self.cursor.execute("SELECT * FROM targets")
        rows = self.cursor.fetchall()
        return [models.BackupTarget(*row) for row in rows]
    
    def get_target(self, id: str) -> None | models.BackupTarget:
        """
        Returns None if the target wasn't found.
        """
        with self.lock:
            self.cursor.execute("SELECT * FROM targets WHERE id = ? OR alias = ?", (id, id))
            row = self.cursor.fetchone()
            return None if row is None else models.BackupTarget(*row)

    def get_target_size(self, id: str) -> int:
        with self.lock:
            self.cursor.execute("SELECT SUM(filesize) FROM backups WHERE target_id = ?", (id,))
            return self.cursor.fetchone()[0] or 0

    def delete_target(self, id: str):
        with self.lock:
            self.cursor.execute("DELETE FROM targets WHERE id = ? OR alias = ?", (id, id))
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
            target = self.get_target(target_id)
            if target is None:
                raise DatabaseError(f"Target with id or alias '{target_id}' does not exist")

            backup_id = str(uuid.uuid4())
            self.cursor.execute("INSERT INTO backups VALUES (?, ?, ?, ?, ?, ?)", (backup_id, target.id, created_at, manual, False, 0))
            self.connection.commit()

            self.logger.info("Add backup for target {%s} created at: %s, manual: %s", target.id, str(created_at), str(manual))
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
            target = self.get_target(target_id)
            if target is None:
                raise DatabaseError(f"Target with id or alias '{target_id}' does not exist")

            self.cursor.execute("SELECT * FROM backups WHERE target_id = ?", (target.id,))
            rows = self.cursor.fetchall()
            return [models.Backup(*row) for row in rows]

    def list_recycled_backups(self) -> list[models.Backup]:
        with self.lock:
            self.cursor.execute("SELECT * FROM backups WHERE is_recycled = TRUE")
            rows = self.cursor.fetchall()
            return [models.Backup(*row) for row in rows]

    def list_backups_target_is_recycled(self, target_id: str, is_recycled: bool) -> list[models.Backup]:
        with self.lock:
            target = self.get_target(target_id)
            if target is None:
                raise DatabaseError(f"Target with id or alias '{target_id}' does not exist")

            self.cursor.execute("SELECT * FROM backups WHERE (target_id = ?) AND is_recycled = ?", (target.id, is_recycled))
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

    def validate_target(self, name: str, name_template: str, location: str, target_id: str | None, alias: str | None):
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
            if not utility.is_valid_path(name_template, False):
                raise DatabaseError("Filename template must not contain invalid characters")

            # Location must not contain illegal characters. '/' is okay.
            if not utility.is_valid_path(location, True):
                raise DatabaseError("Target location must not contain invalid characters")
            
            # Alias must be unique to this target (if present).
            if alias is not None:
                for target in self.list_targets():
                    if target.alias == alias and target.id != target_id:
                        raise DatabaseError("Alias is not unique to this target")

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
