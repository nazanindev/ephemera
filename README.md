# ScrapeBook

Enter a topic. Get a collage.

ScrapeBook scrapes real web material — images, headlines, archive fragments, metadata — and composes them into a single-page abstract collage. The aesthetic is internet archive culture, Tumblr-era edits, and digital zines. Mood over clarity. Texture over polish.

## how it works

1. You enter a topic or phrase
2. The backend scrapes in parallel: [Openverse](https://openverse.org) for images, Wikipedia + HackerNews + Reddit for text, and the [Wayback Machine CDX API](https://archive.org/help/wayback_api.php) for archived fragments
3. Fragments are ranked, deduped, and filtered
4. A seeded layout engine places everything on a 1800×1200 canvas using composition rules — zone coverage, aggressive scale variation, deliberate overlaps
5. Same topic always produces the same collage

## stack

- **Backend:** Python + FastAPI + Celery + Redis
- **Frontend:** Vanilla JS + CSS — no framework, no build step
- **Infra:** Docker Compose

## run it

```bash
docker compose up --build
```

Open `http://localhost:3000`.

## notes

- Scraping takes 15–30s on first run; results are cached for 1 hour
- The collage canvas is 1800×1200 — scroll or zoom out to see the full thing
- For social media: screenshot at full canvas size
