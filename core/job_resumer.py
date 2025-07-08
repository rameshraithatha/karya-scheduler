from datetime import datetime, UTC
import asyncio
import logging
from db.session import SessionLocal
from db.models import Job
from core.executor import FlowExecutor
from core import job_utils

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def resume_due_jobs():
    session = SessionLocal()
    now = datetime.now(UTC)

    due_jobs = (
        session.query(Job).filter(Job.status == "WAITING", Job.resume_at <= now).all()
    )

    for job in due_jobs:
        logger.info(f"[Job {job.id}] Attempting to resume job...")

        if job_utils.exceeded_max_retries(job):
            job.status = "FAILED"
            job.message = (
                f"Max retries exceeded for step '{job.context['meta']['current_step']}'"
            )
            session.commit()
            logger.warning(f"[Job {job.id}] Failed — max retries exceeded.")
            continue

        job.status = "RUNNING"
        job.updated_at = datetime.now(UTC)
        session.commit()  # commit after mutation

        logger.info(
            f"[Job {job.id}] Resuming (retry #{job_utils.get_retry_count(job)})..."
        )

        executor = FlowExecutor(
            steps=job.steps, parameters=job.context.get("context", {}), job_id=job.id
        )
        await executor.run()

    session.close()


if __name__ == "__main__":
    asyncio.run(resume_due_jobs())
