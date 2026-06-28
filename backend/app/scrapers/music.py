from __future__ import annotations
import httpx

_MB_HEADERS = {"User-Agent": "ephemera/1.0 (toy project; +https://github.com/nazanindev/ephemera)"}


def scrape_music(topic: str) -> list[dict]:
    results: list[dict] = []
    results.extend(_fetch_musicbrainz(topic))
    results.extend(_fetch_lyrics(topic))
    return results


def _fetch_musicbrainz(topic: str) -> list[dict]:
    results: list[dict] = []

    # Artists
    try:
        resp = httpx.get(
            "https://musicbrainz.org/ws/2/artist",
            params={"query": topic, "limit": 3, "fmt": "json"},
            timeout=8,
            headers=_MB_HEADERS,
        )
        for artist in resp.json().get("artists", [])[:2]:
            name = artist.get("name", "")
            if not name:
                continue
            begin = (artist.get("life-span") or {}).get("begin", "")
            year = begin[:4] if begin else ""
            aid = artist.get("id", "")
            results.append({
                "title": name,
                "snippet": "",
                "url": f"https://musicbrainz.org/artist/{aid}",
                "domain": "musicbrainz.org",
                "og": {"site_name": "MusicBrainz", "published_time": year},
            })
            for tag in _good_tags(artist.get("tags") or []):
                results.append({
                    "title": "",
                    "snippet": "",
                    "url": f"https://musicbrainz.org/artist/{aid}",
                    "domain": "musicbrainz.org",
                    "og": {"site_name": tag},
                })
    except Exception:
        pass

    # Songs / recordings
    try:
        resp = httpx.get(
            "https://musicbrainz.org/ws/2/recording",
            params={"query": topic, "limit": 8, "fmt": "json"},
            timeout=8,
            headers=_MB_HEADERS,
        )
        seen: set[str] = set()
        for rec in resp.json().get("recordings", [])[:6]:
            title = rec.get("title", "")
            if not title or title in seen:
                continue
            seen.add(title)
            date = (rec.get("first-release-date") or "")[:4]
            credits = rec.get("artist-credit", [])
            artist_name = credits[0].get("artist", {}).get("name", "") if credits else ""
            results.append({
                "title": title,
                "snippet": artist_name,
                "url": f"https://musicbrainz.org/recording/{rec.get('id', '')}",
                "domain": "musicbrainz.org",
                "og": {"site_name": "MusicBrainz", "published_time": date},
            })
    except Exception:
        pass

    return results


def _fetch_lyrics(topic: str) -> list[dict]:
    try:
        resp = httpx.get(
            f"https://api.lyrics.ovh/suggest/{topic}",
            timeout=8,
        )
        tracks = resp.json().get("data", [])[:5]
        results = []
        for track in tracks:
            if len(results) >= 1:
                break
            artist = track.get("artist", {}).get("name", "")
            title = track.get("title", "")
            if not artist or not title:
                continue
            # Only use tracks where topic appears in artist name or song title
            if topic.lower() not in artist.lower() and topic.lower() not in title.lower():
                continue
            try:
                lr = httpx.get(
                    f"https://api.lyrics.ovh/v1/{artist}/{title}",
                    timeout=8,
                )
                lyrics = lr.json().get("lyrics", "")
                if lyrics:
                    snippet = _lyric_fragment(lyrics)
                    if snippet:
                        results.append({
                            "title": "",
                            "snippet": snippet,
                            "url": "",
                            "domain": "lyrics.ovh",
                            "og": {"site_name": f"{artist} — {title}"},
                        })
            except Exception:
                pass
        return results
    except Exception:
        return []


_NOISE_TAGS = {
    "united states", "united kingdom", "the netherlands", "australia",
    "canada", "germany", "france", "sweden", "norway", "ireland",
    "english", "american", "british", "australian", "european",
    "male vocalists", "female vocalists", "seen live", "favorites",
    "all", "albums i own",
}


def _good_tags(tags: list[dict]) -> list[str]:
    out = []
    for t in tags:
        name = t.get("name", "").strip().lower()
        if name and name not in _NOISE_TAGS and 3 < len(name) <= 30:
            out.append(name)
        if len(out) >= 3:
            break
    return out


def _lyric_fragment(lyrics: str) -> str:
    lines = [l.strip() for l in lyrics.splitlines() if l.strip()]
    good = [l for l in lines if 25 <= len(l) <= 90]
    if not good:
        return ""
    mid = len(good) // 2
    return "\n".join(good[mid:mid + 2])
