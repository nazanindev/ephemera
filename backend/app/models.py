from __future__ import annotations
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import uuid


class FragmentType(str, Enum):
    image = "image"
    headline = "headline"
    snippet = "snippet"
    metadata = "metadata"
    archive_screenshot = "archive_screenshot"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    enriched = "enriched"
    failed = "failed"


class FragmentLayout(BaseModel):
    x: float  # 0–1 fraction of canvas width
    y: float  # 0–1 fraction of canvas height
    width: int  # px
    height: int  # px
    rotation: float  # degrees
    z_index: int
    css_filter: str
    blend_mode: str
    text_color: str = ""  # override color for text fragments, e.g. "#ffffff"


class Fragment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: FragmentType
    content: str  # URL for images/archive, raw text for text types
    source_url: str = ""
    source_domain: str = ""
    image_source: str = ""  # "openverse" | "wikimedia" | ""
    captured_at: str | None = None
    og: dict[str, Any] = Field(default_factory=dict)
    layout: FragmentLayout | None = None


class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    status: JobStatus = JobStatus.pending
    progress: int = 0  # 0–100
    error: str | None = None


class GenerateRequest(BaseModel):
    topic: str
    density: str | None = None  # "sparse" | "dense" | None
    layout_seed: int | None = None  # pin composition for reproducible / seed-series runs


class GenerateResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    status: JobStatus
    progress: int
    error: str | None = None


class CanvasConfig(BaseModel):
    width: int = 1800
    height: int = 1200


class CollageResponse(BaseModel):
    job_id: str
    topic: str
    seed: int  # topic hash (deterministic per topic)
    layout_seed: int | None = None  # the actual composition seed used for this collage
    canvas: CanvasConfig
    fragments: list[Fragment]
