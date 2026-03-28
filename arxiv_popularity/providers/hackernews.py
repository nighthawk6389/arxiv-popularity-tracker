from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from arxiv_popularity.matching import normalize_title
from arxiv_popularity.models import HNMention, Paper
from arxiv_popularity.utils import fetch_with_retry

logger = logging.getLogger("arxiv_popularity.providers.hackernews")

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


def _parse_hit(hit: dict) -> HNMention:
    created = datetime.fromisoformat(hit["created_at"].replace("Z", "+00:00"))
    return HNMention(
        story_id=int(hit["objectID"]),
        title=hit.get("title", ""),
        points=hit.get("points", 0) or 0,
        num_comments=hit.get("num_comments", 0) or 0,
        created_at=created,
        url=hit.get("url", ""),
    )


def _search_hn(query: str) -> list[HNMention]:
    resp = fetch_with_retry(HN_SEARCH_URL, params={"query": query, "tags": "story"}, timeout=10)
    data = resp.json()
    return [_parse_hit(h) for h in data.get("hits", [])]


def _dedupe_mentions(mentions: list[HNMention]) -> list[HNMention]:
    seen: set[int] = set()
    result: list[HNMention] = []
    for m in mentions:
        if m.story_id not in seen:
            seen.add(m.story_id)
            result.append(m)
    return result


def _search_for_paper(paper: Paper) -> list[HNMention]:
    all_mentions: list[HNMention] = []

    # Strategy 1: search by arXiv ID
    try:
        all_mentions.extend(_search_hn(paper.arxiv_id))
    except Exception:
        logger.debug("HN search by ID failed for %s", paper.arxiv_id)

    # Strategy 2: search by arXiv URL
    try:
        all_mentions.extend(_search_hn(f"arxiv.org/abs/{paper.arxiv_id}"))
    except Exception:
        logger.debug("HN search by URL failed for %s", paper.arxiv_id)

    # Strategy 3: fallback to normalized title (only if no results yet)
    if not all_mentions:
        try:
            title_query = normalize_title(paper.title)[:80]
            all_mentions.extend(_search_hn(title_query))
        except Exception:
            logger.debug("HN search by title failed for %s", paper.arxiv_id)

    return _dedupe_mentions(all_mentions)


def enrich(papers: list[Paper], thread_pool_size: int = 8) -> list[Paper]:
    def _enrich_one(paper: Paper) -> None:
        try:
            paper.hn_mentions = _search_for_paper(paper)
        except Exception:
            logger.warning("HN enrichment failed for %s", paper.arxiv_id, exc_info=True)

    with ThreadPoolExecutor(max_workers=thread_pool_size) as executor:
        futures = {executor.submit(_enrich_one, p): p for p in papers}
        for future in as_completed(futures):
            future.result()

    total = sum(len(p.hn_mentions) for p in papers)
    logger.info("Hacker News: found %d mentions across %d papers", total, len(papers))
    return papers
