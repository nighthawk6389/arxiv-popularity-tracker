from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta

import feedparser

from arxiv_popularity.matching import normalize_arxiv_id
from arxiv_popularity.models import Paper
from arxiv_popularity.utils import fetch_with_retry

logger = logging.getLogger("arxiv_popularity.providers.arxiv")

ARXIV_API_URL = "https://export.arxiv.org/api/query"


def _parse_entry(entry: dict) -> Paper:
    raw_id = entry["id"].split("/abs/")[-1]
    arxiv_id = normalize_arxiv_id(raw_id)

    authors = [a.get("name", "") for a in entry.get("authors", [])]
    categories = [t["term"] for t in entry.get("tags", [])]

    published = datetime.fromisoformat(
        entry["published"].replace("Z", "+00:00")
    )
    updated = datetime.fromisoformat(
        entry["updated"].replace("Z", "+00:00")
    )

    return Paper(
        arxiv_id=arxiv_id,
        title=entry.get("title", "").replace("\n", " ").strip(),
        authors=authors,
        abstract=entry.get("summary", "").strip(),
        categories=categories,
        published=published,
        updated=updated,
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
    )


def fetch_arxiv_papers(
    categories: list[str],
    window_days: int,
    limit: int,
) -> list[Paper]:
    cat_query = " OR ".join(f"cat:{c}" for c in categories)
    query = f"({cat_query})"
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    all_papers: list[Paper] = []
    start = 0
    page_size = min(limit, 200)

    while len(all_papers) < limit:
        params = {
            "search_query": query,
            "start": start,
            "max_results": page_size,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }
        logger.info("Fetching arXiv papers (start=%d, max=%d)", start, page_size)

        try:
            resp = fetch_with_retry(
                ARXIV_API_URL, params=params, timeout=60,
                max_retries=5, backoff=3.0,
            )
            feed = feedparser.parse(resp.text)
        except Exception:
            logger.warning("arXiv API request failed", exc_info=True)
            break

        if not feed.entries:
            logger.debug("No entries returned from arXiv (possibly rate limited or empty)")

            break

        found_old = False
        for entry in feed.entries:
            try:
                paper = _parse_entry(entry)
                if paper.published < cutoff:
                    found_old = True
                    continue
                all_papers.append(paper)
                if len(all_papers) >= limit:
                    break
            except Exception:
                logger.warning("Failed to parse arXiv entry: %s", entry.get("id", "?"), exc_info=True)

        if found_old or len(feed.entries) < page_size:
            break
        start += page_size
        time.sleep(3)  # arXiv requires 3s between requests

    logger.info("Discovered %d papers from arXiv", len(all_papers))
    return all_papers


def _encode_params(params: dict) -> str:
    from urllib.parse import urlencode
    return urlencode(params)


def fetch_single_paper(arxiv_id: str) -> Paper | None:
    papers = fetch_papers_by_ids([arxiv_id])
    return papers[0] if papers else None


def fetch_papers_by_ids(arxiv_ids: list[str]) -> list[Paper]:
    """Fetch multiple papers by ID in a single arXiv API call."""
    if not arxiv_ids:
        return []
    id_list = ",".join(arxiv_ids)
    params = {"id_list": id_list, "max_results": len(arxiv_ids)}
    try:
        resp = fetch_with_retry(
            ARXIV_API_URL, params=params, timeout=60,
            max_retries=5, backoff=3.0,
        )
        feed = feedparser.parse(resp.text)
        papers = []
        for entry in feed.entries:
            try:
                papers.append(_parse_entry(entry))
            except Exception:
                logger.warning("Failed to parse entry %s", entry.get("id", "?"), exc_info=True)
        logger.info("Fetched %d papers by ID", len(papers))
        return papers
    except Exception:
        logger.warning("Failed to fetch papers by IDs", exc_info=True)
        return []
