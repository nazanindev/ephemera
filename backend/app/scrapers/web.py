from __future__ import annotations
import re
import httpx
from urllib.parse import urlparse

_SKIP_DOMAINS = {
    "en.wikipedia.org", "wikipedia.org", "en.wikiquote.org",
    "commons.wikimedia.org", "wikimedia.org",
    "reddit.com", "old.reddit.com",
    "youtube.com", "youtu.be",
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "amazon.com", "archive.org",
}

_BOILERPLATE = re.compile(
    r"(cookie|subscribe|©|all rights reserved|click here|sign up|log in|"
    r"privacy policy|terms of use|newsletter|advertisement|follow us|"
    r"read more|share this|loading\.\.\.|enable javascript)",
    re.IGNORECASE,
)

_NOISE_TAGS = {"nav", "header", "footer", "aside", "form", "script",
               "style", "button", "figcaption", "label", "noscript"}

_CLAUSE_SPLIT = re.compile(r"(?<=[,;])\s+|(?<=\s)—\s+|(?<=\s)–\s+")
_LEADING_CONJUNCTIONS = re.compile(
    r"^(and |but |or |so |because |which |that |who |as |if |when |while |though )",
    re.IGNORECASE,
)


def _extract_phrases(text: str) -> list[str]:
    """Split a paragraph into short clause-level fragments (the 'torn paper' effect)."""
    if len(text) < 80:
        return []
    clauses = _CLAUSE_SPLIT.split(text)
    phrases = []
    for clause in clauses:
        clause = clause.strip().rstrip(",;")
        if _LEADING_CONJUNCTIONS.match(clause):
            continue
        words = clause.split()
        if len(words) < 3:
            continue
        if len(clause) < 15 or len(clause) > 90:
            continue
        phrases.append(clause)
    return phrases[:2]


def scrape_web_bodies(topic: str, max_pages: int = 3, max_per_page: int = 3) -> list[dict]:
    try:
        from duckduckgo_search import DDGS
        search_results = list(DDGS(timeout=8).text(topic, max_results=10))
    except Exception:
        return []

    candidates = []
    for r in search_results:
        url = r.get("href", "")
        if not url:
            continue
        domain = urlparse(url).netloc.lower().lstrip("www.")
        if any(skip in domain for skip in _SKIP_DOMAINS):
            continue
        candidates.append((url, domain, r.get("title", "")))

    results = []
    for url, domain, search_title in candidates:
        if len(results) >= max_pages:
            break
        page = _fetch_page_text(url, domain, search_title, max_per_page)
        if page:
            results.append(page)

    return results


def _fetch_page_text(url: str, domain: str, search_title: str, max_paragraphs: int) -> dict | None:
    try:
        from bs4 import BeautifulSoup

        resp = httpx.get(
            url,
            timeout=5,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; ephemera/1.0)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        if resp.status_code != 200:
            return None
        if "text/html" not in resp.headers.get("content-type", ""):
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        for tag in soup.find_all(_NOISE_TAGS):
            tag.decompose()

        h1 = soup.find("h1")
        title = h1.get_text(strip=True)[:120] if h1 else ""

        good_paras = []
        for p in soup.find_all("p"):
            text = re.sub(r"\s+", " ", p.get_text(separator=" ", strip=True))
            if len(text) < 40 or len(text) > 320:
                continue
            if _BOILERPLATE.search(text):
                continue
            good_paras.append(text)
            if len(good_paras) >= max_paragraphs:
                break

        if not good_paras:
            return None

        extra = list(good_paras[1:])
        for para in good_paras:
            extra.extend(_extract_phrases(para))

        return {
            "title": title,
            "snippet": good_paras[0],
            "url": url,
            "domain": domain,
            "og": {"site_name": domain},
            "extra_snippets": extra,
        }
    except Exception:
        return None
