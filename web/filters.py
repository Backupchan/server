import datetime
from backupchan_server import utility
from flask import Blueprint

def add_filters(blueprint: Blueprint):
    @blueprint.app_template_filter()
    def time_until(n_target: float) -> str:
        target = datetime.datetime.fromtimestamp(n_target)
        now = datetime.datetime.now(target.tzinfo) if target.tzinfo else datetime.datetime.now()
        delta = target - now

        total_seconds = int(delta.total_seconds())

        if total_seconds <= 0:
            return "now"

        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []

        if days:
            parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds:
            parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")

        return "in " + ", ".join(parts)

    @blueprint.app_template_filter()
    def pretty_datetime(time: datetime.datetime) -> str:
        return time.strftime("%B %d, %Y %H:%M")

    @blueprint.app_template_filter()
    def pretty_ftime(time: float) -> str:
        return pretty_datetime(datetime.datetime.fromtimestamp(time))

    @blueprint.app_template_filter()
    def pretty_filesize(size: int) -> str:
        return utility.humanread_file_size(size)
