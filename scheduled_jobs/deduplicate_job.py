import scheduled_jobs
import serverapi
import database
import file_manager

class DeduplicateJob(scheduled_jobs.ScheduledJob):
    def __init__(self, interval: int, db: database.Database, fm: file_manager.FileManager, server_api: serverapi.ServerAPI):
        super().__init__(interval, __name__.split(".")[-1])

        self.db = db
        self.fm = fm
        self.server_api = server_api
        
        self.backup_hash_cache = {}

    def clear_cache(self):
        self.backup_hash_cache = {}

    def get_cached_backup_hash(self, id: str) -> str:
        if id not in self.backup_hash_cache:
            backup_hash = self.fm.get_backup_hash(id)
            self.backup_hash_cache[id] = backup_hash
            return backup_hash
        return self.backup_hash_cache[id]

    def run(self):
        for target in self.db.list_targets_all():
            if not target.deduplicate:
                continue

            self.logger.info("Check target {%s} (%s)", target.id, target.name)

            # Newest->Oldest
            backups_all = self.db.list_backups_target(target.id)
            backups = sorted(backups_all, key=lambda a: a.created_at, reverse=True)
            for backup in backups:
                self.logger.info(" -> check {%s}", backup.id)

                # Oldest->Newest, exclude current
                backups_iterate = sorted(backups_all, key=lambda a: a.created_at)
                backups_iterate.remove(backup)

                try:
                    current_hash = self.fm.get_backup_hash(backup.id)
                except file_manager.FileManagerError as exc:
                    self.logger.error("Failed to get backup hash", exc_info=exc)
                    continue

                is_dupe = False
                for backup_check in backups_iterate:
                    self.logger.info("   -> against {%s}", backup_check.id)

                    try:
                        backup_hash = self.get_cached_backup_hash(backup_check.id)
                    except file_manager.FileManagerError as exc:
                        self.logger.error("Failed to get backup hash", exc_info=exc)
                        continue
                    if backup_hash == current_hash:
                        self.logger.info("Duplicate. Remove backup {%s}", backup.id)
                        self.server_api.delete_backup(backup.id, True)
                        is_dupe = True

                    if is_dupe:
                        break
                if is_dupe:
                    continue

        self.clear_cache()
