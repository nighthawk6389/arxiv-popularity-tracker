from __future__ import annotations

import logging
import time

from arxiv_popularity.models import Paper
from arxiv_popularity.utils import fetch_with_retry

logger = logging.getLogger("arxiv_popularity.pipeline.share")

DEFAULT_BASE_URL = "https://www.deconstructedpapers.com"
DELAY_BETWEEN_PAPERS_SECONDS = 60


def _share_paper(paper: Paper, base_url: str, api_key: str) -> None:
    """Call the auto-share API for a single paper and set its share_url."""
    try:
        resp = fetch_with_retry(
            f"{base_url}/api/papers/auto-share",
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={"url": paper.arxiv_url},
            timeout=300,
            max_retries=3,
            backoff=2.0,
        )
        data = resp.json()
        if "url" in data:
            paper.share_url = f"{base_url}{data['url']}"
            cached = " (cached)" if data.get("cached") else ""
            logger.info("Shared %s -> %s%s", paper.arxiv_id, paper.share_url, cached)
        else:
            logger.warning("No URL in share response for %s: %s", paper.arxiv_id, data)
    except Exception:
        logger.warning("Failed to share %s", paper.arxiv_id, exc_info=True)


def share_papers(papers: list[Paper], config: dict, top_n: int) -> list[Paper]:
    """Share the top N papers via deconstructedpapers.com and set share_url on each."""
    api_key = config.get("dp_api_key")
    if not api_key:
        logger.warning("DP_API_KEY not set, skipping share stage")
        return papers

    base_url = config.get("dp_base_url", DEFAULT_BASE_URL)
    top = papers[:top_n]
    logger.info("Sharing %d papers via %s", len(top), base_url)

    for idx, paper in enumerate(top):
        if idx > 0:
            logger.info("Sleeping %ds before next share request", DELAY_BETWEEN_PAPERS_SECONDS)
            time.sleep(DELAY_BETWEEN_PAPERS_SECONDS)
        _share_paper(paper, base_url, api_key)

    shared = sum(1 for p in top if p.share_url)
    logger.info("Shared %d/%d papers successfully", shared, len(top))
    return papers
