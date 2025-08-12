import scheduled_jobs
import seq_upload

class StaleSequentialUploadJob(scheduled_jobs.ScheduledJob):
    def __init__(self, interval: int, manager: seq_upload.SequentialUploadManager):
        super().__init__(interval, __name__.split(".")[-1])

        self.manager = manager

    def run(self):
        for target_id in self.manager:
            if self.manager[target_id].expired():
                self.logger.info("Sequential upload on target {%s} expired, deleting", target_id)
                self.manager.delete(target_id)
