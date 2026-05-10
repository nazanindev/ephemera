from __future__ import annotations


def scrape_ddg_images(topic: str, max_results: int = 2) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().images(topic, max_results=max_results, safesearch="moderate"))
        out = []
        for r in results:
            url = r.get("image", "")
            if url and url.startswith("http") and not url.lower().endswith(".svg"):
                out.append({
                    "url": url,
                    "source_url": r.get("url", ""),
                })
        return out[:max_results]
    except Exception:
        return []
