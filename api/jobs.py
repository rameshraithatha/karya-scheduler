from fastapi import APIRouter, HTTPException
from core.executor import FlowExecutor
from db.models import Job
from db.session import SessionLocal
from db.schemas import JobRequest, JobStatus
import asyncio
import uuid

router = APIRouter()


@router.post("/jobs", response_model=JobStatus)
async def start_job(request: JobRequest):
    job_id = str(uuid.uuid4())
    db = SessionLocal()
    print("#####", request)
    job = Job(
        id=job_id,
        workflow_name=request.workflow_name,
        status="SCHEDULED",
        context=request.parameters,
        steps=request.steps,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    executor = FlowExecutor(request.steps, request.parameters, job_id)
    asyncio.create_task(executor.run())
    return JobStatus(job_id=job_id, status=job.status, context=job.context)


@router.get("/jobs/{job_id}/steps")
async def get_job_steps(job_id: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.steps


@router.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(job_id=job.id, status=job.status, context=job.context)


@router.post("/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    return {"message": "Pause functionality not yet implemented."}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    db = SessionLocal()
    job = db.query(Job).filter(Job.id == job_id).first()
    if job:
        db.delete(job)
        db.commit()
        return {"message": f"Job {job_id} deleted."}
    raise HTTPException(status_code=404, detail="Job not found")


@router.get("/jobs")
async def list_jobs():
    db = SessionLocal()
    jobs = db.query(Job).all()
    return [
        {"job_id": job.id, "status": job.status, "context": job.context} for job in jobs
    ]
