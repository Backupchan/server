from api.context import APIContext
from flask import jsonify

def add_routes(context: APIContext):
    @context.blueprint.route("/jobs", methods=["GET"])
    @context.auth.requires_auth
    def list_jobs():
        scheduled_json = []
        delayed_json = []

        for job in context.job_scheduler.jobs:
            scheduled_json.append({
                "name": job.name,
                "interval": job.interval,
                "next_run": job.next_run
            })

        for id, job in context.job_manager.jobs.items():
            delayed_json.append({
                "id": id,
                "name": job.name,
                "display_name": job.display_name,
                "status": job.state.name,
                "start_time": job.start_time,
                "end_time": job.end_time
            })

        return jsonify(success=True, scheduled=scheduled_json, delayed=delayed_json), 200

    @context.blueprint.route("/jobs/force_run/<name>")
    @context.auth.requires_auth
    def force_run_job(name: str):
        context.job_scheduler.force_run_job(name)
        return jsonify(success=True)
