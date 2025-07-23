import jobs
import time
import serverapi
import database
import logging
import models
import datetime
import threading

class RecycleJob(jobs.ScheduledJob):
    def __init__(self, interval: int, db: database.Database, server_api: serverapi.ServerAPI):
        """
        Interval is in minutes.
        """
        super().__init__(interval, __name__.split(".")[-1])

        self.db = db
        self.server_api = server_api
        self.interval = interval
        self.lock = threading.Lock()

    def run(self):
        with self.lock:
            targets = self.db.list_targets()
            for target in targets:
                self.logger.info("Check target {%s}", target.id)

                if target.recycle_criteria == models.BackupRecycleCriteria.NONE:
                    self.logger.info("Target has no recycle criteria.")
                    continue
                else:
                    self.check_target(target)
                    self.logger.info("Finished checking target")

    def check_target(self, target: models.BackupTarget):
        if target.recycle_criteria == models.BackupRecycleCriteria.NONE:
            self.logger.warn("Tried to check target with no recycle criteria: id {%s}", target.id)
            return

        backups = self.db.list_backups_target_is_recycled(target.id, False)
        backups.sort(key=lambda a: a.created_at)

        if target.recycle_criteria == models.BackupRecycleCriteria.COUNT:
            max_backups = target.recycle_value
            num_backups = len(backups)

            if num_backups > max_backups:
                self.logger.info("Criteria = count; Number of backups (%d) exceeds limit (%d), recycling oldest", num_backups, max_backups)
                new_num_backups = num_backups
                delete_backup_ids = []
                for backup in backups:
                    delete_backup_ids.append(backup.id)
                    new_num_backups -= 1
                    if new_num_backups <= max_backups:
                        break
                for backup_id in delete_backup_ids:
                    self.execute_recycle_action(target.recycle_action, backup_id, target.id)
            else:
                self.logger.info("Criteria = count; Number of backups (%d) is within limit (%d), skipping", num_backups, max_backups)
        elif target.recycle_criteria == models.BackupRecycleCriteria.AGE:
            max_age = target.recycle_value
            now = datetime.datetime.now()

            self.logger.info("Criteria = age; Recycling backups older than %d days", max_age)

            for backup in backups:
                age = (now - backup.created_at).days
                if age > max_age:
                    self.logger.info("Backup {%s} is %d days old", backup.id, age)
                    self.execute_recycle_action(target.recycle_action, backup, target.id)
        else:
            self.logger.error("Target {%s} has a broken recycle criteria value", target.id)

    def execute_recycle_action(self, recycle_action: models.BackupRecycleAction, backup_id: str, target_id: str):
        self.logger.info("Execute recycle action (%s) on backup {%s}", recycle_action, backup_id)
        if recycle_action == models.BackupRecycleAction.DELETE:
            self.server_api.delete_backup(backup_id)
        elif recycle_action == models.BackupRecycleAction.RECYCLE:
            self.server_api.recycle_backup(backup_id)
        else:
            self.logger.error("Target {%s} has a broken recycle action value", target_id)
