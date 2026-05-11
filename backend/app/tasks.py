from __future__ import annotations
import os
import random as _random
from celery import Celery, chord
from app import cache
from app.models import Fragment, JobStatus
from app.scrapers.images import scrape_images
from app.scrapers.text import scrape_text, scrape_text_enriched, scrape_ddg_text
from app.scrapers.web import scrape_web_bodies
from app.scrapers.archive import scrape_archive
from app.scrapers.wikimedia import scrape_wikimedia
from app.scrapers.music import scrape_music
from app.scrapers.ddg import scrape_ddg_images
from app.scrapers.patents import scrape_patents
from app.pipeline.extractor import extract_fragments
from app.pipeline.ranker import rank_and_filter, rank_and_filter_incremental
from app.pipeline.composer import compose, compose_incremental, _seed_from_topic
from app.pipeline.vibe import classify_vibe

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("scrapbook", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    broker_connection_retry_on_startup=True,
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
def task_scrape_wikimedia(self, topic: str) -> list[dict]:
    return scrape_wikimedia(topic)


@celery_app.task(bind=True)
def task_scrape_enriched_text(self, topic: str) -> list[dict]:
    return scrape_text_enriched(topic)


@celery_app.task(bind=True)
def task_scrape_music(self, topic: str) -> list[dict]:
    return scrape_music(topic)


@celery_app.task(bind=True)
def task_scrape_ddg(self, topic: str) -> list[dict]:
    return scrape_ddg_images(topic)


@celery_app.task(bind=True)
def task_scrape_patents(self, topic: str) -> list[dict]:
    return scrape_patents(topic)


@celery_app.task(bind=True)
def task_scrape_ddg_text(self, topic: str) -> list[dict]:
    return scrape_ddg_text(topic)


@celery_app.task(bind=True)
def task_scrape_web_bodies(self, topic: str) -> list[dict]:
    return scrape_web_bodies(topic)


@celery_app.task(bind=True)
def task_assemble(self, results: list, job_id: str, topic: str, density: str | None = None) -> None:
    images_data, ddg_data, texts_data, archive_data = results

    try:
        _update_job(job_id, JobStatus.running, progress=60)

        fragments = extract_fragments(images_data + ddg_data, texts_data, archive_data)
        _update_job(job_id, JobStatus.running, progress=75)

        layout_seed = _random.randint(0, 2**31 - 1)
        vibe = classify_vibe(topic)
        fragments = rank_and_filter(fragments, vibe=vibe, density=density, layout_seed=layout_seed)
        _update_job(job_id, JobStatus.running, progress=88)

        fragments = compose(topic, fragments, vibe=vibe, density=density, layout_seed=layout_seed)

        cache.set_collage(job_id, _build_collage_dict(job_id, topic, fragments))
        cache.set_topic_cache(topic, job_id, density)
        _update_job(job_id, JobStatus.done, progress=100)

        task_enrich.delay(job_id, topic, density)
    except Exception:
        _update_job(job_id, JobStatus.failed, progress=0)
        raise


@celery_app.task(bind=True)
def task_enrich(self, job_id: str, topic: str, density: str | None = None) -> None:
    _update_job(job_id, JobStatus.running, progress=50)

    pipeline = chord(
        [
            task_scrape_wikimedia.s(topic),
            task_scrape_enriched_text.s(topic),
            task_scrape_music.s(topic),
            task_scrape_patents.s(topic),
            task_scrape_ddg_text.s(topic),
            task_scrape_web_bodies.s(topic),
        ],
        task_assemble_enrichment.s(job_id, topic, density),
    )
    pipeline.apply_async()


@celery_app.task(bind=True)
def task_assemble_enrichment(self, results: list, job_id: str, topic: str, density: str | None = None) -> None:
    wikimedia_data, enriched_texts, music_data, patents_data, ddg_text_data, web_body_data = results

    try:
        existing_collage = cache.get_collage(job_id)
        if not existing_collage:
            return
        existing_fragments = [Fragment(**f) for f in existing_collage["fragments"]]

        new_fragments = extract_fragments(
            images=[],
            texts=[],
            archive=[],
            wikimedia=wikimedia_data,
            enriched_texts=enriched_texts + music_data + patents_data + ddg_text_data + web_body_data,
        )

        layout_seed = _random.randint(0, 2**31 - 1)
        vibe = classify_vibe(topic)
        new_fragments = rank_and_filter_incremental(new_fragments, existing_fragments, vibe=vibe, density=density, layout_seed=layout_seed)
        new_fragments = compose_incremental(topic, new_fragments, existing_fragments, vibe=vibe, density=density, layout_seed=layout_seed)

        all_fragments = existing_fragments + new_fragments
        cache.set_collage(job_id, _build_collage_dict(job_id, topic, all_fragments))
        _update_job(job_id, JobStatus.enriched, progress=100)
    except Exception:
        _update_job(job_id, JobStatus.enriched, progress=100)
        raise


@celery_app.task(bind=True)
def task_orchestrate(self, job_id: str, topic: str, density: str | None = None) -> None:
    _update_job(job_id, JobStatus.running, progress=10)

    pipeline = chord(
        [
            task_scrape_images.s(topic),
            task_scrape_ddg.s(topic),
            task_scrape_text.s(topic),
            task_scrape_archive.s(topic),
        ],
        task_assemble.s(job_id, topic, density),
    )
    pipeline.apply_async()


def _build_collage_dict(job_id: str, topic: str, fragments: list[Fragment]) -> dict:
    return {
        "job_id": job_id,
        "topic": topic,
        "seed": _seed_from_topic(topic),
        "canvas": {"width": 1600, "height": 2200},
        "fragments": [f.model_dump() for f in fragments],
    }


def _update_job(job_id: str, status: JobStatus, progress: int = 0) -> None:
    cache.set_job(job_id, {
        "id": job_id,
        "status": status.value,
        "progress": progress,
    })
