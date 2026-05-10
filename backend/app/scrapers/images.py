from __future__ import annotations
import httpx

OPENVERSE_URL = "https://api.openverse.org/v1/images/"


def scrape_images(topic: str, max_results: int = 40) -> list[dict]:
    query = topic.replace(",", " ")  # commas break Openverse search
    results = []
    for page in (1, 2):
        if len(results) >= max_results:
            break
        try:
            resp = httpx.get(
                OPENVERSE_URL,
                params={"q": query, "page_size": 20, "page": page},
                timeout=12,
                headers={"User-Agent": "Scrapbook/1.0 (toy project; contact: scrapbook@example.com)"},
            )
            if resp.status_code != 200:
                break
            for item in resp.json().get("results", []):
                url = item.get("url", "")
                if not url or url.lower().endswith(".svg"):
                    continue
                w = item.get("width") or 0
                h = item.get("height") or 0
                if w and h and (w < 100 or h < 100):
                    continue
                results.append({
                    "url": url,
                    "source_url": item.get("foreign_landing_url", ""),
                    "title": item.get("title", ""),
                    "width": w,
                    "height": h,
                })
        except Exception:
            break
    return results[:max_results]
