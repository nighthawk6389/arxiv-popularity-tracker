# arXiv Popularity Tracker — Design Spec

## Problem

"Which arXiv papers are actually getting attention right now, and why?"

A Python CLI tool that discovers recent arXiv papers, enriches them with popularity signals from multiple sources, scores them, and produces a ranked HTML report.

## Architecture

Sequential pipeline: `discover → enrich → score → export`. Each stage operates on a shared `list[Paper]` dataclass. Enrichment uses `ThreadPoolExecutor` internally for parallel HTTP calls. No database, no async, no background workers.

```
CLI (argparse)
  │
  ▼
Discovery ──► arXiv API + HuggingFace Papers
  │
  ▼
Enrichment ──► Semantic Scholar (citations) + HN Algolia (discussion)
  │               [ThreadPoolExecutor per provider]
  ▼
Scoring ──► Weighted sum of 4 normalized components
  │
  ▼
Export ──► JSON + CSV + Markdown + HTML report
```

## Data Model

### Paper (core dataclass)

```python
@dataclass
class Paper:
    arxiv_id: str                    # e.g. "2401.12345"
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published: datetime
    updated: datetime
    arxiv_url: str
    pdf_url: str

    # Enrichment (populated by providers)
    citation_count: int | None = None
    semantic_scholar_id: str | None = None
    hf_trending: bool = False
    hf_trending_rank: int | None = None
    hn_mentions: list[HNMention] = field(default_factory=list)

    # Scoring (populated by scoring stage)
    total_score: float = 0.0
    score_breakdown: ScoreBreakdown | None = None
    explanation: str = ""
```

### HNMention

```python
@dataclass
class HNMention:
    story_id: int
    title: str
    points: int
    num_comments: int
    created_at: datetime
    url: str
```

### ScoreBreakdown

```python
@dataclass
class ScoreBreakdown:
    recency: float
    citations: float
    hf_trending: float
    hn_discussion: float
```

A single mutable `Paper` flows through all stages. Fields are progressively filled — no separate DTOs.

## CLI Interface

```bash
python -m arxiv_popularity run \
  --categories cs.AI cs.LG stat.ML \
  --window 7d \
  --limit 100 \
  --top 50 \
  --output-dir output
```

Arguments:
- `--categories`: arXiv category codes (default: `cs.AI cs.LG`)
- `--window`: lookback window in days, format `Nd` where N is an integer (e.g. `7d`, `14d`, `30d`). Other units not supported for MVP. Invalid format raises an error. (default: `7d`)
- `--limit`: max papers to discover (default: `100`)
- `--top`: how many to include in the ranked report (default: `50`)
- `--output-dir`: where to write output files (default: `output`)

## Pipeline Stages

### 1. Discovery

**arXiv API** — Query the Atom feed API (`export.arxiv.org/api/query`) by category, filtered by `--window`. The API supports `max_results` up to 1000 per request, which is sufficient for MVP limits. For `--limit` values above that, paginate using `start` offset. Parse XML response with `feedparser` into `Paper` objects.

**HuggingFace Papers** — Fetch `huggingface.co/papers` (the daily papers listing page). The page embeds paper data in a JSON script tag or structured HTML. Extract arXiv IDs from paper links (which follow the pattern `huggingface.co/papers/{arxiv_id}`). If the page structure changes, fail gracefully and log a warning. Match against discovered papers and mark `hf_trending=True`. Any HF papers not already in the candidate list get fetched from arXiv and added.

**Deduplication** — By normalized arXiv ID (strip version suffix: `2401.12345v2` → `2401.12345`).

### 2. Enrichment

Each provider has signature `def enrich(papers: list[Paper]) -> list[Paper]` and uses `ThreadPoolExecutor(max_workers=8)` internally.

**Semantic Scholar** — Use the batch endpoint (`POST /graph/v1/paper/batch`) with arXiv IDs, up to 500 per request. Falls back to individual `GET /paper/arXiv:{id}` requests if batch fails. Populates `citation_count` and `semantic_scholar_id`. Free tier: 100 req/s unauthenticated. Optional `SEMANTIC_SCHOLAR_API_KEY` for higher limits.

**Hacker News** (Algolia API) — For each paper:
1. Search by arXiv ID
2. Search by arXiv URL
3. Fallback to normalized title

Dedupe HN stories by `story_id`. Populates `hn_mentions`.

**Stubbed providers:**
- Reddit — scaffold, skips with log message. Env vars: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`
- X — scaffold only, logs "not implemented"

**Error handling:** Each provider catches all exceptions per-paper, logs failures, continues with remaining papers. A provider failure never crashes the pipeline.

### 3. Scoring

Weighted sum of four normalized components (each 0–1):

| Component | Weight | Method |
|-----------|--------|--------|
| Recency | 0.25 | `exp(-λ * days_old)`, λ tuned so 7 days ≈ 0.5 |
| HF Trending | 0.20 | Binary: 1.0 if trending, 0.0 otherwise |
| HN Discussion | 0.30 | `tanh(Σ(decay * (points + 2*comments)) / scale)` where `decay = exp(-λ * story_age_days)` using same λ as recency |
| Citations | 0.25 | `tanh(citations / 50)` |

**Formula:** `total = 0.25*recency + 0.20*hf + 0.30*hn + 0.25*citations`

**Explanation generator** — Rule-based templates:
- Top component > 50% of weighted score → "Driven mainly by {component}"
- Two components each > 30% → "Strong {X} and {Y} signal"
- Recent + trending → "New breakout paper"
- Fallback (no component dominates) → "Balanced signals across sources"

### 4. Export

All files written to `--output-dir`:

- **papers.json** — Full structured data, all papers
- **papers.csv** — Flat table, all papers. List fields flattened: `authors` as semicolon-delimited string, `hn_mentions` as integer count (detail in JSON only), `categories` as semicolon-delimited
- **report.md** — Markdown summary, top N
- **report.html** — Primary output, top N ranked report

**HTML report requirements:**
- Clean table layout with columns: rank, title (linked), authors, date, score, citations, HN mentions, HF badge, explanation
- Minimal inline CSS, no external dependencies
- Optimized for quick scanning
- Self-contained single file

## Matching Utilities

```python
def normalize_arxiv_id(raw: str) -> str
    # "2401.12345v2" → "2401.12345"

def extract_arxiv_id_from_url(url: str) -> str | None
    # "https://arxiv.org/abs/2401.12345" → "2401.12345"

def normalize_title(title: str) -> str
    # lowercase, strip punctuation, collapse whitespace
```

Matching priority: arXiv ID → arXiv URL → normalized title → fuzzy title (conservative threshold).

## Configuration

All tunable values in `config.py`:

```python
DEFAULT_CONFIG = {
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
```

Environment variables (all optional):
- `SEMANTIC_SCHOLAR_API_KEY`
- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`

## Project Structure

```
arxiv_popularity/
  __init__.py
  __main__.py
  cli.py
  config.py
  models.py
  scoring.py
  matching.py
  utils.py
  providers/
    __init__.py
    arxiv.py
    huggingface.py
    semantic_scholar.py
    hackernews.py
    reddit.py
    x.py
  pipeline/
    __init__.py
    discover.py
    enrich.py
    score.py
    export.py
```

### Module Responsibilities

- `cli.py` — argparse setup, entry point
- `config.py` — default config dict, env var loading
- `models.py` — Paper, HNMention, ScoreBreakdown dataclasses
- `scoring.py` — score computation and explanation generation
- `matching.py` — arXiv ID normalization, title normalization, matching utilities
- `utils.py` — shared helpers: HTTP request with retry/backoff, window string parsing, logging setup
- `pipeline/discover.py` — orchestrates arXiv + HF discovery and dedup
- `pipeline/enrich.py` — orchestrates enrichment providers
- `pipeline/score.py` — calls scoring on each paper
- `pipeline/export.py` — writes JSON, CSV, Markdown, and HTML report files

## Dependencies

- `requests` — HTTP calls
- `feedparser` — arXiv Atom feed parsing
- Standard library only otherwise (`dataclasses`, `concurrent.futures`, `argparse`, `json`, `csv`, `html`, `math`, `re`, `logging`)

## Caching

Simple file-based cache in `.cache/` directory, keyed by `{provider}_{arxiv_id}_{YYYY-MM-DD}.json` where the date is today's date (UTC). Cache entries naturally expire after one calendar day. Cache is optional — if the file is missing or unreadable, re-fetch. No explicit invalidation logic needed.

## What Is Stubbed

- Reddit provider — scaffold with env var check, returns empty results
- X provider — scaffold only, logs "not implemented"
- Fuzzy title matching — conservative, only used as last-resort fallback

## Tradeoffs

1. **Mutable dataclass vs immutable pipeline** — Chose mutable for simplicity. Each stage modifies in place. Acceptable for a single-threaded pipeline with parallel enrichment contained within each provider.

2. **ThreadPoolExecutor vs asyncio** — Threads are simpler, stdlib-only, sufficient for I/O-bound HTTP calls. No need for async complexity.

3. **HuggingFace scraping vs API** — HF has no official "trending papers" API. Scraping the daily page is fragile but the only option. Fails gracefully if the page format changes.

4. **Single score vs multi-dimensional** — A single weighted sum is simpler to understand and sort by. The score breakdown provides transparency. Good enough for MVP.

5. **No database** — File output only. For a batch CLI tool producing a static report, a database adds complexity without benefit.
