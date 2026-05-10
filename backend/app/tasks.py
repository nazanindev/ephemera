from __future__ import annotations
import os
from celery import Celery, chord
from app import cache
from app.models import JobStatus
from app.scrapers.images import scrape_images
from app.scrapers.text import scrape_text
from app.scrapers.archive import scrape_archive
from app.pipeline.extractor import extract_fragments
from app.pipeline.ranker import rank_and_filter
from app.pipeline.composer import compose, _seed_from_topic

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("scrapbook", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)


@celery_app.task(bind=True)
def task_scrape_images(self, topic: str) -> list[dict]:
    return scrape_images(topic)


@celery_app.task(bind=True)
def task_scrape_text(self, topic: str) -> list[dict]:
    return scrape_text(topic)


@celery_app.task(bind=True)
def task_scrape_archive(self, topic: str) -> list[dict]:
    return scrape_archive(topic)


@celery_app.task(bind=True)
def task_assemble(self, results: list, job_id: str, topic: str) -> None:
    images_data, texts_data, archive_data = results

    try:
        _update_job(job_id, JobStatus.running, progress=60)

        fragments = extract_fragments(images_data, texts_data, archive_data)
        _update_job(job_id, JobStatus.running, progress=75)

        fragments = rank_and_filter(fragments)
        _update_job(job_id, JobStatus.running, progress=88)

        fragments = compose(topic, fragments)

        collage = {
            "job_id": job_id,
            "topic": topic,
            "seed": _seed_from_topic(topic),
            "canvas": {"width": 1800, "height": 1200},
            "fragments": [f.model_dump() for f in fragments],
        }
        cache.set_collage(job_id, collage)
        cache.set_topic_cache(topic, job_id)
        _update_job(job_id, JobStatus.done, progress=100)
    except Exception as exc:
        _update_job(job_id, JobStatus.failed, progress=0)
        raise


@celery_app.task(bind=True)
def task_orchestrate(self, job_id: str, topic: str) -> None:
    _update_job(job_id, JobStatus.running, progress=10)

    pipeline = chord(
        [
            task_scrape_images.s(topic),
            task_scrape_text.s(topic),
            task_scrape_archive.s(topic),
        ],
        task_assemble.s(job_id, topic),
    )
    pipeline.apply_async()


def _update_job(job_id: str, status: JobStatus, progress: int = 0) -> None:
    cache.set_job(job_id, {
        "id": job_id,
        "status": status.value,
        "progress": progress,
    })
