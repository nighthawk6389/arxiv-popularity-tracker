from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from arxiv_popularity.matching import normalize_arxiv_id
from arxiv_popularity.utils import fetch_with_retry

logger = logging.getLogger("arxiv_popularity.providers.huggingface")

HF_DAILY_PAPERS_URL = "https://huggingface.co/api/daily_papers"


@dataclass
class HFPaperData:
    arxiv_id: str
    upvotes: int
    title: str
    project_page: str | None
    github_repo: str | None
    github_stars: int | None


def _extract_arxiv_ids(html: str) -> list[str]:
    """Fallback: extract arXiv IDs from HTML page."""
    pattern = r'href="/papers/(\d{4}\.\d{4,5}(?:v\d+)?)"'
    matches = re.findall(pattern, html)
    seen: set[str] = set()
    result: list[str] = []
    for raw_id in matches:
        arxiv_id = normalize_arxiv_id(raw_id)
        if arxiv_id not in seen:
            seen.add(arxiv_id)
            result.append(arxiv_id)
    return result


def fetch_hf_daily_papers(sort: str = "trending") -> list[HFPaperData]:
    """Fetch papers from HuggingFace JSON API.

    Args:
        sort: Sort order — "trending" for trending papers, "date" for latest.
    """
    try:
        resp = fetch_with_retry(
            HF_DAILY_PAPERS_URL, params={"limit": 100, "sort": sort}, timeout=15,
        )
        entries = resp.json()
        results: list[HFPaperData] = []
        seen: set[str] = set()
        for entry in entries:
            paper = entry.get("paper", {})
            raw_id = paper.get("id", "")
            if not raw_id:
                continue
            arxiv_id = normalize_arxiv_id(raw_id)
            if arxiv_id in seen:
                continue
            seen.add(arxiv_id)

            gh_repo = paper.get("githubRepo") or None
            gh_stars = paper.get("githubStars")
            if gh_stars is not None:
                gh_stars = int(gh_stars)

            results.append(HFPaperData(
                arxiv_id=arxiv_id,
                upvotes=paper.get("upvotes", 0) or 0,
                title=paper.get("title", ""),
                project_page=paper.get("projectPage") or None,
                github_repo=gh_repo,
                github_stars=gh_stars,
            ))
        _hf_cache["papers"] = results
        logger.info("Found %d trending papers on HuggingFace", len(results))
        return results
    except Exception:
        logger.warning("Failed to fetch HuggingFace trending papers", exc_info=True)
        return []


def fetch_hf_trending_ids() -> list[str]:
    """Return arXiv IDs of currently trending HF papers."""
    papers = fetch_hf_daily_papers()
    return [p.arxiv_id for p in papers]


def get_hf_titles() -> dict[str, str]:
    """Get titles from cached HF data."""
    papers = _hf_cache.get("papers", [])
    return {p.arxiv_id: p.title for p in papers if p.title}


def get_hf_upvotes() -> dict[str, int]:
    """Get upvote counts from cached HF data."""
    papers = _hf_cache.get("papers", [])
    return {p.arxiv_id: p.upvotes for p in papers}


def get_hf_project_pages() -> dict[str, str]:
    """Get project page URLs from cached HF data."""
    papers = _hf_cache.get("papers", [])
    return {p.arxiv_id: p.project_page for p in papers if p.project_page}


def get_hf_github_data() -> dict[str, tuple[str, int | None]]:
    """Get GitHub repo URLs and star counts from cached HF data."""
    papers = _hf_cache.get("papers", [])
    return {
        p.arxiv_id: (p.github_repo, p.github_stars)
        for p in papers if p.github_repo
    }


# Module-level cache for parsed HF data
_hf_cache: dict[str, list[HFPaperData]] = {}
