from __future__ import annotations
from collections import Counter

from app.pipeline.vibe import classify_vibe

# The closed tag vocabulary (low-cardinality axes someone can actually browse).
# Per-post numbers (vibe, seed, counts) live in the caption body, never in tags.
BRAND_TAG = "ephemera"

_IMAGE_TYPES = {"image", "archive_screenshot"}


def vibe_band(vibe: float) -> str:
    if vibe < 0.40:
        return "sparse"
    if vibe > 0.60:
        return "dense"
    return "neutral-zone"


def _source_counts(collage: dict) -> str:
    images = [f for f in collage.get("fragments", []) if f.get("type") in _IMAGE_TYPES]
    counts = Counter((f.get("image_source") or "other") for f in images)
    return ", ".join(f"{src} ×{n}" for src, n in counts.most_common())


def _seed_hex(collage: dict) -> str:
    seed = collage.get("layout_seed")
    if seed is None:
        seed = collage.get("seed")  # topic hash fallback (older collages)
    return f"{seed:08x}" if isinstance(seed, int) else "—"


def lab_line(topic: str, collage: dict, density: str | None) -> str:
    """The lab-notebook readout for a single collage."""
    vibe = classify_vibe(topic)
    n = len(collage.get("fragments", []))
    line = f"vibe {vibe:.2f} · {density or 'auto'} · seed {_seed_hex(collage)} · {n} fragments"
    sources = _source_counts(collage)
    if sources:
        line += f" · {sources}"
    return line


def build_tags(band: str | None, experiment) -> list[str]:
    """series tag + (optional) vibe band + brand. Small on purpose."""
    tags = [BRAND_TAG]
    if experiment is not None and experiment.tag:
        tags.append(experiment.tag)
    if band:
        tags.append(band)
    # de-dup while preserving order
    seen: set[str] = set()
    return [t for t in tags if not (t in seen or seen.add(t))]


def build_caption(topic: str, collage: dict, density: str | None, experiment) -> tuple[str, list[str]]:
    """Caption + tags for a single-collage post."""
    band = vibe_band(classify_vibe(topic))
    body = [f'"{topic}"', "", lab_line(topic, collage, density)]
    if experiment is not None and experiment.blurb:
        body += ["", experiment.blurb]
    return "\n".join(body), build_tags(band, experiment)


def build_series_caption(items: list[tuple[str, str | None, dict]], experiment) -> tuple[str, list[str]]:
    """Caption + tags for a photoset post (one caption over several collages).

    items: list of (topic, density, collage) in display order.
    """
    header = experiment.name if experiment is not None else "series"
    lines: list[str] = [header]
    if experiment is not None and experiment.blurb:
        lines.append(experiment.blurb)
    lines.append("")
    for topic, density, collage in items:
        lines.append(f'"{topic}"')
        lines.append(f"  {lab_line(topic, collage, density)}")
    # photosets mix bands, so no band tag — just brand + series.
    return "\n".join(lines), build_tags(None, experiment)
