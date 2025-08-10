import delayed_jobs
import serverapi
from werkzeug.datastructures import FileStorage

class UploadJob(delayed_jobs.DelayedJob):
    def __init__(self, target_id: str, manual: bool, temp_save_path: str, file: FileStorage, server_api: serverapi.ServerAPI):
        super().__init__(__name__.split(".")[-1])
        self.target_id = target_id
        self.manual = manual
        self.temp_save_path = temp_save_path
        self.file = file
        self.server_api = server_api

    def run(self) -> delayed_jobs.DelayedJobState:
        self.logger.info("Upload backup to target {%s}: manual {%s}, backup file: %s", self.target_id, self.manual, self.file.filename)
        self.server_api.upload_backup(self.target_id, self.manual, self.temp_save_path, self.file)
        return delayed_jobs.DelayedJobState.FINISHED
