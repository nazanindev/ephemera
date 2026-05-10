Enter a topic
<img width="3454" height="1936" alt="image" src="https://github.com/user-attachments/assets/0b5a228b-2fc0-45bf-8007-8b0a4eed1295" />

Get a collage



## Architecture

User types a prompt, triggers a new job, workers scrape for prompt topics, frontend compiles the collage.

<img width="2054" height="752" alt="image" src="https://github.com/user-attachments/assets/171d1d3c-ed34-4d3c-8c26-63c0252aa616" />

**Stack**

- Nginx
- FastAPI
- Celery (scrapers)
- Redis
- Main Sources: Openverse · Wikipedia · HackerNews · Reddit · Wayback Machine
