from __future__ import annotations
import hashlib
import httpx
from app.models import Fragment, FragmentType

# Max fragments per type in final collage
TYPE_CAPS = {
    FragmentType.image: 20,
    FragmentType.headline: 10,
    FragmentType.snippet: 8,
    FragmentType.metadata: 6,
    FragmentType.archive_screenshot: 6,
}

# Max fragments from a single domain
DOMAIN_CAP = 4


def rank_and_filter(fragments: list[Fragment]) -> list[Fragment]:
    fragments = _dedup(fragments)
    fragments = _check_image_links(fragments)
    fragments = _apply_domain_cap(fragments)
    fragments = _apply_type_caps(fragments)
    return fragments


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


def _check_image_links(fragments: list[Fragment]) -> list[Fragment]:
    image_types = {FragmentType.image, FragmentType.archive_screenshot}
    to_check = [f for f in fragments if f.type in image_types]
    others = [f for f in fragments if f.type not in image_types]

    valid = []
    with httpx.Client(timeout=5, follow_redirects=True) as client:
        for f in to_check:
            try:
                resp = client.head(f.content)
                if resp.status_code < 400:
                    valid.append(f)
                    continue
                # Some CDNs reject HEAD — fall back to a range GET
                resp = client.get(f.content, headers={"Range": "bytes=0-0"})
                if resp.status_code < 400 or resp.status_code == 416:
                    valid.append(f)
            except Exception:
                pass

    return valid + others


def _apply_domain_cap(fragments: list[Fragment]) -> list[Fragment]:
    domain_counts: dict[str, int] = {}
    out = []
    for f in fragments:
        d = f.source_domain
        count = domain_counts.get(d, 0)
        if not d or count < DOMAIN_CAP:
            domain_counts[d] = count + 1
            out.append(f)
    return out


def _apply_type_caps(fragments: list[Fragment]) -> list[Fragment]:
    type_counts: dict[FragmentType, int] = {}
    out = []
    for f in fragments:
        # Drop noise: very short text fragments
        if f.type in (FragmentType.metadata, FragmentType.headline, FragmentType.snippet):
            if len(f.content.strip()) < 6:
                continue
        cap = TYPE_CAPS.get(f.type, 999)
        count = type_counts.get(f.type, 0)
        if count < cap:
            type_counts[f.type] = count + 1
            out.append(f)
    return out
