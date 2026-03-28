from __future__ import annotations

import logging
import os

from arxiv_popularity.models import Paper

logger = logging.getLogger("arxiv_popularity.providers.reddit")


def enrich(papers: list[Paper], **kwargs) -> list[Paper]:
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.info("Reddit provider not configured (set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET) — skipping")
    else:
        logger.info("Reddit provider not yet implemented — skipping")
    return papers
