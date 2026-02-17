import scheduled_jobs
import os
import datetime
from backupchan_server import utility

class TemporaryPurgeJob(scheduled_jobs.ScheduledJob):
    def __init__(self, interval: int, temp_dir: str):
        super().__init__(interval, __name__.split(".")[-1])

        self.temp_dir = temp_dir

    def run(self):
        temp_files = os.listdir(self.temp_dir)
        for i, file in enumerate(temp_files):
            temp_files[i] = utility.join_path(self.temp_dir, file)
        files = [file for file in temp_files if os.path.isfile(file)]
        now = datetime.datetime.now()
        for file in files:
            mod_timestamp = os.path.getmtime(file)
            mod_datetime = datetime.datetime.fromtimestamp(mod_timestamp)
            file_age = now - mod_datetime
            if file_age.days > 1:
                self.logger.info("Deleting temporary file '%s' as it is older than 1 day", file)
                os.remove(file)
