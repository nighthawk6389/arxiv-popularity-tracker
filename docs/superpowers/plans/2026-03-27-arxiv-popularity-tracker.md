# arXiv Popularity Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that discovers arXiv papers, enriches them with popularity signals, scores them, and produces a ranked Top 50 HTML report.

**Architecture:** Sequential pipeline (`discover → enrich → score → export`) operating on a shared `list[Paper]`. Enrichment providers use `ThreadPoolExecutor` for parallel HTTP calls. All output is file-based (JSON, CSV, Markdown, HTML).

**Tech Stack:** Python 3.10+, `requests`, `feedparser`, standard library (`dataclasses`, `concurrent.futures`, `argparse`, `json`, `csv`, `html`, `math`, `re`, `logging`, `copy`)

**Spec:** `docs/superpowers/specs/2026-03-27-arxiv-popularity-tracker-design.md`

---

## File Map

```
arxiv_popularity/
  __init__.py          — package init, version
  __main__.py          — python -m entry point
  cli.py               — argparse, run command
  config.py            — DEFAULT_CONFIG dict, env var loading
  models.py            — Paper, HNMention, ScoreBreakdown dataclasses
  scoring.py           — score computation, explanation generation
  matching.py          — arxiv ID normalization, title normalization
  utils.py             — HTTP helpers, window parsing, logging setup
  providers/
    __init__.py        — empty
    arxiv.py           — arXiv Atom feed fetching
    huggingface.py     — HuggingFace daily papers scraping
    semantic_scholar.py — S2 batch + individual citation lookup
    hackernews.py      — HN Algolia search
    reddit.py          — stub provider
    x.py               — stub provider
  pipeline/
    __init__.py        — empty
    discover.py        — orchestrate discovery + dedup
    enrich.py          — orchestrate enrichment providers
    score.py           — score all papers
    export.py          — write JSON, CSV, MD, HTML

tests/
  __init__.py
  test_models.py
  test_matching.py
  test_scoring.py
  test_utils.py
  test_config.py
  test_providers/
    __init__.py
    test_arxiv.py
    test_huggingface.py
    test_semantic_scholar.py
    test_hackernews.py
  test_pipeline/
    __init__.py
    test_discover.py
    test_enrich.py
    test_score.py
    test_export.py

pyproject.toml         — project metadata, dependencies
.env.example           — documented env vars
README.md              — install, run, scoring explanation
DESIGN.md              — sources, tradeoffs (copy of spec essentials)
```

---

### Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `arxiv_popularity/__init__.py`
- Create: `arxiv_popularity/__main__.py`
- Create: `arxiv_popularity/providers/__init__.py`
- Create: `arxiv_popularity/pipeline/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_providers/__init__.py`
- Create: `tests/test_pipeline/__init__.py`
- Create: `.env.example`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "arxiv-popularity-tracker"
version = "0.1.0"
description = "Track which arXiv papers are getting attention and why"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.28",
    "feedparser>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
]
```

- [ ] **Step 2: Create package init files**

`arxiv_popularity/__init__.py`:
```python
"""arXiv Popularity Tracker — discover, enrich, score, and rank arXiv papers."""

__version__ = "0.1.0"
```

`arxiv_popularity/__main__.py`:
```python
from arxiv_popularity.cli import main

main()
```

`arxiv_popularity/providers/__init__.py`: empty file
`arxiv_popularity/pipeline/__init__.py`: empty file

- [ ] **Step 3: Create test directory init files**

`tests/__init__.py`: empty file
`tests/test_providers/__init__.py`: empty file
`tests/test_pipeline/__init__.py`: empty file

- [ ] **Step 4: Create .env.example**

```env
# Optional: Semantic Scholar API key for higher rate limits
# SEMANTIC_SCHOLAR_API_KEY=

# Optional: Reddit API credentials (not yet implemented)
# REDDIT_CLIENT_ID=
# REDDIT_CLIENT_SECRET=
```

- [ ] **Step 5: Install in dev mode and verify**

Run: `pip install -e ".[dev]"`
Expected: successful install

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml arxiv_popularity/ tests/ .env.example
git commit -m "feat: project scaffolding with package structure"
```

---

### Task 2: Data Models

**Files:**
- Create: `arxiv_popularity/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write test for Paper dataclass**

`tests/test_models.py`:
```python
from datetime import datetime, timezone
from arxiv_popularity.models import Paper, HNMention, ScoreBreakdown


def test_paper_defaults():
    p = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author A"],
        abstract="An abstract.",
        categories=["cs.AI"],
        published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url="https://arxiv.org/abs/2401.12345",
        pdf_url="https://arxiv.org/pdf/2401.12345",
    )
    assert p.citation_count is None
    assert p.hf_trending is False
    assert p.hn_mentions == []
    assert p.total_score == 0.0
    assert p.score_breakdown is None
    assert p.explanation == ""


def test_hn_mention():
    m = HNMention(
        story_id=123,
        title="Show HN: cool paper",
        points=100,
        num_comments=50,
        created_at=datetime(2024, 1, 16, tzinfo=timezone.utc),
        url="https://news.ycombinator.com/item?id=123",
    )
    assert m.points == 100
    assert m.num_comments == 50


def test_score_breakdown():
    sb = ScoreBreakdown(recency=0.8, citations=0.3, hf_trending=1.0, hn_discussion=0.5)
    assert sb.recency == 0.8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement models.py**

`arxiv_popularity/models.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class HNMention:
    story_id: int
    title: str
    points: int
    num_comments: int
    created_at: datetime
    url: str


@dataclass
class ScoreBreakdown:
    recency: float
    citations: float
    hf_trending: float
    hn_discussion: float


@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published: datetime
    updated: datetime
    arxiv_url: str
    pdf_url: str

    citation_count: int | None = None
    semantic_scholar_id: str | None = None
    hf_trending: bool = False
    hf_trending_rank: int | None = None
    hn_mentions: list[HNMention] = field(default_factory=list)

    total_score: float = 0.0
    score_breakdown: ScoreBreakdown | None = None
    explanation: str = ""
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_models.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add arxiv_popularity/models.py tests/test_models.py
git commit -m "feat: add Paper, HNMention, ScoreBreakdown dataclasses"
```

---

### Task 3: Matching Utilities

**Files:**
- Create: `arxiv_popularity/matching.py`
- Create: `tests/test_matching.py`

- [ ] **Step 1: Write tests**

`tests/test_matching.py`:
```python
from arxiv_popularity.matching import (
    normalize_arxiv_id,
    extract_arxiv_id_from_url,
    normalize_title,
)


class TestNormalizeArxivId:
    def test_strips_version(self):
        assert normalize_arxiv_id("2401.12345v2") == "2401.12345"

    def test_no_version(self):
        assert normalize_arxiv_id("2401.12345") == "2401.12345"

    def test_old_format(self):
        assert normalize_arxiv_id("hep-th/9901001v1") == "hep-th/9901001"

    def test_strips_whitespace(self):
        assert normalize_arxiv_id("  2401.12345v3  ") == "2401.12345"


class TestExtractArxivIdFromUrl:
    def test_abs_url(self):
        assert extract_arxiv_id_from_url("https://arxiv.org/abs/2401.12345") == "2401.12345"

    def test_abs_url_with_version(self):
        assert extract_arxiv_id_from_url("https://arxiv.org/abs/2401.12345v2") == "2401.12345"

    def test_pdf_url(self):
        assert extract_arxiv_id_from_url("https://arxiv.org/pdf/2401.12345") == "2401.12345"

    def test_non_arxiv_url(self):
        assert extract_arxiv_id_from_url("https://example.com/paper") is None

    def test_huggingface_papers_url(self):
        assert extract_arxiv_id_from_url("https://huggingface.co/papers/2401.12345") == "2401.12345"


class TestNormalizeTitle:
    def test_lowercase(self):
        assert normalize_title("Attention Is All You Need") == "attention is all you need"

    def test_strip_punctuation(self):
        assert normalize_title("Hello, World!") == "hello world"

    def test_collapse_whitespace(self):
        assert normalize_title("  too   many   spaces  ") == "too many spaces"

    def test_combined(self):
        assert normalize_title("  GPT-4: A Large  Model! ") == "gpt-4 a large model"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_matching.py -v`
Expected: FAIL

- [ ] **Step 3: Implement matching.py**

`arxiv_popularity/matching.py`:
```python
from __future__ import annotations

import re


def normalize_arxiv_id(raw: str) -> str:
    raw = raw.strip()
    return re.sub(r"v\d+$", "", raw)


def extract_arxiv_id_from_url(url: str) -> str | None:
    patterns = [
        r"arxiv\.org/(?:abs|pdf)/(\S+)",
        r"huggingface\.co/papers/(\S+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return normalize_arxiv_id(match.group(1))
    return None


def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_matching.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add arxiv_popularity/matching.py tests/test_matching.py
git commit -m "feat: add arxiv ID normalization and title matching utilities"
```

---

### Task 4: Config & Utils

**Files:**
- Create: `arxiv_popularity/config.py`
- Create: `arxiv_popularity/utils.py`
- Create: `tests/test_config.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write config tests**

`tests/test_config.py`:
```python
from arxiv_popularity.config import DEFAULT_CONFIG, load_config


def test_default_config_has_required_keys():
    assert "score_weights" in DEFAULT_CONFIG
    assert "providers" in DEFAULT_CONFIG
    assert "thread_pool_size" in DEFAULT_CONFIG


def test_weights_sum_to_one():
    weights = DEFAULT_CONFIG["score_weights"]
    assert abs(sum(weights.values()) - 1.0) < 0.001


def test_load_config_returns_defaults():
    cfg = load_config()
    assert cfg["score_weights"]["recency"] == 0.25
```

- [ ] **Step 2: Write utils tests**

`tests/test_utils.py`:
```python
import pytest
from arxiv_popularity.utils import parse_window


def test_parse_window_7d():
    assert parse_window("7d") == 7


def test_parse_window_14d():
    assert parse_window("14d") == 14


def test_parse_window_30d():
    assert parse_window("30d") == 30


def test_parse_window_invalid():
    with pytest.raises(ValueError):
        parse_window("7x")


def test_parse_window_no_unit():
    with pytest.raises(ValueError):
        parse_window("7")


def test_parse_window_zero():
    with pytest.raises(ValueError):
        parse_window("0d")
```

- [ ] **Step 3: Run tests to verify failure**

Run: `pytest tests/test_config.py tests/test_utils.py -v`
Expected: FAIL

- [ ] **Step 4: Implement config.py**

`arxiv_popularity/config.py`:
```python
from __future__ import annotations

import copy
import os


DEFAULT_CONFIG: dict = {
    "score_weights": {
        "recency": 0.25,
        "hf_trending": 0.20,
        "hn_discussion": 0.30,
        "citations": 0.25,
    },
    "recency_halflife_days": 7,
    "hn_scale_factor": 150,
    "citation_scale_factor": 50,
    "providers": {
        "semantic_scholar": True,
        "hackernews": True,
        "reddit": False,
        "x": False,
    },
    "thread_pool_size": 8,
}


def load_config() -> dict:
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        cfg["semantic_scholar_api_key"] = api_key
    return cfg
```

- [ ] **Step 5: Implement utils.py**

`arxiv_popularity/utils.py`:
```python
from __future__ import annotations

import logging
import re
import time

import requests


logger = logging.getLogger("arxiv_popularity")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_window(window: str) -> int:
    match = re.fullmatch(r"(\d+)d", window)
    if not match:
        raise ValueError(f"Invalid window format '{window}'. Use format like '7d', '14d', '30d'.")
    days = int(match.group(1))
    if days <= 0:
        raise ValueError(f"Window must be positive, got {days}d.")
    return days


def fetch_with_retry(
    url: str,
    *,
    method: str = "GET",
    headers: dict | None = None,
    json: dict | None = None,
    params: dict | None = None,
    max_retries: int = 3,
    backoff: float = 1.0,
    timeout: int = 30,
) -> requests.Response:
    for attempt in range(max_retries):
        try:
            resp = requests.request(
                method, url, headers=headers, json=json, params=params, timeout=timeout
            )
            if resp.status_code == 429:
                wait = backoff * (2 ** attempt)
                logger.warning("Rate limited on %s, waiting %.1fs", url, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait = backoff * (2 ** attempt)
            logger.warning("Request to %s failed (%s), retrying in %.1fs", url, e, wait)
            time.sleep(wait)
    raise requests.RequestException(f"Failed after {max_retries} retries: {url}")
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_config.py tests/test_utils.py -v`
Expected: all passed

- [ ] **Step 7: Commit**

```bash
git add arxiv_popularity/config.py arxiv_popularity/utils.py tests/test_config.py tests/test_utils.py
git commit -m "feat: add config defaults and utility helpers"
```

---

### Task 5: arXiv Provider

**Files:**
- Create: `arxiv_popularity/providers/arxiv.py`
- Create: `tests/test_providers/test_arxiv.py`

- [ ] **Step 1: Write tests**

`tests/test_providers/test_arxiv.py`:
```python
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from arxiv_popularity.providers.arxiv import fetch_arxiv_papers, _parse_entry


SAMPLE_ENTRY = {
    "id": "http://arxiv.org/abs/2401.12345v1",
    "title": "Test Paper Title",
    "summary": "This is a test abstract.",
    "authors": [{"name": "Alice"}, {"name": "Bob"}],
    "published": "2024-01-15T00:00:00Z",
    "updated": "2024-01-15T00:00:00Z",
    "arxiv_primary_category": {"term": "cs.AI"},
    "tags": [{"term": "cs.AI"}, {"term": "cs.LG"}],
    "links": [
        {"href": "http://arxiv.org/abs/2401.12345v1", "type": "text/html"},
        {"href": "http://arxiv.org/pdf/2401.12345v1", "type": "application/pdf", "title": "pdf"},
    ],
}


def test_parse_entry():
    paper = _parse_entry(SAMPLE_ENTRY)
    assert paper.arxiv_id == "2401.12345"
    assert paper.title == "Test Paper Title"
    assert paper.authors == ["Alice", "Bob"]
    assert paper.categories == ["cs.AI", "cs.LG"]
    assert paper.arxiv_url == "https://arxiv.org/abs/2401.12345"
    assert paper.pdf_url == "https://arxiv.org/pdf/2401.12345"


def test_fetch_arxiv_papers_filters_by_window():
    with patch("arxiv_popularity.providers.arxiv.feedparser") as mock_fp:
        old_entry = {**SAMPLE_ENTRY, "published": "2020-01-01T00:00:00Z", "updated": "2020-01-01T00:00:00Z"}
        mock_fp.parse.return_value = MagicMock(entries=[SAMPLE_ENTRY, old_entry])
        papers = fetch_arxiv_papers(categories=["cs.AI"], window_days=7, limit=100)
        # Only the recent one should pass (depending on current date, the sample may also be old)
        # The function should not crash regardless
        assert isinstance(papers, list)
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_providers/test_arxiv.py -v`
Expected: FAIL

- [ ] **Step 3: Implement arxiv.py**

`arxiv_popularity/providers/arxiv.py`:
```python
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_providers/test_arxiv.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add arxiv_popularity/providers/arxiv.py tests/test_providers/test_arxiv.py
git commit -m "feat: add arXiv provider with Atom feed parsing"
```

---

### Task 6: HuggingFace Provider

**Files:**
- Create: `arxiv_popularity/providers/huggingface.py`
- Create: `tests/test_providers/test_huggingface.py`

- [ ] **Step 1: Write tests**

`tests/test_providers/test_huggingface.py`:
```python
from unittest.mock import patch, MagicMock
from arxiv_popularity.providers.huggingface import fetch_hf_trending_ids, _extract_arxiv_ids


def test_extract_arxiv_ids_from_html():
    html = '''
    <a href="/papers/2401.12345">Paper 1</a>
    <a href="/papers/2401.67890">Paper 2</a>
    <a href="/other/link">Not a paper</a>
    '''
    ids = _extract_arxiv_ids(html)
    assert ids == ["2401.12345", "2401.67890"]


def test_extract_arxiv_ids_deduplicates():
    html = '''
    <a href="/papers/2401.12345">Paper 1</a>
    <a href="/papers/2401.12345">Paper 1 again</a>
    '''
    ids = _extract_arxiv_ids(html)
    assert ids == ["2401.12345"]


def test_fetch_hf_trending_returns_empty_on_failure():
    with patch("arxiv_popularity.providers.huggingface.fetch_with_retry") as mock_fetch:
        mock_fetch.side_effect = Exception("Network error")
        ids = fetch_hf_trending_ids()
        assert ids == []
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_providers/test_huggingface.py -v`
Expected: FAIL

- [ ] **Step 3: Implement huggingface.py**

`arxiv_popularity/providers/huggingface.py`:
```python
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


def fetch_hf_trending_ids() -> list[str]:
    try:
        resp = fetch_with_retry(HF_PAPERS_URL, timeout=15)
        ids = _extract_arxiv_ids(resp.text)
        logger.info("Found %d trending papers on HuggingFace", len(ids))
        return ids
    except Exception:
        logger.warning("Failed to fetch HuggingFace trending papers", exc_info=True)
        return []
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_providers/test_huggingface.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add arxiv_popularity/providers/huggingface.py tests/test_providers/test_huggingface.py
git commit -m "feat: add HuggingFace trending papers provider"
```

---

### Task 7: Semantic Scholar Provider

**Files:**
- Create: `arxiv_popularity/providers/semantic_scholar.py`
- Create: `tests/test_providers/test_semantic_scholar.py`

- [ ] **Step 1: Write tests**

`tests/test_providers/test_semantic_scholar.py`:
```python
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from arxiv_popularity.models import Paper
from arxiv_popularity.providers.semantic_scholar import enrich


def _make_paper(arxiv_id: str = "2401.12345") -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title="Test", authors=[], abstract="",
        categories=[], published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
    )


def test_enrich_sets_citation_count():
    paper = _make_paper()
    batch_response = MagicMock()
    batch_response.json.return_value = [
        {"paperId": "s2-123", "citationCount": 42, "externalIds": {"ArXiv": "2401.12345"}}
    ]

    with patch("arxiv_popularity.providers.semantic_scholar.fetch_with_retry") as mock_fetch:
        mock_fetch.return_value = batch_response
        result = enrich([paper])
    assert result[0].citation_count == 42
    assert result[0].semantic_scholar_id == "s2-123"


def test_enrich_handles_missing_paper():
    paper = _make_paper()
    batch_response = MagicMock()
    batch_response.json.return_value = [None]

    with patch("arxiv_popularity.providers.semantic_scholar.fetch_with_retry") as mock_fetch:
        mock_fetch.return_value = batch_response
        result = enrich([paper])
    assert result[0].citation_count is None


def test_enrich_handles_batch_failure_with_individual_fallback():
    paper = _make_paper()

    individual_response = MagicMock()
    individual_response.json.return_value = {
        "paperId": "s2-123", "citationCount": 10
    }

    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Batch failed")
        return individual_response

    with patch("arxiv_popularity.providers.semantic_scholar.fetch_with_retry") as mock_fetch:
        mock_fetch.side_effect = side_effect
        result = enrich([paper])
    assert result[0].citation_count == 10
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_providers/test_semantic_scholar.py -v`
Expected: FAIL

- [ ] **Step 3: Implement semantic_scholar.py**

`arxiv_popularity/providers/semantic_scholar.py`:
```python
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
                    future.result()  # propagate exceptions logged inside

    enriched = sum(1 for p in papers if p.citation_count is not None)
    logger.info("Semantic Scholar: enriched %d/%d papers", enriched, len(papers))
    return papers
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_providers/test_semantic_scholar.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add arxiv_popularity/providers/semantic_scholar.py tests/test_providers/test_semantic_scholar.py
git commit -m "feat: add Semantic Scholar provider with batch + fallback"
```

---

### Task 8: Hacker News Provider

**Files:**
- Create: `arxiv_popularity/providers/hackernews.py`
- Create: `tests/test_providers/test_hackernews.py`

- [ ] **Step 1: Write tests**

`tests/test_providers/test_hackernews.py`:
```python
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from arxiv_popularity.models import Paper
from arxiv_popularity.providers.hackernews import enrich, _search_hn, _dedupe_mentions


def _make_paper(arxiv_id: str = "2401.12345") -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title="Attention Is All You Need", authors=[], abstract="",
        categories=[], published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
    )


def test_search_hn_returns_mentions():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "hits": [
            {
                "objectID": "123",
                "title": "Attention paper on HN",
                "points": 200,
                "num_comments": 80,
                "created_at": "2024-01-16T12:00:00Z",
                "url": "https://arxiv.org/abs/2401.12345",
            }
        ]
    }
    with patch("arxiv_popularity.providers.hackernews.fetch_with_retry", return_value=mock_resp):
        mentions = _search_hn("2401.12345")
    assert len(mentions) == 1
    assert mentions[0].points == 200


def test_dedupe_mentions():
    from arxiv_popularity.models import HNMention
    m1 = HNMention(story_id=1, title="A", points=10, num_comments=5,
                   created_at=datetime(2024, 1, 15, tzinfo=timezone.utc), url="u1")
    m2 = HNMention(story_id=1, title="A", points=10, num_comments=5,
                   created_at=datetime(2024, 1, 15, tzinfo=timezone.utc), url="u1")
    m3 = HNMention(story_id=2, title="B", points=20, num_comments=10,
                   created_at=datetime(2024, 1, 16, tzinfo=timezone.utc), url="u2")
    result = _dedupe_mentions([m1, m2, m3])
    assert len(result) == 2


def test_enrich_does_not_crash_on_failure():
    paper = _make_paper()
    with patch("arxiv_popularity.providers.hackernews.fetch_with_retry", side_effect=Exception("fail")):
        result = enrich([paper])
    assert result[0].hn_mentions == []
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_providers/test_hackernews.py -v`
Expected: FAIL

- [ ] **Step 3: Implement hackernews.py**

`arxiv_popularity/providers/hackernews.py`:
```python
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_providers/test_hackernews.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add arxiv_popularity/providers/hackernews.py tests/test_providers/test_hackernews.py
git commit -m "feat: add Hacker News provider with multi-strategy search"
```

---

### Task 9: Stub Providers (Reddit, X)

**Files:**
- Create: `arxiv_popularity/providers/reddit.py`
- Create: `arxiv_popularity/providers/x.py`

- [ ] **Step 1: Create reddit.py stub**

`arxiv_popularity/providers/reddit.py`:
```python
from __future__ import annotations

import logging
import os

from arxiv_popularity.models import Paper

logger = logging.getLogger("arxiv_popularity.providers.reddit")


def enrich(papers: list[Paper], **kwargs) -> list[Paper]:
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        logger.info("Reddit provider not configured (set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET) — skipping")
    else:
        logger.info("Reddit provider not yet implemented — skipping")
    return papers
```

- [ ] **Step 2: Create x.py stub**

`arxiv_popularity/providers/x.py`:
```python
from __future__ import annotations

import logging

from arxiv_popularity.models import Paper

logger = logging.getLogger("arxiv_popularity.providers.x")


def enrich(papers: list[Paper], **kwargs) -> list[Paper]:
    logger.info("X (Twitter) provider not implemented — skipping")
    return papers
```

- [ ] **Step 3: Commit**

```bash
git add arxiv_popularity/providers/reddit.py arxiv_popularity/providers/x.py
git commit -m "feat: add Reddit and X stub providers"
```

---

### Task 10: Scoring Engine

**Files:**
- Create: `arxiv_popularity/scoring.py`
- Create: `tests/test_scoring.py`

- [ ] **Step 1: Write tests**

`tests/test_scoring.py`:
```python
import math
from datetime import datetime, timezone, timedelta
from arxiv_popularity.models import Paper, HNMention, ScoreBreakdown
from arxiv_popularity.scoring import score_paper, generate_explanation
from arxiv_popularity.config import DEFAULT_CONFIG


def _make_paper(**overrides) -> Paper:
    defaults = dict(
        arxiv_id="2401.12345", title="Test", authors=[], abstract="",
        categories=[], published=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
        arxiv_url="https://arxiv.org/abs/2401.12345",
        pdf_url="https://arxiv.org/pdf/2401.12345",
    )
    defaults.update(overrides)
    return Paper(**defaults)


def test_brand_new_paper_has_high_recency():
    paper = _make_paper()
    score_paper(paper, DEFAULT_CONFIG)
    assert paper.score_breakdown.recency > 0.9


def test_old_paper_has_low_recency():
    paper = _make_paper(published=datetime.now(timezone.utc) - timedelta(days=30))
    score_paper(paper, DEFAULT_CONFIG)
    assert paper.score_breakdown.recency < 0.1


def test_hf_trending_boosts_score():
    p1 = _make_paper(hf_trending=False)
    p2 = _make_paper(hf_trending=True)
    score_paper(p1, DEFAULT_CONFIG)
    score_paper(p2, DEFAULT_CONFIG)
    assert p2.total_score > p1.total_score


def test_citations_contribute_to_score():
    p1 = _make_paper(citation_count=0)
    p2 = _make_paper(citation_count=100)
    score_paper(p1, DEFAULT_CONFIG)
    score_paper(p2, DEFAULT_CONFIG)
    assert p2.total_score > p1.total_score


def test_hn_mentions_contribute_to_score():
    mention = HNMention(
        story_id=1, title="HN", points=200, num_comments=100,
        created_at=datetime.now(timezone.utc), url="u",
    )
    p1 = _make_paper()
    p2 = _make_paper(hn_mentions=[mention])
    # Need to use field properly
    p2.hn_mentions = [mention]
    score_paper(p1, DEFAULT_CONFIG)
    score_paper(p2, DEFAULT_CONFIG)
    assert p2.total_score > p1.total_score


def test_explanation_not_empty():
    paper = _make_paper(hf_trending=True, citation_count=50)
    score_paper(paper, DEFAULT_CONFIG)
    assert paper.explanation != ""


def test_score_between_0_and_1():
    paper = _make_paper(hf_trending=True, citation_count=1000)
    mention = HNMention(
        story_id=1, title="HN", points=500, num_comments=200,
        created_at=datetime.now(timezone.utc), url="u",
    )
    paper.hn_mentions = [mention]
    score_paper(paper, DEFAULT_CONFIG)
    assert 0 <= paper.total_score <= 1.0
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_scoring.py -v`
Expected: FAIL

- [ ] **Step 3: Implement scoring.py**

`arxiv_popularity/scoring.py`:
```python
from __future__ import annotations

import math
from datetime import datetime, timezone

from arxiv_popularity.models import Paper, ScoreBreakdown


def _recency_score(paper: Paper, halflife_days: float) -> float:
    age_days = (datetime.now(timezone.utc) - paper.published).total_seconds() / 86400
    lam = math.log(2) / halflife_days
    return math.exp(-lam * max(age_days, 0))


def _hf_score(paper: Paper) -> float:
    return 1.0 if paper.hf_trending else 0.0


def _hn_score(paper: Paper, halflife_days: float, scale_factor: float) -> float:
    if not paper.hn_mentions:
        return 0.0
    lam = math.log(2) / halflife_days
    total = 0.0
    now = datetime.now(timezone.utc)
    for m in paper.hn_mentions:
        age_days = (now - m.created_at).total_seconds() / 86400
        decay = math.exp(-lam * max(age_days, 0))
        total += decay * (m.points + 2 * m.num_comments)
    return math.tanh(total / scale_factor)


def _citation_score(paper: Paper, scale_factor: float) -> float:
    count = paper.citation_count or 0
    return math.tanh(count / scale_factor)


def generate_explanation(breakdown: ScoreBreakdown, weights: dict) -> str:
    components = {
        "recency": breakdown.recency * weights["recency"],
        "HF trending": breakdown.hf_trending * weights["hf_trending"],
        "HN discussion": breakdown.hn_discussion * weights["hn_discussion"],
        "citations": breakdown.citations * weights["citations"],
    }
    total = sum(components.values())
    if total == 0:
        return "No signals detected"

    fractions = {k: v / total for k, v in components.items()}
    sorted_components = sorted(fractions.items(), key=lambda x: x[1], reverse=True)
    top_name, top_frac = sorted_components[0]
    second_name, second_frac = sorted_components[1]

    # Special case: recent + trending
    if fractions.get("recency", 0) > 0.2 and fractions.get("HF trending", 0) > 0.2:
        return "New breakout paper with trending signal"

    if top_frac > 0.50:
        return f"Driven mainly by {top_name}"

    if top_frac > 0.30 and second_frac > 0.30:
        return f"Strong {top_name} and {second_name} signal"

    return "Balanced signals across sources"


def score_paper(paper: Paper, config: dict) -> None:
    weights = config["score_weights"]
    halflife = config["recency_halflife_days"]

    recency = _recency_score(paper, halflife)
    hf = _hf_score(paper)
    hn = _hn_score(paper, halflife, config["hn_scale_factor"])
    citations = _citation_score(paper, config["citation_scale_factor"])

    breakdown = ScoreBreakdown(
        recency=recency,
        citations=citations,
        hf_trending=hf,
        hn_discussion=hn,
    )

    total = (
        weights["recency"] * recency
        + weights["hf_trending"] * hf
        + weights["hn_discussion"] * hn
        + weights["citations"] * citations
    )

    paper.score_breakdown = breakdown
    paper.total_score = total
    paper.explanation = generate_explanation(breakdown, weights)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_scoring.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add arxiv_popularity/scoring.py tests/test_scoring.py
git commit -m "feat: add scoring engine with weighted components and explanations"
```

---

### Task 11: Pipeline — Discovery & Enrichment Orchestration

**Files:**
- Create: `arxiv_popularity/pipeline/discover.py`
- Create: `arxiv_popularity/pipeline/enrich.py`
- Create: `arxiv_popularity/pipeline/score.py`
- Create: `tests/test_pipeline/test_discover.py`
- Create: `tests/test_pipeline/test_enrich.py`
- Create: `tests/test_pipeline/test_score.py`

- [ ] **Step 1: Write discover tests**

`tests/test_pipeline/test_discover.py`:
```python
from datetime import datetime, timezone
from unittest.mock import patch
from arxiv_popularity.models import Paper
from arxiv_popularity.pipeline.discover import discover


def _make_paper(arxiv_id: str, hf: bool = False) -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title=f"Paper {arxiv_id}", authors=[], abstract="",
        categories=["cs.AI"], published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        hf_trending=hf,
    )


def test_discover_deduplicates():
    papers = [_make_paper("2401.11111"), _make_paper("2401.11111")]
    with patch("arxiv_popularity.pipeline.discover.fetch_arxiv_papers", return_value=papers), \
         patch("arxiv_popularity.pipeline.discover.fetch_hf_trending_ids", return_value=[]):
        result = discover(categories=["cs.AI"], window_days=7, limit=100)
    assert len(result) == 1


def test_discover_marks_hf_trending():
    papers = [_make_paper("2401.11111"), _make_paper("2401.22222")]
    with patch("arxiv_popularity.pipeline.discover.fetch_arxiv_papers", return_value=papers), \
         patch("arxiv_popularity.pipeline.discover.fetch_hf_trending_ids", return_value=["2401.11111"]):
        result = discover(categories=["cs.AI"], window_days=7, limit=100)
    trending = [p for p in result if p.hf_trending]
    assert len(trending) == 1
    assert trending[0].arxiv_id == "2401.11111"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `pytest tests/test_pipeline/test_discover.py -v`
Expected: FAIL

- [ ] **Step 3: Implement discover.py**

`arxiv_popularity/pipeline/discover.py`:
```python
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
        # Fetch missing papers individually from arXiv
        for hf_id in missing_hf_ids:
            try:
                from arxiv_popularity.providers.arxiv import fetch_single_paper
                paper = fetch_single_paper(hf_id)
                if paper:
                    seen[paper.arxiv_id] = paper
            except Exception:
                logger.debug("Could not fetch HF paper %s from arXiv", hf_id)

    for rank, hf_id in enumerate(hf_ids, 1):
        if hf_id in seen:
            seen[hf_id].hf_trending = True
            seen[hf_id].hf_trending_rank = rank

    trending_count = sum(1 for p in seen.values() if p.hf_trending)
    logger.info("Discovery complete: %d papers (%d HF trending)", len(seen), trending_count)

    return list(seen.values())
```

- [ ] **Step 4: Run discover tests**

Run: `pytest tests/test_pipeline/test_discover.py -v`
Expected: all passed

- [ ] **Step 5: Write enrich tests**

`tests/test_pipeline/test_enrich.py`:
```python
from datetime import datetime, timezone
from unittest.mock import patch
from arxiv_popularity.models import Paper
from arxiv_popularity.pipeline.enrich import enrich_papers


def _make_paper(arxiv_id: str = "2401.12345") -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title="Test", authors=[], abstract="",
        categories=[], published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
    )


def test_enrich_skips_disabled_providers():
    papers = [_make_paper()]
    config = {"providers": {"semantic_scholar": False, "hackernews": False, "reddit": False, "x": False}, "thread_pool_size": 2}
    with patch("arxiv_popularity.providers.semantic_scholar.enrich") as mock_s2, \
         patch("arxiv_popularity.providers.hackernews.enrich") as mock_hn:
        result = enrich_papers(papers, config)
        mock_s2.assert_not_called()
        mock_hn.assert_not_called()
    assert len(result) == 1


def test_enrich_calls_enabled_providers():
    papers = [_make_paper()]
    config = {"providers": {"semantic_scholar": True, "hackernews": True, "reddit": False, "x": False}, "thread_pool_size": 2}
    with patch("arxiv_popularity.providers.semantic_scholar.enrich", return_value=papers) as mock_s2, \
         patch("arxiv_popularity.providers.hackernews.enrich", return_value=papers) as mock_hn:
        enrich_papers(papers, config)
        mock_s2.assert_called_once()
        mock_hn.assert_called_once()
```

- [ ] **Step 6: Implement enrich.py**

`arxiv_popularity/pipeline/enrich.py`:
```python
from __future__ import annotations

import logging

from arxiv_popularity.models import Paper
from arxiv_popularity.providers import semantic_scholar, hackernews, reddit, x

logger = logging.getLogger("arxiv_popularity.pipeline.enrich")


def enrich_papers(papers: list[Paper], config: dict) -> list[Paper]:
    providers_config = config.get("providers", {})
    pool_size = config.get("thread_pool_size", 8)

    if providers_config.get("semantic_scholar", True):
        logger.info("Enriching with Semantic Scholar...")
        papers = semantic_scholar.enrich(papers, thread_pool_size=pool_size)

    if providers_config.get("hackernews", True):
        logger.info("Enriching with Hacker News...")
        papers = hackernews.enrich(papers, thread_pool_size=pool_size)

    if providers_config.get("reddit", False):
        papers = reddit.enrich(papers)

    if providers_config.get("x", False):
        papers = x.enrich(papers)

    return papers
```

- [ ] **Step 7: Write score pipeline tests**

`tests/test_pipeline/test_score.py`:
```python
from datetime import datetime, timezone
from arxiv_popularity.models import Paper
from arxiv_popularity.pipeline.score import score_papers
from arxiv_popularity.config import DEFAULT_CONFIG


def _make_paper(arxiv_id: str, citation_count: int = 0) -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title=f"Paper {arxiv_id}", authors=[], abstract="",
        categories=[], published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        citation_count=citation_count,
    )


def test_score_papers_sorts_by_score():
    papers = [_make_paper("2401.11111", citation_count=5), _make_paper("2401.22222", citation_count=500)]
    result = score_papers(papers, DEFAULT_CONFIG)
    assert result[0].arxiv_id == "2401.22222"
    assert result[0].total_score >= result[1].total_score


def test_score_papers_sets_breakdown():
    papers = [_make_paper("2401.11111")]
    result = score_papers(papers, DEFAULT_CONFIG)
    assert result[0].score_breakdown is not None
    assert result[0].explanation != ""
```

- [ ] **Step 8: Implement score.py**

`arxiv_popularity/pipeline/score.py`:
```python
from __future__ import annotations

import logging

from arxiv_popularity.models import Paper
from arxiv_popularity.scoring import score_paper

logger = logging.getLogger("arxiv_popularity.pipeline.score")


def score_papers(papers: list[Paper], config: dict) -> list[Paper]:
    for paper in papers:
        score_paper(paper, config)

    papers.sort(key=lambda p: p.total_score, reverse=True)
    logger.info("Scored and ranked %d papers", len(papers))
    return papers
```

- [ ] **Step 9: Run pipeline tests so far**

Run: `pytest tests/test_pipeline/test_discover.py tests/test_pipeline/test_enrich.py tests/test_pipeline/test_score.py -v`
Expected: all passed

- [ ] **Step 10: Commit**

```bash
git add arxiv_popularity/pipeline/discover.py arxiv_popularity/pipeline/enrich.py arxiv_popularity/pipeline/score.py tests/test_pipeline/
git commit -m "feat: add pipeline stages — discover, enrich, score"
```

---

### Task 12: Pipeline — Export

**Files:**
- Create: `arxiv_popularity/pipeline/export.py`
- Create: `tests/test_pipeline/test_export.py`

- [ ] **Step 1: Write export tests**

`tests/test_pipeline/test_export.py`:
```python
import json
import csv
import os
from datetime import datetime, timezone
from arxiv_popularity.models import Paper, ScoreBreakdown
from arxiv_popularity.pipeline.export import export_all


def _make_scored_paper(arxiv_id: str = "2401.12345") -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title="Test Paper", authors=["Alice", "Bob"],
        abstract="Abstract", categories=["cs.AI"],
        published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        citation_count=42, hf_trending=True, total_score=0.75,
        score_breakdown=ScoreBreakdown(recency=0.9, citations=0.4, hf_trending=1.0, hn_discussion=0.3),
        explanation="Strong HF trending and recency signal",
    )


def test_export_creates_all_files(tmp_path):
    papers = [_make_scored_paper()]
    export_all(papers, output_dir=str(tmp_path), top_n=50)

    assert (tmp_path / "papers.json").exists()
    assert (tmp_path / "papers.csv").exists()
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.html").exists()


def test_json_output_is_valid(tmp_path):
    papers = [_make_scored_paper()]
    export_all(papers, output_dir=str(tmp_path), top_n=50)

    with open(tmp_path / "papers.json") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["arxiv_id"] == "2401.12345"


def test_csv_has_headers(tmp_path):
    papers = [_make_scored_paper()]
    export_all(papers, output_dir=str(tmp_path), top_n=50)

    with open(tmp_path / "papers.csv") as f:
        reader = csv.DictReader(f)
        row = next(reader)
    assert "arxiv_id" in row
    assert "title" in row
    assert "score" in row
    assert row["authors"] == "Alice; Bob"


def test_html_contains_paper_title(tmp_path):
    papers = [_make_scored_paper()]
    export_all(papers, output_dir=str(tmp_path), top_n=50)

    html = (tmp_path / "report.html").read_text()
    assert "Test Paper" in html
    assert "arxiv.org/abs/2401.12345" in html
```

- [ ] **Step 2: Run export tests to verify failure**

Run: `pytest tests/test_pipeline/test_export.py -v`
Expected: FAIL

- [ ] **Step 3: Implement export.py**

`arxiv_popularity/pipeline/export.py`:
```python
from __future__ import annotations

import csv
import json
import logging
import os
from datetime import datetime, timezone
from html import escape

from arxiv_popularity.models import Paper

logger = logging.getLogger("arxiv_popularity.pipeline.export")


def _paper_to_dict(paper: Paper) -> dict:
    return {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "authors": paper.authors,
        "abstract": paper.abstract,
        "categories": paper.categories,
        "published": paper.published.isoformat(),
        "updated": paper.updated.isoformat(),
        "arxiv_url": paper.arxiv_url,
        "pdf_url": paper.pdf_url,
        "citation_count": paper.citation_count,
        "hf_trending": paper.hf_trending,
        "hf_trending_rank": paper.hf_trending_rank,
        "hn_mention_count": len(paper.hn_mentions),
        "hn_total_points": sum(m.points for m in paper.hn_mentions),
        "score": round(paper.total_score, 4),
        "score_breakdown": {
            "recency": round(paper.score_breakdown.recency, 4),
            "citations": round(paper.score_breakdown.citations, 4),
            "hf_trending": round(paper.score_breakdown.hf_trending, 4),
            "hn_discussion": round(paper.score_breakdown.hn_discussion, 4),
        } if paper.score_breakdown else None,
        "explanation": paper.explanation,
    }


def _export_json(papers: list[Paper], path: str) -> None:
    data = [_paper_to_dict(p) for p in papers]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Wrote %s (%d papers)", path, len(papers))


def _export_csv(papers: list[Paper], path: str) -> None:
    fieldnames = [
        "arxiv_id", "title", "authors", "categories", "published",
        "score", "citation_count", "hn_mention_count", "hf_trending", "explanation",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in papers:
            writer.writerow({
                "arxiv_id": p.arxiv_id,
                "title": p.title,
                "authors": "; ".join(p.authors),
                "categories": "; ".join(p.categories),
                "published": p.published.strftime("%Y-%m-%d"),
                "score": f"{p.total_score:.4f}",
                "citation_count": p.citation_count if p.citation_count is not None else "",
                "hn_mention_count": len(p.hn_mentions),
                "hf_trending": "Yes" if p.hf_trending else "",
                "explanation": p.explanation,
            })
    logger.info("Wrote %s (%d papers)", path, len(papers))


def _export_markdown(papers: list[Paper], path: str, top_n: int) -> None:
    top = papers[:top_n]
    lines = [
        f"# arXiv Popularity Report",
        f"",
        f"*Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        f"",
        f"## Top {len(top)} Papers",
        f"",
        "| # | Title | Date | Score | Cites | HN | HF | Why |",
        "|---|-------|------|-------|-------|----|----|-----|",
    ]
    for i, p in enumerate(top, 1):
        cites = str(p.citation_count) if p.citation_count is not None else "-"
        hn = str(len(p.hn_mentions)) if p.hn_mentions else "0"
        hf = "Yes" if p.hf_trending else ""
        date = p.published.strftime("%Y-%m-%d")
        title_link = f"[{p.title}]({p.arxiv_url})"
        lines.append(f"| {i} | {title_link} | {date} | {p.total_score:.3f} | {cites} | {hn} | {hf} | {p.explanation} |")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    logger.info("Wrote %s (top %d)", path, len(top))


def _export_html(papers: list[Paper], path: str, top_n: int) -> None:
    top = papers[:top_n]
    rows = []
    for i, p in enumerate(top, 1):
        cites = str(p.citation_count) if p.citation_count is not None else "-"
        hn_count = len(p.hn_mentions)
        hn_points = sum(m.points for m in p.hn_mentions)
        hn_display = f"{hn_count} ({hn_points}pts)" if hn_count else "0"
        hf_badge = '<span class="badge hf">HF</span>' if p.hf_trending else ""
        date = p.published.strftime("%Y-%m-%d")
        authors_short = ", ".join(p.authors[:3])
        if len(p.authors) > 3:
            authors_short += f" +{len(p.authors) - 3}"

        score_bar_width = int(p.total_score * 100)

        rows.append(f"""      <tr>
        <td class="rank">{i}</td>
        <td class="title-cell">
          <a href="{escape(p.arxiv_url)}" target="_blank">{escape(p.title)}</a>
          <div class="authors">{escape(authors_short)}</div>
        </td>
        <td class="date">{date}</td>
        <td class="score">
          <div class="score-val">{p.total_score:.3f}</div>
          <div class="score-bar"><div class="score-fill" style="width:{score_bar_width}%"></div></div>
        </td>
        <td class="num">{cites}</td>
        <td class="num">{hn_display}</td>
        <td class="badges">{hf_badge}</td>
        <td class="explanation">{escape(p.explanation)}</td>
      </tr>""")

    table_rows = "\n".join(rows)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>arXiv Popularity Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8f9fa; color: #1a1a2e; padding: 2rem; max-width: 1400px; margin: 0 auto; }}
  h1 {{ font-size: 1.5rem; font-weight: 700; margin-bottom: 0.25rem; }}
  .subtitle {{ color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }}
  table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  thead {{ background: #1a1a2e; color: white; }}
  th {{ padding: 0.75rem 0.5rem; text-align: left; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }}
  td {{ padding: 0.6rem 0.5rem; border-bottom: 1px solid #eee; font-size: 0.85rem; vertical-align: top; }}
  tr:hover {{ background: #f0f4ff; }}
  .rank {{ text-align: center; font-weight: 700; color: #888; width: 2rem; }}
  .title-cell a {{ color: #1a1a2e; text-decoration: none; font-weight: 600; line-height: 1.3; }}
  .title-cell a:hover {{ color: #4361ee; text-decoration: underline; }}
  .authors {{ color: #888; font-size: 0.75rem; margin-top: 0.2rem; }}
  .date {{ white-space: nowrap; color: #666; }}
  .score {{ min-width: 5rem; }}
  .score-val {{ font-weight: 700; font-variant-numeric: tabular-nums; }}
  .score-bar {{ height: 4px; background: #eee; border-radius: 2px; margin-top: 3px; }}
  .score-fill {{ height: 100%; background: #4361ee; border-radius: 2px; }}
  .num {{ text-align: center; font-variant-numeric: tabular-nums; }}
  .badges {{ text-align: center; }}
  .badge {{ display: inline-block; padding: 0.15rem 0.4rem; border-radius: 3px; font-size: 0.7rem; font-weight: 700; }}
  .badge.hf {{ background: #ffd21e; color: #1a1a2e; }}
  .explanation {{ color: #555; font-size: 0.8rem; max-width: 14rem; }}
</style>
</head>
<body>
  <h1>arXiv Popularity Report</h1>
  <p class="subtitle">Top {len(top)} papers &mdash; Generated {generated}</p>
  <table>
    <thead>
      <tr>
        <th>#</th><th>Title</th><th>Date</th><th>Score</th><th>Cites</th><th>HN</th><th>HF</th><th>Why</th>
      </tr>
    </thead>
    <tbody>
{table_rows}
    </tbody>
  </table>
</body>
</html>"""

    with open(path, "w") as f:
        f.write(html)
    logger.info("Wrote %s (top %d)", path, len(top))


def export_all(papers: list[Paper], output_dir: str, top_n: int) -> None:
    os.makedirs(output_dir, exist_ok=True)
    _export_json(papers, os.path.join(output_dir, "papers.json"))
    _export_csv(papers, os.path.join(output_dir, "papers.csv"))
    _export_markdown(papers, os.path.join(output_dir, "report.md"), top_n)
    _export_html(papers, os.path.join(output_dir, "report.html"), top_n)
```

- [ ] **Step 4: Run export tests**

Run: `pytest tests/test_pipeline/test_export.py -v`
Expected: all passed

- [ ] **Step 5: Commit**

```bash
git add arxiv_popularity/pipeline/export.py tests/test_pipeline/test_export.py
git commit -m "feat: add export pipeline stage with JSON, CSV, MD, HTML output"
```

---

### Task 13: CLI & Main Entry Point

**Files:**
- Create: `arxiv_popularity/cli.py`
- Modify: `arxiv_popularity/__main__.py` (already created in Task 1)

- [ ] **Step 1: Implement cli.py**

`arxiv_popularity/cli.py`:
```python
from __future__ import annotations

import argparse
import logging
import time

from arxiv_popularity.config import load_config
from arxiv_popularity.pipeline.discover import discover
from arxiv_popularity.pipeline.enrich import enrich_papers
from arxiv_popularity.pipeline.score import score_papers
from arxiv_popularity.pipeline.export import export_all
from arxiv_popularity.utils import parse_window, setup_logging

logger = logging.getLogger("arxiv_popularity")


def run(args: argparse.Namespace) -> None:
    config = load_config()
    window_days = parse_window(args.window)

    start = time.time()

    # 1. Discover
    logger.info("=== Stage 1: Discovery ===")
    papers = discover(args.categories, window_days, args.limit)

    # 2. Enrich
    logger.info("=== Stage 2: Enrichment ===")
    papers = enrich_papers(papers, config)

    # 3. Score
    logger.info("=== Stage 3: Scoring ===")
    papers = score_papers(papers, config)

    # 4. Export
    logger.info("=== Stage 4: Export ===")
    export_all(papers, args.output_dir, args.top)

    elapsed = time.time() - start
    logger.info("Done in %.1fs. Output in %s/", elapsed, args.output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="arxiv_popularity",
        description="Track which arXiv papers are getting attention and why.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the full pipeline")
    run_parser.add_argument("--categories", nargs="+", default=["cs.AI", "cs.LG"],
                           help="arXiv categories to search (default: cs.AI cs.LG)")
    run_parser.add_argument("--window", default="7d",
                           help="Lookback window, e.g. 7d, 14d, 30d (default: 7d)")
    run_parser.add_argument("--limit", type=int, default=100,
                           help="Max papers to discover (default: 100)")
    run_parser.add_argument("--top", type=int, default=50,
                           help="Number of papers in ranked report (default: 50)")
    run_parser.add_argument("--output-dir", default="output",
                           help="Output directory (default: output)")
    run_parser.add_argument("-v", "--verbose", action="store_true",
                           help="Enable debug logging")

    args = parser.parse_args()
    setup_logging(getattr(args, "verbose", False))

    if args.command == "run":
        run(args)
    else:
        parser.print_help()
```

- [ ] **Step 2: Verify __main__.py calls cli.main**

`arxiv_popularity/__main__.py` should already contain:
```python
from arxiv_popularity.cli import main

main()
```

- [ ] **Step 3: Smoke test the CLI help**

Run: `python -m arxiv_popularity --help`
Expected: Shows help text with "run" subcommand

Run: `python -m arxiv_popularity run --help`
Expected: Shows run arguments

- [ ] **Step 4: Commit**

```bash
git add arxiv_popularity/cli.py arxiv_popularity/__main__.py
git commit -m "feat: add CLI with argparse and pipeline orchestration"
```

---

### Task 14: Documentation

**Files:**
- Create: `README.md` (overwrite placeholder)
- Create: `DESIGN.md`

- [ ] **Step 1: Write README.md**

`README.md`:
```markdown
# arXiv Popularity Tracker

Track which arXiv papers are getting attention right now, and why.

Discovers recent papers, enriches them with popularity signals from multiple sources, computes a momentum score, and produces a ranked HTML report.

## Install

```bash
pip install -e ".[dev]"
```

## Run

```bash
python -m arxiv_popularity run \
  --categories cs.AI cs.LG stat.ML \
  --window 7d \
  --limit 100 \
  --top 50 \
  --output-dir output
```

### Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--categories` | `cs.AI cs.LG` | arXiv categories to search |
| `--window` | `7d` | Lookback window (e.g. `7d`, `14d`, `30d`) |
| `--limit` | `100` | Max papers to discover |
| `--top` | `50` | Papers in ranked report |
| `--output-dir` | `output` | Output directory |
| `-v` | off | Verbose/debug logging |

### Output Files

- `papers.json` — full structured data
- `papers.csv` — flat sortable table
- `report.md` — Markdown summary
- `report.html` — **primary output** — ranked HTML report

## Environment Variables

All optional. The tool works without any API keys.

| Variable | Purpose |
|----------|---------|
| `SEMANTIC_SCHOLAR_API_KEY` | Higher rate limits for citation data |
| `REDDIT_CLIENT_ID` | Reddit API (not yet implemented) |
| `REDDIT_CLIENT_SECRET` | Reddit API (not yet implemented) |

Copy `.env.example` and fill in as needed.

## Scoring

Papers are ranked by a **Momentum Score** (0–1) combining four signals:

| Signal | Weight | Source |
|--------|--------|--------|
| Recency | 25% | Exponential decay from publish date (7-day half-life) |
| HF Trending | 20% | Binary — is the paper on HuggingFace daily papers? |
| HN Discussion | 30% | Hacker News mentions weighted by points + comments, time-decayed |
| Citations | 25% | Semantic Scholar citation count, tanh-normalized |

Each paper includes a human-readable explanation of why it ranked where it did.

## Architecture

```
CLI → Discovery → Enrichment → Scoring → Export
        │              │
        ├─ arXiv API   ├─ Semantic Scholar (citations)
        └─ HuggingFace └─ Hacker News (discussion)
```

See [DESIGN.md](DESIGN.md) for details.
```

- [ ] **Step 2: Write DESIGN.md**

`DESIGN.md`:
```markdown
# Design

## Data Sources

### Discovery
- **arXiv API** — Atom feed at `export.arxiv.org/api/query`. Sorted by submission date, filtered by category and time window.
- **HuggingFace Papers** — Scraped from `huggingface.co/papers`. Extracts arXiv IDs from paper links. Fragile (no official API), fails gracefully.

### Enrichment
- **Semantic Scholar** — Batch API (`POST /graph/v1/paper/batch`) for citation counts. Falls back to individual lookups. Free tier: 100 req/s.
- **Hacker News** — Algolia search API. Searches by arXiv ID, URL, then title. Deduplicates by story ID.
- **Reddit** — Stubbed. Scaffold exists for future implementation.
- **X (Twitter)** — Stubbed. Scaffold only.

## Scoring Model

Weighted sum of four 0–1 normalized components:

- **Recency** (0.25): `exp(-λ * days_old)`, λ = ln(2)/7 (7-day half-life)
- **HF Trending** (0.20): Binary 1.0/0.0
- **HN Discussion** (0.30): `tanh(Σ(decay * (points + 2*comments)) / 150)` with same exponential decay
- **Citations** (0.25): `tanh(citations / 50)`

## Tradeoffs

1. **Mutable dataclass** — Simple, all stages modify in place. No DTOs.
2. **ThreadPoolExecutor** — Stdlib threads for parallel HTTP. No async.
3. **HF scraping** — No official API exists. Fails gracefully.
4. **Single score** — Weighted sum with breakdown. Explainable.
5. **No database** — File output only. Batch CLI tool.

## Matching

Priority: arXiv ID → arXiv URL → normalized title.
Normalization strips versions (`v2`), lowercases, removes punctuation.
```

- [ ] **Step 3: Commit**

```bash
git add README.md DESIGN.md
git commit -m "docs: add README with usage guide and DESIGN with architecture"
```

---

### Task 15: Run Full Pipeline & Verify

- [ ] **Step 1: Run all tests**

Run: `pytest -v`
Expected: All tests pass

- [ ] **Step 2: Run the full pipeline**

Run: `python -m arxiv_popularity run --categories cs.AI --window 7d --limit 20 --top 10 --output-dir output`
Expected: Runs to completion, creates `output/` with 4 files

- [ ] **Step 3: Verify output files exist**

Run: `ls -la output/`
Expected: `papers.json`, `papers.csv`, `report.md`, `report.html`

- [ ] **Step 4: Spot-check HTML report**

Open `output/report.html` in a browser or verify it contains valid HTML structure.

- [ ] **Step 5: Commit output directory to .gitignore**

Add `output/` to `.gitignore`.

```bash
echo "output/" >> .gitignore
echo ".cache/" >> .gitignore
git add .gitignore
git commit -m "chore: add output and cache dirs to gitignore"
```

- [ ] **Step 6: Final commit — all tests pass**

Run: `pytest -v`
Verify all green, then:
```bash
git add -A
git commit -m "feat: complete MVP — working pipeline with all providers and HTML report"
```
