import delayed_jobs
import time

class TestJob(delayed_jobs.DelayedJob):
    def __init__(self):
        super().__init__(__name__.split(".")[-1])

    def run(self) -> delayed_jobs.DelayedJobState:
        for _ in range(5):
            self.logger.info("Pretending I'm doing something.")
            time.sleep(1)
        return delayed_jobs.DelayedJobState.FINISHED
