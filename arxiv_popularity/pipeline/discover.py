from __future__ import annotations

import logging
from datetime import datetime, timezone

from arxiv_popularity.models import Paper
from arxiv_popularity.providers.arxiv import fetch_arxiv_papers
from arxiv_popularity.providers.huggingface import fetch_hf_trending_ids, get_hf_titles

logger = logging.getLogger("arxiv_popularity.pipeline.discover")


def _make_stub_paper(arxiv_id: str) -> Paper:
    """Create a minimal Paper when arXiv metadata is unavailable."""
    return Paper(
        arxiv_id=arxiv_id,
        title=f"arXiv:{arxiv_id}",
        authors=[],
        abstract="",
        categories=[],
        published=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
    )


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
        fetched_ids = {p.arxiv_id for p in fetched}
        for paper in fetched:
            if paper.arxiv_id not in seen:
                seen[paper.arxiv_id] = paper
        # For any HF papers we couldn't fetch from arXiv, create stubs with HF titles
        still_missing = [hf_id for hf_id in missing_hf_ids if hf_id not in seen and hf_id not in fetched_ids]
        if still_missing:
            hf_titles = get_hf_titles()
            for hf_id in still_missing:
                logger.debug("Creating stub for HF paper %s (arXiv unavailable)", hf_id)
                stub = _make_stub_paper(hf_id)
                if hf_id in hf_titles:
                    stub.title = hf_titles[hf_id]
                seen[hf_id] = stub

    for rank, hf_id in enumerate(hf_ids, 1):
        if hf_id in seen:
            seen[hf_id].hf_trending = True
            seen[hf_id].hf_trending_rank = rank

    trending_count = sum(1 for p in seen.values() if p.hf_trending)
    logger.info("Discovery complete: %d papers (%d HF trending)", len(seen), trending_count)

    return list(seen.values())
