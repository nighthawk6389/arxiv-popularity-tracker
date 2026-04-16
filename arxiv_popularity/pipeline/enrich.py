from __future__ import annotations

import logging

from arxiv_popularity.models import Paper
from arxiv_popularity.providers import semantic_scholar, hackernews, reddit, x, github

logger = logging.getLogger("arxiv_popularity.pipeline.enrich")


def enrich_papers(papers: list[Paper], config: dict) -> list[Paper]:
    providers_config = config.get("providers", {})
    pool_size = config.get("thread_pool_size", 8)

    if providers_config.get("semantic_scholar", True):
        logger.info("Enriching with Semantic Scholar...")
        papers = semantic_scholar.enrich(papers, thread_pool_size=pool_size)

    if providers_config.get("hackernews", True):
        logger.info("Enriching with Hacker News...")
        papers = hackernews.enrich(papers, thread_pool_size=pool_size)

    if providers_config.get("github", True):
        logger.info("Enriching with GitHub stars...")
        papers = github.enrich(papers, thread_pool_size=pool_size)

    if providers_config.get("reddit", False):
        papers = reddit.enrich(papers)

    if providers_config.get("x", False):
        papers = x.enrich(papers)

    return papers
