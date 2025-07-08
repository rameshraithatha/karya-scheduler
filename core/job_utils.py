from db.models import Job
from typing import Dict, Any


def get_current_step(job: Job) -> Dict[str, Any]:
    """Returns the current step definition based on job.context.meta.current_step"""
    current_step_id = (job.context or {}).get("meta", {}).get("current_step")
    for step in job.steps or []:
        if step["id"] == current_step_id:
            return step
    return {}


def get_retry_count(job: Job) -> int:
    """Returns the retry count for the current step from context.meta.step_retries"""
    meta = (job.context or {}).get("meta", {})
    current_step_id = meta.get("current_step")
    retry_counts = meta.get("step_retries", {})
    return retry_counts.get(current_step_id, 0)


def increment_retry_count(job: Job):
    """Increments retry count in job.context.meta.step_retries and updates job context"""
    step_id = (job.context or {}).get("meta", {}).get("current_step")
    if not step_id:
        return

    meta = job.context.setdefault("meta", {})
    retries = meta.setdefault("step_retries", {})
    retries[step_id] = retries.get(step_id, 0) + 1

    job.step_retry_counts = retries
    job.context["meta"]["step_retries"] = retries


def exceeded_max_retries(job: Job) -> bool:
    """Checks if current step has exceeded its max_retries (default = 5)"""
    step = get_current_step(job)
    if step.get("type") != "wait":
        return False
    retry_count = get_retry_count(job)
    max_retries = step.get("max_retries", 5)
    return retry_count >= max_retries
