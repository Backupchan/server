import threading
import logging
import datetime
from enum import Enum

class DelayedJobState(Enum):
    RUNNING = 0
    ERROR = 1
    FINISHED = 2
    IDLE = 3

class DelayedJob:
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self.state = DelayedJobState.IDLE
        self.start_time = 0
        self.end_time = 0

        self.logger.info(f"Created delayed job %s", name)

    def start(self):
        self.start_time = datetime.datetime.now()
        self.state = DelayedJobState.RUNNING
        try:
            self.state = self.run()
        except Exception as exc:
            self.logger.info("Encountered error when running job %s", self.name, exc_info=exc)
            self.state = DelayedJobState.ERROR
        self.end_time = datetime.datetime.now()
        self.logger.info("Delayed job %s finished with state: %s", self.name, self.state)

    def run(self):
        raise NotImplementedError()

class JobManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.jobs: dict[int, DelayedJob] = {}
        self.current_id = 1

    def run_job(self, job: DelayedJob) -> int:
        job_id = self.current_id
        self.jobs[job_id] = job
        self.current_id += 1
        threading.Thread(target=job.start).start()
        self.logger.info("Started delayed job #%d", job_id)
        return job_id
