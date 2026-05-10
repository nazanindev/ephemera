import json
import os
import redis

_client: redis.Redis | None = None

COLLAGE_TTL = 3600  # 1 hour
JOB_TTL = 7200      # 2 hours

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    return _client


def set_job(job_id: str, data: dict) -> None:
    get_client().setex(f"job:{job_id}", JOB_TTL, json.dumps(data))


def get_job(job_id: str) -> dict | None:
    raw = get_client().get(f"job:{job_id}")
    return json.loads(raw) if raw else None


def set_collage(job_id: str, data: dict) -> None:
    get_client().setex(f"collage:{job_id}", COLLAGE_TTL, json.dumps(data))


def get_collage(job_id: str) -> dict | None:
    raw = get_client().get(f"collage:{job_id}")
    return json.loads(raw) if raw else None


def get_cached_collage_id(topic: str) -> str | None:
    return get_client().get(f"topic:{topic}")


def set_topic_cache(topic: str, job_id: str) -> None:
    get_client().setex(f"topic:{topic}", COLLAGE_TTL, job_id)
