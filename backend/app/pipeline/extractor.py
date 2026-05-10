from __future__ import annotations
from urllib.parse import urlparse
from app.models import Fragment, FragmentType


def extract_fragments(
    images: list[dict],
    texts: list[dict],
    archive: list[dict],
) -> list[Fragment]:
    fragments: list[Fragment] = []

    for img in images:
        fragments.append(Fragment(
            type=FragmentType.image,
            content=img["url"],
            source_url=img.get("source_url", ""),
            source_domain=urlparse(img.get("source_url", "")).netloc,
        ))

    for item in texts:
        domain = item.get("domain", urlparse(item.get("url", "")).netloc)
        og = item.get("og", {})

        if item.get("title"):
            fragments.append(Fragment(
                type=FragmentType.headline,
                content=item["title"],
                source_url=item.get("url", ""),
                source_domain=domain,
                og=og,
            ))

        if item.get("snippet"):
            fragments.append(Fragment(
                type=FragmentType.snippet,
                content=item["snippet"],
                source_url=item.get("url", ""),
                source_domain=domain,
                og=og,
            ))

        # Surface metadata as visible artifact fragments — skip generic aggregator names
        _GENERIC_SITES = {"wikipedia", "hacker news", "hackernews", "reddit", "youtube"}
        site_name = og.get("site_name", "")
        if site_name and site_name.lower() not in _GENERIC_SITES and len(site_name) > 3:
            fragments.append(Fragment(
                type=FragmentType.metadata,
                content=site_name,
                source_url=item.get("url", ""),
                source_domain=domain,
            ))

        pub = og.get("published_time", "")
        if pub and len(pub) >= 10:
            # Format as a timestamp artifact: "2001 · example.com"
            year = pub[:4]
            fragments.append(Fragment(
                type=FragmentType.metadata,
                content=f"{year} · {domain}" if domain else year,
                source_url=item.get("url", ""),
                source_domain=domain,
            ))

        desc = og.get("description", "")
        if desc and len(desc) > 60:
            fragments.append(Fragment(
                type=FragmentType.snippet,
                content=desc[:280],
                source_url=item.get("url", ""),
                source_domain=domain,
            ))

    for snap in archive:
        fragments.append(Fragment(
            type=FragmentType.archive_screenshot,
            content=snap["thumbnail_url"],
            source_url=snap["wayback_url"],
            source_domain=snap["domain"],
            captured_at=snap["timestamp"],
            og={
                "year": snap["year"],
                "original_url": snap["original_url"],
            },
        ))
        # Also surface raw URL + year as a metadata atom
        fragments.append(Fragment(
            type=FragmentType.metadata,
            content=f"{snap['year']} — {snap['domain']}",
            source_url=snap["wayback_url"],
            source_domain=snap["domain"],
            captured_at=snap["timestamp"],
        ))

    return fragments
