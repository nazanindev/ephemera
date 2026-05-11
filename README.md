#### Enter anything

<img width="2278" height="754" alt="image" src="https://github.com/user-attachments/assets/19aab908-4c9b-4e91-9f7c-5532802ae5dd" />

#### Get a collage

<img width="3428" height="1910" alt="image" src="https://github.com/user-attachments/assets/79ba941c-f1c0-41e8-87b3-7cb290f6e562" />

####

#### Ambiguous queries drift across domains

<img width="1974" height="554" alt="image" src="https://github.com/user-attachments/assets/f288116f-57ee-42c8-9212-24e58e9f33a7" />

####

<img width="3450" height="1938" alt="image" src="https://github.com/user-attachments/assets/a8790cf2-c2ff-4ead-97db-a07702fb6c7e" />


## Architecture

Frontend submits a crawl job. Distributed workers scrape topic-related content. Frontend composes the collage.

<img width="2054" height="752" alt="image" src="https://github.com/user-attachments/assets/171d1d3c-ed34-4d3c-8c26-63c0252aa616" />

#### Stack

- Nginx
- FastAPI
- Celery workers
- Redis

**Sources**

Initial: Openverse · Wikipedia · Hacker News · Reddit · Wayback Machine · DuckDuckGo

Enriched: Wikimedia · Wikiquote · Internet Archive · MusicBrainz · patents
