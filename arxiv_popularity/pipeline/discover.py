from __future__ import annotations

import logging

from arxiv_popularity.models import Paper
from arxiv_popularity.providers.arxiv import fetch_arxiv_papers
from arxiv_popularity.providers.huggingface import fetch_hf_trending_ids

logger = logging.getLogger("arxiv_popularity.pipeline.discover")


def discover(categories: list[str], window_days: int, limit: int) -> list[Paper]:
    logger.info("Starting discovery: categories=%s, window=%dd, limit=%d", categories, window_days, limit)

    papers = fetch_arxiv_papers(categories, window_days, limit)

    # Deduplicate by arxiv_id
    seen: dict[str, Paper] = {}
    for p in papers:
        if p.arxiv_id not in seen:
            seen[p.arxiv_id] = p

    # Mark HuggingFace trending and fetch missing HF papers
    hf_ids = fetch_hf_trending_ids()
    missing_hf_ids = [hf_id for hf_id in hf_ids if hf_id not in seen]
    if missing_hf_ids:
        logger.info("Fetching %d HF trending papers not in arXiv results", len(missing_hf_ids))
        from arxiv_popularity.providers.arxiv import fetch_papers_by_ids
        fetched = fetch_papers_by_ids(missing_hf_ids)
        for paper in fetched:
            if paper.arxiv_id not in seen:
                seen[paper.arxiv_id] = paper

    for rank, hf_id in enumerate(hf_ids, 1):
        if hf_id in seen:
            seen[hf_id].hf_trending = True
            seen[hf_id].hf_trending_rank = rank

    trending_count = sum(1 for p in seen.values() if p.hf_trending)
    logger.info("Discovery complete: %d papers (%d HF trending)", len(seen), trending_count)

    return list(seen.values())
