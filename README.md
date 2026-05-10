# ScrapeBook

Enter a topic. Get a collage.

ScrapeBook scrapes real web material — images, headlines, archive fragments, and metadata — from Openverse, Wikipedia, HackerNews, Reddit, and the Wayback Machine, then composes everything into a single-page abstract collage. The same topic always produces the same result.

## Screenshots

<!-- add screenshots here -->

## Architecture

```
Browser → Nginx (frontend :3000)
              ↓ REST
          FastAPI (api :8000) ←→ Redis (broker + cache)
              ↓ tasks
          Celery worker (×4)
              ↓ scrapes
          Openverse · Wikipedia · HackerNews · Reddit · Wayback Machine
```
