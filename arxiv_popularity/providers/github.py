from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from arxiv_popularity.models import Paper
from arxiv_popularity.utils import fetch_with_retry

logger = logging.getLogger("arxiv_popularity.providers.github")

GH_API_URL = "https://api.github.com/repos"
UNAUTHENTICATED_LIMIT = 50


def _get_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    return {"Accept": "application/vnd.github.v3+json"}


def _parse_repo(url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub URL."""
    # e.g. https://github.com/owner/repo
    parts = url.rstrip("/").split("github.com/")
    if len(parts) != 2:
        return None
    segments = parts[1].split("/")
    if len(segments) < 2:
        return None
    owner, repo = segments[0], segments[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return (owner, repo)


def _fetch_stars(owner: str, repo: str) -> int | None:
    try:
        resp = fetch_with_retry(f"{GH_API_URL}/{owner}/{repo}", headers=_get_headers(), timeout=10)
        data = resp.json()
        return data.get("stargazers_count")
    except Exception:
        logger.debug("Failed to fetch stars for %s/%s", owner, repo)
        return None


def enrich(papers: list[Paper], thread_pool_size: int = 8) -> list[Paper]:
    candidates = [p for p in papers if p.github_url and p.github_stars is None]
    has_token = bool(os.environ.get("GITHUB_TOKEN", ""))

    if not has_token and len(candidates) > UNAUTHENTICATED_LIMIT:
        logger.warning(
            "No GITHUB_TOKEN set; capping GitHub enrichment at %d papers "
            "(set GITHUB_TOKEN for higher rate limits)",
            UNAUTHENTICATED_LIMIT,
        )
        candidates = candidates[:UNAUTHENTICATED_LIMIT]

    if not candidates:
        logger.info("GitHub: no papers with repo URLs to enrich")
        return papers

    def _enrich_one(paper: Paper) -> None:
        parsed = _parse_repo(paper.github_url)
        if not parsed:
            return
        owner, repo = parsed
        stars = _fetch_stars(owner, repo)
        if stars is not None:
            paper.github_stars = stars

    with ThreadPoolExecutor(max_workers=thread_pool_size) as executor:
        futures = {executor.submit(_enrich_one, p): p for p in candidates}
        for future in as_completed(futures):
            future.result()

    enriched = sum(1 for p in candidates if p.github_stars is not None)
    logger.info("GitHub: enriched %d/%d papers with star counts", enriched, len(candidates))
    return papers
