from __future__ import annotations
import httpx
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

_HEADERS = {"User-Agent": "Scrapebook/1.0 (toy project)"}
_BAD_MIMES = {"image/svg+xml", "image/tiff", "image/x-xcf"}
_MIN_DIM = 200


def scrape_wikimedia(topic: str, max_results: int = 20) -> list[dict]:
    results = _search(topic)
    if len(results) < 5:
        # Broaden: drop the last word for tangential coverage
        words = topic.strip().split()
        if len(words) > 1:
            broader = " ".join(words[:-1])
            seen = {r["url"] for r in results}
            for r in _search(broader):
                if r["url"] not in seen:
                    results.append(r)
    return results[:max_results]


def _search(query: str) -> list[dict]:
    try:
        resp = httpx.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": query,
                "gsrnamespace": 6,
                "gsrlimit": 20,
                "prop": "imageinfo",
                # thumburl avoids the CDN hotlink block that rejects the full-res url
                "iiprop": "url|size|mime|thumburl",
                "iiurlwidth": 800,
                "format": "json",
            },
            headers=_HEADERS,
            timeout=10,
        )
        pages = resp.json().get("query", {}).get("pages", {})
        results = []
        for page in pages.values():
            ii = (page.get("imageinfo") or [{}])[0]
            mime = ii.get("mime", "")
            if mime in _BAD_MIMES or not mime.startswith("image/"):
                continue
            w = ii.get("width", 0)
            h = ii.get("height", 0)
            if w < _MIN_DIM or h < _MIN_DIM:
                continue
            # Prefer thumburl — served from /thumb/ CDN path
            url = _strip_utm(ii.get("thumburl") or ii.get("url", ""))
            if not url:
                continue
            thumb_w = ii.get("thumbwidth") or min(w, 800)
            thumb_h = ii.get("thumbheight") or int(h * thumb_w / w) if w else h
            title = page.get("title", "").removeprefix("File:")
            source_url = f"https://commons.wikimedia.org/wiki/{page.get('title', '').replace(' ', '_')}"
            results.append({
                "url": url,
                "source_url": source_url,
                "title": title,
                "width": thumb_w,
                "height": thumb_h,
            })
        return results
    except Exception:
        return []


def _strip_utm(url: str) -> str:
    if not url:
        return url
    parts = urlparse(url)
    qs = {k: v for k, v in parse_qs(parts.query).items() if not k.startswith("utm_")}
    clean_query = urlencode(qs, doseq=True)
    return urlunparse(parts._replace(query=clean_query))
