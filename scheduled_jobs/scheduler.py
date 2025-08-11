import time
import logging
import threading
import datetime

class ScheduledJob:
    def __init__(self, interval: int, name: str):
        self.interval = interval
        self.name = name
        self.next_run = time.time() + interval
        self.logger = logging.getLogger(name)
        self.force_flag = False

        self.logger.info(f"Created scheduled job {name} (interval: {interval} sec)")
 
    def run(self):
        raise NotImplementedError()

    def force_run(self):
        self.force_flag = True
        self.logger.info("Force re-run")

    def pretty_next_run(self) -> str:
        return datetime.datetime.fromtimestamp(self.next_run).strftime("%b %d, %Y at %I:%M:%S %p")

class JobScheduler:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.jobs: list[ScheduledJob] = []

    def start(self):
        self.logger.info("Start job scheduler")
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        while True:
            self.tick()
            time.sleep(1)

    def tick(self):
        now = time.time()
        for job in self.jobs:
            if now >= job.next_run or job.force_flag:
                self.logger.info("Run job %s", job.name)
                job.force_flag = False
                start_time = time.perf_counter()
                try:
                    job.run()
                except Exception as exc:
                    self.logger.error("Exception raised when running job %s", job.name, exc_info=exc)
                end_time = time.perf_counter()
                elapsed_time = end_time - start_time
                self.logger.info("Finished running job (took %.4f seconds)", elapsed_time)
                job.next_run = now + job.interval

    def add_job(self, job: ScheduledJob):
        self.jobs.append(job)

    def force_run_job(self, name: str):
        for job in self.jobs:
            if job.name == name:
                job.force_run()
                return
        self.logger.warn(f"Requested to force-run job {name}, but no such job found.")
