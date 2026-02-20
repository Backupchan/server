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
import sys
from datetime import datetime
from pathlib import Path
from backupchan_server import models
from backupchan_server import nameformat
from backupchan_server import utility

class DatabaseError(Exception):
    pass

class SortOptions:
    def __init__(self, valid_columns: list[str], default_column: str, asc: bool, column: str | None):
        self.valid_columns = valid_columns
        if column is not None and column in valid_columns:
            self.column = column
        else:
            self.column = default_column

        self.asc = asc

    @classmethod
    def default(cls) -> "SortOptions":
        raise NotImplementedError

    def sql(self) -> str:
        return f"ORDER BY {self.column} {self.asc_str()}"

    def asc_str(self) -> str:
        return "ASC" if self.asc else "DESC"

class TargetSortOptions(SortOptions):
    def __init__(self, asc: bool, column: str | None):
        super().__init__(["id", "name", "type", "recycle_criteria", "recycle_value", "recycle_action", "location", "name_template", "deduplicate", "alias"], "name", asc, column)

    @classmethod
    def default(cls) -> "TargetSortOptions":
        return cls(True, "name")

class BackupSortOptions(SortOptions):
    def __init__(self, asc: bool, column: str | None):
        super().__init__(["id", "target_id", "created_at", "manual", "is_recycled", "filesize"], "created_at", asc, column)

    @classmethod
    def default(cls) -> "BackupSortOptions":
        return cls(False, "created_at")

class Database:
    """
    This class handles the communication with the database.
    It does not perform any actual file operations on backups.
    """

    CURRENT_SCHEMA_VERSION = 13

    def __init__(self, connection_config: dict, page_size: int = 10):
        if connection_config == {}:
            raise DatabaseError("Database connection not configured")

        self.logger = logging.getLogger(__name__)
        try:
            self.connection = mariadb.connect(user=connection_config["user"], password=connection_config["password"], host=connection_config["host"], port=connection_config["port"], database=connection_config["database"])
        except mariadb.OperationalError as exc:
            self.logger.error("Unable to establish a database connection. Make sure the database server is running and that your config is correct.", exc_info=exc)
            sys.exit(1)
        self.cursor = self.connection.cursor()
        self.page_size = page_size
        self.lock = threading.RLock()

    #
    # Schema version methods
    #

    def get_schema_version(self):
        self.cursor.execute("SELECT version FROM schema_versions ORDER BY version DESC LIMIT 1;")
        return self.cursor.fetchone()[0]

    def validate_schema_version(self):
        try:
            if self.get_schema_version() != Database.CURRENT_SCHEMA_VERSION:
                raise DatabaseError(f"Schema version mismatch, update Backup-chan. (current = {self.get_schema_version()}, required = {Database.CURRENT_SCHEMA_VERSION})")
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
        alias: str | None,
        min_backups: int | None,
        tags: str | None
    ) -> str:
        with self.lock:
            self.validate_target(name, name_template, location, None, alias)

            target_id = str(uuid.uuid4())
            self.cursor.execute("INSERT INTO targets VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (target_id, name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate, alias, min_backups))
            self.connection.commit()

            if tags:
                self.set_target_tags(target_id, tags)

            self.logger.info("Add target {%s} name: %s type: %s criteria: %s value: %s action: %s location: %s template: %s dedup: %s alias: %s min backups: %d", target_id, name, target_type, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate, alias, min_backups)
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
        alias: str | None,
        min_backups: int | None,
        tags: str | None
    ):
        with self.lock:
            target = self.get_target(id)
            if target is None:
                raise DatabaseError(f"Target with id or alias {id} does not exist")

            target_id = target.id
            self.validate_target(name, name_template, location, target_id, alias)

            self.cursor.execute("UPDATE targets SET name = ?, recycle_criteria = ?, recycle_value = ?, recycle_action = ?, location = ?, name_template = ?, deduplicate = ?, alias = ?, min_backups = ? WHERE id = ? OR alias = ?", (name, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate, alias, min_backups, id, alias))
            self.connection.commit()

            self.set_target_tags(target_id, tags)

            self.logger.info("Update target {%s} name: %s criteria: %s value: %s action: %s location: %s template: %s dedup: %s alias: %s min backups %d", target_id, name, recycle_criteria, recycle_value, recycle_action, location, name_template, deduplicate, alias, min_backups)

    def list_targets(self, page: int = 1, sort_options: TargetSortOptions | None = None) -> list[models.BackupTarget]:
        sort_options = sort_options or TargetSortOptions.default()
        offset = (page - 1) * self.page_size
        with self.lock:
            self.cursor.execute(f"SELECT * FROM targets {sort_options.sql()} LIMIT ? OFFSET ?", (self.page_size, offset))
            rows = self.cursor.fetchall()
            self.cursor.execute(f"SELECT * FROM targets {sort_options.sql()} LIMIT ? OFFSET ?", (self.page_size, offset + self.page_size))
            has_more = bool(self.cursor.fetchall())
            return {
                # Column #0 is ID
                "targets": [models.BackupTarget(*row, self.get_target_tags(row[0])) for row in rows],
                "has_more": has_more
            }

    def list_targets_all(self) -> list[models.BackupTarget]:
        self.cursor.execute("SELECT * FROM targets")
        rows = self.cursor.fetchall()
        return [models.BackupTarget(*row, self.get_target_tags(row[0])) for row in rows]
    
    def get_target(self, id: str) -> None | models.BackupTarget:
        """
        Returns None if the target wasn't found.
        """
        with self.lock:
            self.cursor.execute("SELECT * FROM targets WHERE id = ? OR alias = ?", (id, id))
            row = self.cursor.fetchone()
            return None if row is None else models.BackupTarget(*row, self.get_target_tags(row[0]))

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

    # Methods dealing with tags do not support alias as ID.

    def get_target_tags(self, id: str) -> list[str]:
        with self.lock:
            self.cursor.execute("SELECT tag.name FROM tags tag JOIN target_tags tt ON tt.tag_id = tag.id WHERE tt.target_id = ?", (id,))
            return [row[0] for row in self.cursor.fetchall()]

    def set_target_tags(self, id: str, tags: list[str]):
        with self.lock:
            # Normalize tag names
            tags = [tag.strip() for tag in tags]

            if tags:
                # Insert missing tags
                self.cursor.executemany("INSERT IGNORE INTO tags (name) VALUES (%s)", [(tag,) for tag in tags])

                # Map names to tag IDs
                self.cursor.execute(f"SELECT id, name FROM tags WHERE name IN ({', '.join(['?'] * len(tags))})", tags)
                rows = self.cursor.fetchall()
                tag_map = {row[1]: row[0] for row in rows}

            # Remove existing links
            self.cursor.execute("DELETE FROM target_tags WHERE target_id = ?", (id,))

            if tags:
                # Insert new links
                self.cursor.executemany("INSERT INTO target_tags (target_id, tag_id) VALUES (?, ?)", [(id, tag_map[tag]) for tag in tags])

            self.connection.commit()

    def validate_target(self, name: str, name_template: str, location: str, target_id: str | None, alias: str | None):
        with self.lock:
            # The name must not be empty.
            if len(name.strip()) == 0:
                raise DatabaseError("Target name must not be empty")

            # Name template must contain either ID of backup or its creation date.
            if not nameformat.verify_name(name_template):
                raise DatabaseError("Filename template must contain either creation date or ID of backup")

            # Name template must be unique to this target.
            for target in self.list_targets_all():
                if target.name_template == name_template and target.id != target_id:
                    raise DatabaseError("Name template is not unique to this target")

            # Name template must not contain illegal characters (like '?' on Windows, or '/' on everything else).
            if not utility.is_valid_path(name_template, False):
                raise DatabaseError("Filename template must not contain invalid characters")

            # Location must not contain illegal characters. '/' is okay.
            if not utility.is_valid_path(location, True):
                raise DatabaseError("Target location must not contain invalid characters")
            
            # Alias validation
            if alias is not None:
                # Alias must not be empty.
                if len(alias.strip()) == 0:
                    raise DatabaseError("Alias must not be empty")
                
                # Alias must be unique to this target.
                for target in self.list_targets_all():
                    if target.alias == alias and target.id != target_id:
                        raise DatabaseError("Alias is not unique to this target")

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

    def list_backups(self, sort_options: None | BackupSortOptions = None) -> list[models.Backup]:
        sort_options = sort_options or BackupSortOptions.default()
        with self.lock:
            self.cursor.execute(f"SELECT * FROM backups {sort_options.sql()}")
            rows = self.cursor.fetchall()
            return [models.Backup(*row) for row in rows]

    def list_backups_target(self, target_id: str, sort_options: None | BackupSortOptions = None) -> list[models.Backup]:
        sort_options = sort_options or BackupSortOptions.default()
        with self.lock:
            target = self.get_target(target_id)
            if target is None:
                raise DatabaseError(f"Target with id or alias '{target_id}' does not exist")

            self.cursor.execute(f"SELECT * FROM backups WHERE target_id = ? {sort_options.sql()}", (target.id,))
            rows = self.cursor.fetchall()
            return [models.Backup(*row) for row in rows]

    def list_recycled_backups(self, sort_options: None | BackupSortOptions = None) -> list[models.Backup]:
        sort_options = sort_options or BackupSortOptions.default()
        with self.lock:
            self.cursor.execute(f"SELECT * FROM backups WHERE is_recycled = TRUE {sort_options.sql()}")
            rows = self.cursor.fetchall()
            return [models.Backup(*row) for row in rows]

    def list_backups_target_is_recycled(self, target_id: str, is_recycled: bool, sort_options: None | BackupSortOptions = None) -> list[models.Backup]:
        sort_options = sort_options or BackupSortOptions.default()
        with self.lock:
            target = self.get_target(target_id)
            if target is None:
                raise DatabaseError(f"Target with id or alias '{target_id}' does not exist")

            self.cursor.execute(f"SELECT * FROM backups WHERE (target_id = ?) AND is_recycled = ? {sort_options.sql()}", (target.id, is_recycled))
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
