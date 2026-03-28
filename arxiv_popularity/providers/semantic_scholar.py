from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from arxiv_popularity.models import Paper
from arxiv_popularity.utils import fetch_with_retry

logger = logging.getLogger("arxiv_popularity.providers.semantic_scholar")

S2_BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
S2_SINGLE_URL = "https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}"
S2_FIELDS = "paperId,citationCount,externalIds"


def _get_headers() -> dict:
    headers = {}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    return headers


def _enrich_single(paper: Paper) -> None:
    try:
        url = S2_SINGLE_URL.format(arxiv_id=paper.arxiv_id)
        resp = fetch_with_retry(url, headers=_get_headers(), params={"fields": S2_FIELDS})
        data = resp.json()
        paper.citation_count = data.get("citationCount")
        paper.semantic_scholar_id = data.get("paperId")
    except Exception:
        logger.warning("S2 individual lookup failed for %s", paper.arxiv_id, exc_info=True)


def _try_batch(papers: list[Paper]) -> bool:
    try:
        ids = [f"ArXiv:{p.arxiv_id}" for p in papers]
        resp = fetch_with_retry(
            S2_BATCH_URL,
            method="POST",
            headers=_get_headers(),
            json={"ids": ids},
            params={"fields": S2_FIELDS},
        )
        results = resp.json()

        id_to_paper = {p.arxiv_id: p for p in papers}
        for item in results:
            if item is None:
                continue
            ext_ids = item.get("externalIds", {})
            arxiv_id = ext_ids.get("ArXiv")
            if arxiv_id and arxiv_id in id_to_paper:
                p = id_to_paper[arxiv_id]
                p.citation_count = item.get("citationCount")
                p.semantic_scholar_id = item.get("paperId")
        return True
    except Exception:
        logger.warning("S2 batch request failed, falling back to individual lookups", exc_info=True)
        return False


def enrich(papers: list[Paper], thread_pool_size: int = 8) -> list[Paper]:
    if not papers:
        return papers

    # Try batch first (up to 500 per request)
    for i in range(0, len(papers), 500):
        batch = papers[i:i + 500]
        if not _try_batch(batch):
            # Fallback: individual lookups with thread pool
            unenriched = [p for p in batch if p.citation_count is None]
            with ThreadPoolExecutor(max_workers=thread_pool_size) as executor:
                futures = {executor.submit(_enrich_single, p): p for p in unenriched}
                for future in as_completed(futures):
                    future.result()

    enriched = sum(1 for p in papers if p.citation_count is not None)
    logger.info("Semantic Scholar: enriched %d/%d papers", enriched, len(papers))
    return papers
