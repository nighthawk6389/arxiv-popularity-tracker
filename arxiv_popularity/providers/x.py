from __future__ import annotations

import logging

from arxiv_popularity.models import Paper

logger = logging.getLogger("arxiv_popularity.providers.x")


def enrich(papers: list[Paper], **kwargs) -> list[Paper]:
    logger.info("X (Twitter) provider not implemented — skipping")
    return papers
