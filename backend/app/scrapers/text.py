from __future__ import annotations
import httpx
from urllib.parse import urlparse


def scrape_text(topic: str, max_results: int = 40) -> list[dict]:
    results: list[dict] = []
    results.extend(_fetch_wikipedia(topic))
    results.extend(_fetch_hackernews(topic))
    results.extend(_fetch_reddit(topic))
    return results[:max_results]


def _fetch_wikipedia(topic: str) -> list[dict]:
    try:
        resp = httpx.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": topic,
                "format": "json",
                "srlimit": 15,
                "utf8": 1,
            },
            timeout=8,
            headers={"User-Agent": "Scrapbook/1.0"},
        )
        items = resp.json().get("query", {}).get("search", [])
        results = []
        for item in items:
            title = item.get("title", "")
            snippet = (item.get("snippet", "")
                       .replace('<span class="searchmatch">', "")
                       .replace("</span>", ""))
            url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
            results.append({
                "title": title,
                "snippet": snippet,
                "url": url,
                "domain": "en.wikipedia.org",
                "og": {"site_name": "Wikipedia"},
            })
        return results
    except Exception:
        return []


def _fetch_hackernews(topic: str) -> list[dict]:
    try:
        resp = httpx.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": topic, "tags": "story", "hitsPerPage": 20},
            timeout=8,
        )
        results = []
        for hit in resp.json().get("hits", []):
            title = hit.get("title", "")
            if not title:
                continue
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            created = (hit.get("created_at") or "")[:10]
            results.append({
                "title": title,
                "snippet": "",
                "url": url,
                "domain": urlparse(url).netloc,
                "og": {"site_name": "Hacker News", "published_time": created},
            })
        return results
    except Exception:
        return []


def _fetch_reddit(topic: str) -> list[dict]:
    try:
        resp = httpx.get(
            "https://www.reddit.com/search.json",
            params={"q": topic, "sort": "top", "limit": 15, "t": "year"},
            timeout=8,
            headers={"User-Agent": "Scrapbook/1.0"},
        )
        results = []
        for child in resp.json().get("data", {}).get("children", []):
            d = child.get("data", {})
            title = d.get("title", "")
            url = d.get("url", "")
            domain = d.get("domain", urlparse(url).netloc)
            created = str(d.get("created_utc", ""))[:10]
            subreddit = d.get("subreddit_name_prefixed", "")
            results.append({
                "title": title,
                "snippet": d.get("selftext", "")[:200],
                "url": url,
                "domain": domain,
                "og": {"site_name": subreddit or "Reddit", "published_time": created},
            })
        return results
    except Exception:
        return []
