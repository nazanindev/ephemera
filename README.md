Enter a topic
<img width="2410" height="1092" alt="image" src="https://github.com/user-attachments/assets/1fa2fb05-0565-47d6-8816-1c3d0387d511" />

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
