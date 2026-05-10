from __future__ import annotations
import hashlib
import httpx
from app.models import Fragment, FragmentType

IMAGE_DOMAIN_CAP = 18
TEXT_DOMAIN_CAP = 4

_SOURCE_ORDER = {"openverse": 0, "wikimedia": 1, "": 2}

_SPARSE_CAPS = {
    FragmentType.image: 14,
    FragmentType.headline: 8,
    FragmentType.snippet: 12,
    FragmentType.metadata: 3,
    FragmentType.archive_screenshot: 3,
}
_DENSE_CAPS = {
    FragmentType.image: 32,
    FragmentType.headline: 20,
    FragmentType.snippet: 26,
    FragmentType.metadata: 8,
    FragmentType.archive_screenshot: 8,
}


def _vibe_caps(vibe: float) -> dict:
    return {
        t: max(1, round(_SPARSE_CAPS[t] + (_DENSE_CAPS[t] - _SPARSE_CAPS[t]) * vibe))
        for t in FragmentType
    }


def rank_and_filter(fragments: list[Fragment], vibe: float = 0.5) -> list[Fragment]:
    caps = _vibe_caps(vibe)
    fragments = _dedup(fragments)
    fragments = _sort_images_by_source(fragments)
    fragments = _check_image_links(fragments)
    fragments = _apply_domain_cap(fragments)
    fragments = _apply_type_caps(fragments, caps)
    return fragments


def rank_and_filter_incremental(
    new_fragments: list[Fragment],
    existing_fragments: list[Fragment],
    vibe: float = 0.5,
) -> list[Fragment]:
    caps = _vibe_caps(vibe)
    existing_hashes = {_content_hash(f) for f in existing_fragments}
    existing_type_counts: dict[FragmentType, int] = {}
    existing_domain_counts: dict[str, int] = {}
    for f in existing_fragments:
        existing_type_counts[f.type] = existing_type_counts.get(f.type, 0) + 1
        if f.source_domain:
            existing_domain_counts[f.source_domain] = existing_domain_counts.get(f.source_domain, 0) + 1

    fresh = [f for f in new_fragments if _content_hash(f) not in existing_hashes]
    fresh = _dedup(fresh)
    fresh = _sort_images_by_source(fresh)
    fresh = _check_image_links(fresh, max_to_check=20)

    out = []
    domain_counts = dict(existing_domain_counts)
    type_counts = dict(existing_type_counts)
    for f in fresh:
        if f.type in (FragmentType.metadata, FragmentType.headline, FragmentType.snippet):
            if len(f.content.strip()) < 15:
                continue
        d = f.source_domain
        dcap = IMAGE_DOMAIN_CAP if f.type == FragmentType.image else TEXT_DOMAIN_CAP
        if d and domain_counts.get(d, 0) >= dcap:
            continue
        cap = caps.get(f.type, 999)
        if type_counts.get(f.type, 0) >= cap:
            continue
        domain_counts[d] = domain_counts.get(d, 0) + 1
        type_counts[f.type] = type_counts.get(f.type, 0) + 1
        out.append(f)
    return out


def _content_hash(f: Fragment) -> str:
    return hashlib.sha256(f.content.encode()).hexdigest()


def _dedup(fragments: list[Fragment]) -> list[Fragment]:
    seen: set[str] = set()
    out = []
    for f in fragments:
        h = _content_hash(f)
        if h not in seen:
            seen.add(h)
            out.append(f)
    return out


def _sort_images_by_source(fragments: list[Fragment]) -> list[Fragment]:
    images = [f for f in fragments if f.type == FragmentType.image]
    others = [f for f in fragments if f.type != FragmentType.image]
    images.sort(key=lambda f: _SOURCE_ORDER.get(f.image_source, 2))
    return images + others


def _check_image_links(fragments: list[Fragment], max_to_check: int = 35) -> list[Fragment]:
    image_types = {FragmentType.image, FragmentType.archive_screenshot}
    wikimedia = [f for f in fragments if f.type in image_types and f.image_source == "wikimedia"]
    to_check = [f for f in fragments if f.type in image_types and f.image_source != "wikimedia"]
    others = [f for f in fragments if f.type not in image_types]

    to_check_limited = to_check[:max_to_check]
    unchecked = to_check[max_to_check:]

    valid = []
    with httpx.Client(timeout=5, follow_redirects=True) as client:
        for f in to_check_limited:
            try:
                resp = client.head(f.content)
                if resp.status_code < 400:
                    valid.append(f)
                    continue
                resp = client.get(f.content, headers={"Range": "bytes=0-0"})
                if resp.status_code < 400 or resp.status_code == 416:
                    valid.append(f)
            except Exception:
                pass

    return valid + unchecked + wikimedia + others


def _apply_domain_cap(fragments: list[Fragment]) -> list[Fragment]:
    domain_counts: dict[str, int] = {}
    out = []
    for f in fragments:
        d = f.source_domain
        cap = IMAGE_DOMAIN_CAP if f.type == FragmentType.image else TEXT_DOMAIN_CAP
        count = domain_counts.get(d, 0)
        if not d or count < cap:
            domain_counts[d] = count + 1
            out.append(f)
    return out


def _apply_type_caps(fragments: list[Fragment], caps: dict) -> list[Fragment]:
    type_counts: dict[FragmentType, int] = {}
    out = []
    for f in fragments:
        if f.type in (FragmentType.metadata, FragmentType.headline, FragmentType.snippet):
            if len(f.content.strip()) < 15:
                continue
        cap = caps.get(f.type, 999)
        count = type_counts.get(f.type, 0)
        if count < cap:
            type_counts[f.type] = count + 1
            out.append(f)
    return out
