import scheduled_jobs
import database
import file_manager
from backupchan_server import utility

class BackupFilesizeJob(scheduled_jobs.ScheduledJob):
    def __init__(self, interval: int, db: database.Database, fm: file_manager.FileManager):
        super().__init__(interval, __name__.split(".")[-1])

        self.db = db
        self.fm = fm

    def run(self):
        targets = self.db.list_targets()
        for target in targets:
            self.logger.info("Check target {%s} (%s)", target.id, target.name)
            for backup in self.db.list_backups_target(target.id):
                old_filesize = backup.filesize
                try:
                    new_filesize = self.fm.get_backup_size(backup.id)
                except file_manager.FileManagerError as exc:
                    self.logger.error("Unable to retrieve filesize for backup {%s}", backup.id, exc_info=exc)
                    continue
                status_string = "no change"
                if old_filesize != new_filesize:
                    status_string = f"{old_filesize} ({utility.humanread_file_size(old_filesize)}) -> {new_filesize} ({utility.humanread_file_size(new_filesize)})"
                    self.db.set_backup_filesize(backup.id, new_filesize)
                self.logger.info(" -> %s ( %s )", backup.id, status_string)
