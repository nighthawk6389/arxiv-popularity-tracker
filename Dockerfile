FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir requests feedparser

COPY arxiv_popularity/ arxiv_popularity/
COPY scripts/ scripts/
RUN chmod +x scripts/generate_daily.sh

ENTRYPOINT ["scripts/generate_daily.sh"]
