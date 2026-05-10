Enter a topic. 
<img width="3454" height="1936" alt="image" src="https://github.com/user-attachments/assets/0b5a228b-2fc0-45bf-8007-8b0a4eed1295" />

Get a collage.



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
