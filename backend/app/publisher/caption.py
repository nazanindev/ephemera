from __future__ import annotations
import re

from app.pipeline.vibe import classify_vibe

BRAND_TAG = "ephemera"

# substring found in a fragment's source_domain -> the source label we tag.
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

_YEAR_RE = re.compile(r"\b(1[89]\d\d|20[0-2]\d)\b")
_CANVAS_BG = (237, 229, 216)  # the cream background; excluded from palette analysis
_TEXT_TYPES = {"headline", "snippet", "metadata"}


def vibe_band(vibe: float) -> str:
    if vibe < 0.40:
        return "sparse"
    if vibe > 0.60:
        return "dense"
    return "neutral-zone"


def _seed_hex(collage: dict) -> str:
    seed = collage.get("layout_seed")
    if seed is None:
        seed = collage.get("seed")
    return f"{seed:08x}" if isinstance(seed, int) else "—"


def lab_line(topic: str, collage: dict, density: str | None) -> str:
    """Data readout — ends at fragment count. No source counts (tags), no prose."""
    vibe = classify_vibe(topic)
    n = len(collage.get("fragments", []))
    return f"vibe {vibe:.2f} · {density or 'auto'} · seed {_seed_hex(collage)} · {n} fragments"


# ── tag axes ────────────────────────────────────────────────────────────────

def collage_sources(collage: dict) -> list[str]:
    """Every distinct content source present in the collage."""
    found: set[str] = set()
    for f in collage.get("fragments", []):
        if f.get("type") == "archive_screenshot":
            found.add("wayback machine")
        src = f.get("image_source")
        if src:
            found.add(src)
        dom = (f.get("source_domain") or "").lower()
        for needle, label in _DOMAIN_SOURCES:
            if needle in dom:
                found.add(label)
                break
    return sorted(found)


def _years(topic: str, collage: dict) -> set[int]:
    """Intentional/historical years only: the topic + Wayback capture years.

    Deliberately skips text-metadata years, which are article *publication* dates
    (often recent) and don't describe the subject's era.
    """
    years = {int(y) for y in _YEAR_RE.findall(topic)}
    for f in collage.get("fragments", []):
        if f.get("type") == "archive_screenshot":
            y = (f.get("og") or {}).get("year")
            if y and str(y).isdigit():
                years.add(int(y))
    return years


def _era(year: int) -> str:
    if year < 1901:
        return "victorian"
    if year <= 1945:
        return "early 20th century"
    if year <= 1970:
        return "midcentury"
    if year <= 2000:
        return "late 20th century"
    return "21st century"


def _time_tags(topic: str, collage: dict) -> list[str]:
    years = _years(topic, collage)
    if not years:
        return []
    tags = [f"{(y // 10) * 10}s" for y in sorted({(y // 10) * 10 for y in years})[:2]]
    tags.append(_era(min(years)))
    return tags


def _composition_tags(collage: dict) -> list[str]:
    frags = collage.get("fragments", [])
    has_text = any(f.get("type") in _TEXT_TYPES for f in frags)
    tags = ["with-text" if has_text else "image-only"]
    if any(f.get("type") == "archive_screenshot" for f in frags):
        tags.append("with-archive")
    return tags


def _shape_tags(topic: str) -> list[str]:
    return ["one-word" if len(topic.split()) == 1 else "multi-word"]


def palette_tags(image_path: str | None) -> list[str]:
    """Warmth / saturation / brightness of the actual imagery (background excluded)."""
    if not image_path:
        return []
    try:
        from PIL import Image
        im = Image.open(image_path).convert("RGB")
    except Exception:
        return []
    im.thumbnail((90, 124))
    rs = gs = bs = sat = 0.0
    n = 0
    for r, g, b in im.getdata():
        if abs(r - _CANVAS_BG[0]) < 22 and abs(g - _CANVAS_BG[1]) < 22 and abs(b - _CANVAS_BG[2]) < 22:
            continue  # skip cream background
        rs += r; gs += g; bs += b; n += 1
        mx, mn = max(r, g, b), min(r, g, b)
        sat += 0.0 if mx == 0 else (mx - mn) / mx
    if n < 40:
        return []
    ar, ag, ab, asat = rs / n, gs / n, bs / n, sat / n
    bright, warmth = (ar + ag + ab) / 3, ar - ab
    tags = ["warm" if warmth > 14 else "cool" if warmth < -6 else "neutral-tone"]
    if asat < 0.16:
        tags.append("sepia" if warmth > 12 else "monochrome")
    elif asat > 0.42:
        tags.append("vivid")
    if bright < 95:
        tags.append("dark")
    elif bright > 182:
        tags.append("bright")
    return tags


def build_tags(topic, collage, density, experiment, meta_topics, image_path=None) -> list[str]:
    """Rich, navigational tag set — the blog's whole index lives here."""
    band = density or vibe_band(classify_vibe(topic))
    core = [BRAND_TAG]
    if experiment is not None and experiment.tag:
        core.append(experiment.tag)
    core.extend(meta_topics or ())
    core.append(band)

    axes = _time_tags(topic, collage) + palette_tags(image_path) \
        + _composition_tags(collage) + _shape_tags(topic)

    sources = collage_sources(collage)
    if len(sources) >= 4:
        axes.append("multi-source")

    ordered = core + axes + [topic.strip().lower()] + sources
    seen: set[str] = set()
    out = [t for t in ordered if t and not (t in seen or seen.add(t))]
    return out[:24]  # Tumblr's per-post ceiling is ~30; keep it generous but bounded


def build_caption(topic, collage, density, experiment=None, meta_topics=(), image_path=None) -> tuple[str, list[str]]:
    caption = f'"{topic}"\n{lab_line(topic, collage, density)}'
    return caption, build_tags(topic, collage, density, experiment, meta_topics, image_path)
