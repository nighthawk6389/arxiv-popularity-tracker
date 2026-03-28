from __future__ import annotations

import logging
import re

from arxiv_popularity.matching import normalize_arxiv_id
from arxiv_popularity.utils import fetch_with_retry

logger = logging.getLogger("arxiv_popularity.providers.huggingface")

HF_PAPERS_URL = "https://huggingface.co/papers"


def _extract_arxiv_ids(html: str) -> list[str]:
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


def _extract_paper_titles(html: str) -> dict[str, str]:
    """Extract {arxiv_id: title} from HF papers page."""
    # Pattern: link to paper followed by title text
    pattern = r'href="/papers/(\d{4}\.\d{4,5}(?:v\d+)?)"[^>]*>\s*(?:<[^>]+>)*\s*([^<]+)'
    titles: dict[str, str] = {}
    for match in re.finditer(pattern, html):
        arxiv_id = normalize_arxiv_id(match.group(1))
        title = match.group(2).strip()
        if title and arxiv_id not in titles:
            titles[arxiv_id] = title
    return titles


def fetch_hf_trending_ids() -> list[str]:
    try:
        resp = fetch_with_retry(HF_PAPERS_URL, timeout=15)
        _hf_cache["html"] = resp.text
        ids = _extract_arxiv_ids(resp.text)
        logger.info("Found %d trending papers on HuggingFace", len(ids))
        return ids
    except Exception:
        logger.warning("Failed to fetch HuggingFace trending papers", exc_info=True)
        return []


def get_hf_titles() -> dict[str, str]:
    """Get titles from cached HF page HTML."""
    html = _hf_cache.get("html", "")
    if not html:
        return {}
    return _extract_paper_titles(html)


# Module-level cache for the HF page HTML
_hf_cache: dict[str, str] = {}
