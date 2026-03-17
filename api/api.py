import database
import serverapi
import configtony
import file_manager
import stats
import delayed_jobs
import scheduled_jobs
import seq_upload
from api.context import APIContext
from api import routes
from api.auth import APIAuth
from flask import Blueprint

class API:
    """
    Refer to API.md for documentaton on the JSON API.
    """
    def __init__(
            self,
            db: database.Database,
            server_api: serverapi.ServerAPI,
            config: configtony.Config,
            fm: file_manager.FileManager,
            stats: stats.Stats,
            job_manager: delayed_jobs.JobManager,
            job_scheduler: scheduled_jobs.JobScheduler,
            seq_upload_manager: seq_upload.SequentialUploadManager):
        self.blueprint = Blueprint("api", __name__)
        self.auth = APIAuth()
        context = APIContext(self.blueprint, self.auth, db, server_api, fm, config, stats, job_manager, job_scheduler, seq_upload_manager)
        routes.add_routes(context)
