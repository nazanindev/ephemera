from __future__ import annotations
import httpx
from app.scrapers._filters import is_violent
from app.scrapers.ddg import scrape_ddg_images

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
                headers={"User-Agent": "ephemera/1.0 (toy project; +https://github.com/nazanindev/ephemera)"},
            )
            if resp.status_code != 200:
                break
            for item in resp.json().get("results", []):
                url = item.get("url", "")
                if not url or url.lower().endswith(".svg"):
                    continue
                w = item.get("width") or 0
                h = item.get("height") or 0
                if w and h and (w < 300 or h < 300):
                    continue
                if is_violent(item.get("title", "")):
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
    results = results[:max_results]
    results += scrape_ddg_images(topic, max_results=2)
    return results
