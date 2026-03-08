import database
import file_manager
import serverapi
import scheduled_jobs
import delayed_jobs
import stats
import seq_upload
import configtony
import logging
from web import routes
from web import filters
from web.auth import WebAuth
from web.context import WebContext
from flask import Blueprint

class WebUI:
    def __init__(
            self,
            db: database.Database,
            fm: file_manager.FileManager,
            server_api: serverapi.ServerAPI,
            job_scheduler: scheduled_jobs.JobScheduler,
            job_manager: delayed_jobs.JobManager,
            stats: stats.Stats,
            seq_upload_manager: seq_upload.SequentialUploadManager,
            config: configtony.Config,
            passwd_hash: str | None,
            root_path: str):
        self.config = config
        self.blueprint = Blueprint("webui", __name__)
        self.auth = WebAuth(passwd_hash, self.config)

        self.auth.add_routes(self.blueprint)
        filters.add_filters(self.blueprint)

        self.context = WebContext(
                self.blueprint,
                self.auth,
                db,
                seq_upload_manager,
                stats,
                job_scheduler,
                job_manager,
                root_path,
                fm,
                server_api,
                self.config
        )
        routes.add_routes(self.context)
