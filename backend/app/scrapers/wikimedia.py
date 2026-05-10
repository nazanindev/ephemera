from __future__ import annotations
import httpx

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
                "iiprop": "url|size|mime",
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
            url = ii.get("url", "")
            if not url:
                continue
            title = page.get("title", "").removeprefix("File:")
            source_url = f"https://commons.wikimedia.org/wiki/{page.get('title', '').replace(' ', '_')}"
            results.append({
                "url": url,
                "source_url": source_url,
                "title": title,
                "width": w,
                "height": h,
            })
        return results
    except Exception:
        return []
