import database
import seq_upload
import stats
import scheduled_jobs
import delayed_jobs
import file_manager
import serverapi
import configtony
from web.auth import WebAuth
from dataclasses import dataclass
from flask import Blueprint

@dataclass
class WebContext:
    blueprint: Blueprint
    auth: WebAuth
    db: database.Database
    seq_upload_manager: seq_upload.SequentialUploadManager
    stats: stats.Stats
    job_scheduler: scheduled_jobs.JobScheduler
    job_manager: delayed_jobs.JobManager
    root_path: str
    fm: file_manager.FileManager
    server_api: serverapi.ServerAPI
    config: configtony.Config
