from __future__ import annotations
import httpx
from urllib.parse import urlparse

CDX_BASE = "http://web.archive.org/cdx/search/cdx"
WAYBACK_BASE = "https://web.archive.org/web"


def scrape_archive(topic: str, limit: int = 12) -> list[dict]:
    results: list[dict] = []

    # Look up archived snapshots of the Wikipedia article for this topic —
    # guaranteed to exist for most topics, gives good historical texture.
    wiki_slug = topic.strip().replace(" ", "_")
    wiki_url = f"en.wikipedia.org/wiki/{wiki_slug}"
    results.extend(_snapshots_for_url(wiki_url, count=4))

    # Broad keyword search — only if Wikipedia gave nothing
    if len(results) < 2:
        results.extend(_pattern_search(topic, count=limit - len(results)))

    seen_domains: dict[str, int] = {}
    deduped = []
    for r in results:
        d = r["domain"]
        if seen_domains.get(d, 0) < 2:
            seen_domains[d] = seen_domains.get(d, 0) + 1
            deduped.append(r)
        if len(deduped) >= limit:
            break

    return deduped


def _snapshots_for_url(url: str, count: int = 5, is_pattern: bool = False) -> list[dict]:
    params = {
        "url": url if is_pattern else url,
        "output": "json",
        "limit": str(count * 3),
        "fl": "timestamp,original,statuscode",
        "filter": "statuscode:200",
        "collapse": "timestamp:6",  # one per month
    }
    if not is_pattern:
        params["matchType"] = "prefix"

    try:
        resp = httpx.get(CDX_BASE, params=params, timeout=6)
        if resp.status_code != 200:
            return []
        rows = resp.json()
        if not rows or len(rows) < 2:
            return []
        keys = rows[0]
        records = [dict(zip(keys, row)) for row in rows[1:count + 1]]
        return [_to_snapshot(r) for r in records]
    except Exception:
        return []


def _pattern_search(topic: str, count: int = 5) -> list[dict]:
    query = topic.replace(" ", "-").replace(",", "").lower()
    params = {
        "url": f"*{query}*",
        "output": "json",
        "limit": str(count * 2),
        "fl": "timestamp,original,statuscode",
        "filter": "statuscode:200",
        "collapse": "urlkey",
    }
    try:
        resp = httpx.get(CDX_BASE, params=params, timeout=6)
        if resp.status_code != 200:
            return []
        rows = resp.json()
        if not rows or len(rows) < 2:
            return []
        keys = rows[0]
        return [_to_snapshot(dict(zip(keys, row))) for row in rows[1:count + 1]]
    except Exception:
        return []


def _to_snapshot(record: dict) -> dict:
    ts = record.get("timestamp", "")
    original = record.get("original", "")
    return {
        "thumbnail_url": f"{WAYBACK_BASE}/{ts}im_/{original}",
        "wayback_url": f"{WAYBACK_BASE}/{ts}/{original}",
        "original_url": original,
        "domain": urlparse(original).netloc,
        "timestamp": ts,
        "year": ts[:4],
    }
