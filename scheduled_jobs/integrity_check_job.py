import scheduled_jobs
import database
import file_manager

class IntegrityCheckJob(scheduled_jobs.ScheduledJob):
    def __init__(self, interval: int, db: database.Database, fm: file_manager.FileManager):
        super().__init__(interval, __name__.split(".")[-1], "Check backup integrity")

        self.db = db
        self.fm = fm

    def run(self):
        targets = self.db.list_targets_all()
        for target in targets:
            self.logger.info("Check target {%s} (%s)", target.id, target.name)
            for backup in self.db.list_backups_target(target.id):
                if backup.hash:
                    self.logger.info(" -> Checking backup {%s}", backup.id)
                    on_disk_hash = self.fm.get_backup_hash(backup.id)
                    if on_disk_hash != backup.hash:
                        self.logger.warn(f"  -> Mismatch (expected=%s, got=%s)", backup.hash, on_disk_hash)
                        if not backup.hash_mismatch:
                            self.db.set_backup_hash_mismatch(backup.id, True)
                    elif backup.hash_mismatch:
                        self.logger.info("  -> No longer mismatch")
                        self.db.set_backup_hash_mismatch(backup.id, False)
                else:
                    self.logger.info(" -> Creating new hash for backup {%s}", backup.id)
                    self.db.set_backup_hash(backup.id, self.fm.get_backup_hash(backup.id))
                    self.db.set_backup_hash_mismatch(backup.id, False)
