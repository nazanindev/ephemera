from __future__ import annotations

from app.pipeline.vibe import classify_vibe

BRAND_TAG = "ephemera"

# substring found in a fragment's source_domain -> the source label we tag.
# Each distinct source present in a collage gets its own tag (tags do the sorting).
_DOMAIN_SOURCES = [
    ("wikipedia", "wikipedia"),
    ("wikimedia", "wikimedia"),
    ("wikiquote", "wikiquote"),
    ("reddit", "reddit"),
    ("ycombinator", "hacker news"),
    ("musicbrainz", "musicbrainz"),
    ("patents.google", "patents"),
    ("archive.org", "internet archive"),
]


def vibe_band(vibe: float) -> str:
    if vibe < 0.40:
        return "sparse"
    if vibe > 0.60:
        return "dense"
    return "neutral-zone"


def _seed_hex(collage: dict) -> str:
    seed = collage.get("layout_seed")
    if seed is None:
        seed = collage.get("seed")  # topic-hash fallback (older collages)
    return f"{seed:08x}" if isinstance(seed, int) else "—"


def lab_line(topic: str, collage: dict, density: str | None) -> str:
    """The data readout — ends at fragment count. No source counts (those are tags), no prose."""
    vibe = classify_vibe(topic)
    n = len(collage.get("fragments", []))
    return f"vibe {vibe:.2f} · {density or 'auto'} · seed {_seed_hex(collage)} · {n} fragments"


def collage_sources(collage: dict) -> list[str]:
    """Every distinct content source present in the collage, as tag labels."""
    found: set[str] = set()
    for f in collage.get("fragments", []):
        if f.get("type") == "archive_screenshot":
            found.add("wayback machine")
        src = f.get("image_source")  # "openverse" | "wikimedia"
        if src:
            found.add(src)
        dom = (f.get("source_domain") or "").lower()
        for needle, label in _DOMAIN_SOURCES:
            if needle in dom:
                found.add(label)
                break
    return sorted(found)


def build_tags(topic, collage, density, experiment, meta_topics) -> list[str]:
    """Rich, navigational tag set — the blog's index lives here, not in photosets."""
    band = density or vibe_band(classify_vibe(topic))
    tags = [BRAND_TAG]
    if experiment is not None and experiment.tag:
        tags.append(experiment.tag)          # series (e.g. seed-series)
    tags.append(topic.strip().lower())       # the prompt — groups ladders/seed-series
    tags.append(band)                        # dense | sparse | neutral-zone
    tags.extend(meta_topics or ())           # history | art | culture | ...
    tags.extend(collage_sources(collage))    # openverse, wikipedia, wayback machine, ...
    seen: set[str] = set()
    return [t for t in tags if t and not (t in seen or seen.add(t))]


def build_caption(topic, collage, density, experiment=None, meta_topics=()) -> tuple[str, list[str]]:
    caption = f'"{topic}"\n{lab_line(topic, collage, density)}'
    return caption, build_tags(topic, collage, density, experiment, meta_topics)
