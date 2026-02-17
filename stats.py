import database
import file_manager

class Stats:
    def __init__(self, db: database.Database, fm: file_manager.FileManager):
        self.db = db
        self.fm = fm

    def total_target_size(self) -> int:
        targets = self.db.list_targets_all()
        total = 0
        for target in targets:
            total += self.db.get_target_size(target.id)
        return int(total)

    def total_recycle_bin_size(self) -> int:
        recycled_backups = self.db.list_recycled_backups()
        total = 0
        for backup in recycled_backups:
            total += self.db.get_backup(backup.id).filesize
        return int(total)

    # not worth putting total backups and targets count since they can be easily accessed from the database
