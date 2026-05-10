from __future__ import annotations
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app import cache
from app.models import (
    GenerateRequest,
    GenerateResponse,
    JobStatus,
    JobStatusResponse,
    CollageResponse,
)
from app.tasks import task_orchestrate

app = FastAPI(title="Scrapbook Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest):
    topic = req.topic.strip()
    density = req.density if req.density in ("sparse", "dense") else None
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")

    # Return cached result immediately if available
    cached_id = cache.get_cached_collage_id(topic, density)
    if cached_id and cache.get_collage(cached_id):
        return GenerateResponse(job_id=cached_id)

    job_id = str(uuid.uuid4())
    cache.set_job(job_id, {
        "id": job_id,
        "status": JobStatus.pending.value,
        "progress": 0,
    })
    task_orchestrate.delay(job_id, topic, density)
    return GenerateResponse(job_id=job_id)


@app.get("/job/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str):
    data = cache.get_job(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="job not found")
    return JobStatusResponse(
        status=data["status"],
        progress=data.get("progress", 0),
        error=data.get("error"),
    )


@app.get("/collage/{job_id}", response_model=CollageResponse)
def get_collage(job_id: str):
    data = cache.get_collage(job_id)
    if not data:
        job = cache.get_job(job_id)
        if job and job["status"] == JobStatus.done.value:
            raise HTTPException(status_code=500, detail="collage missing despite done status")
        raise HTTPException(status_code=404, detail="collage not ready")
    return CollageResponse(**data)


@app.get("/health")
def health():
    return {"ok": True}
