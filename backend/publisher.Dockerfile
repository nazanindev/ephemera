# Daily auto-walk, run as a Railway cron service (schedule lives in the service's
# settings: deploy.cronSchedule). The base image ships Chromium + its system deps for
# exactly this Playwright version — bump the tag together with playwright in
# app/publisher/requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

WORKDIR /app

COPY app/publisher/requirements.txt publisher-requirements.txt
RUN pip install --no-cache-dir -r publisher-requirements.txt

COPY . .

ENV PYTHONPATH=/app PYTHONUNBUFFERED=1

CMD ["sh", "app/publisher/cron.sh"]
