import database
import serverapi
import configtony
import file_manager
import stats
import delayed_jobs
import scheduled_jobs
import seq_upload
from api.auth import APIAuth
from dataclasses import dataclass
from flask import Blueprint

@dataclass
class APIContext:
    blueprint: Blueprint
    auth: APIAuth
    db: database.Database
    server_api: serverapi.ServerAPI
    fm: file_manager.FileManager
    config: configtony.Config
    stats: stats.Stats
    job_manager: delayed_jobs.JobManager
    job_scheduler: scheduled_jobs.JobScheduler
    seq_upload_manager: seq_upload.SequentialUploadManager
