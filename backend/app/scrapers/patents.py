from __future__ import annotations
import json
import re
import httpx


def scrape_patents(topic: str, max_results: int = 5) -> list[dict]:
    try:
        resp = httpx.get(
            "https://search.patentsview.org/api/v1/patent/",
            params={
                "q": json.dumps({"_or": [
                    {"_text_any": {"patent_abstract": topic}},
                    {"_text_any": {"patent_title": topic}},
                ]}),
                "f": json.dumps(["patent_id", "patent_title", "patent_abstract", "patent_date"]),
                "o": json.dumps({"size": max_results}),
            },
            timeout=10,
            headers={"User-Agent": "Scrapebook/1.0"},
        )
        patents = resp.json().get("patents") or []
        results = []
        for p in patents:
            title = (p.get("patent_title") or "").strip()
            abstract = (p.get("patent_abstract") or "").strip()
            date = (p.get("patent_date") or "")[:4]
            patent_id = p.get("patent_id") or ""
            if not title and not abstract:
                continue
            snippet = _first_sentences(abstract, 2) if abstract else ""
            results.append({
                "title": title,
                "snippet": snippet[:300],
                "url": f"https://patents.google.com/patent/US{patent_id}",
                "domain": "patents.google.com",
                "og": {"site_name": "Patent", "published_time": date},
            })
        return results
    except Exception:
        return []


def _first_sentences(text: str, n: int) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return " ".join(sentences[:n])
