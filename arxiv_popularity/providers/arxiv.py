from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

import feedparser

from arxiv_popularity.matching import normalize_arxiv_id
from arxiv_popularity.models import Paper

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
        feed = feedparser.parse(f"{ARXIV_API_URL}?{_encode_params(params)}")

        if not feed.entries:
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

    logger.info("Discovered %d papers from arXiv", len(all_papers))
    return all_papers


def _encode_params(params: dict) -> str:
    from urllib.parse import urlencode
    return urlencode(params)


def fetch_single_paper(arxiv_id: str) -> Paper | None:
    params = {"id_list": arxiv_id, "max_results": 1}
    feed = feedparser.parse(f"{ARXIV_API_URL}?{_encode_params(params)}")
    if feed.entries:
        return _parse_entry(feed.entries[0])
    return None
