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
| `--share` | off | Share top papers via deconstructedpapers.com and generate social posts (requires `DP_API_KEY`) |
| `-v` | off | Verbose/debug logging |

### Output Files

- `papers.json` — full structured data
- `papers.csv` — flat sortable table
- `report.md` — Markdown summary
- `report.html` — **primary output** — ranked HTML report
- `social_posts.md` — copy-paste Reddit and X posts (only generated with `--share`)

## Environment Variables

All optional unless using `--share`. The tool works without any API keys for basic discovery and ranking.

| Variable | Purpose |
|----------|---------|
| `SEMANTIC_SCHOLAR_API_KEY` | Higher rate limits for citation data |
| `GITHUB_TOKEN` | Higher rate limits for GitHub star counts |
| `DP_API_KEY` | **Required for `--share`** — deconstructedpapers.com API key |
| `DP_BASE_URL` | Override deconstructedpapers.com base URL (default: `https://www.deconstructedpapers.com`) |
| `REDDIT_CLIENT_ID` | Reddit API (not yet implemented) |
| `REDDIT_CLIENT_SECRET` | Reddit API (not yet implemented) |

Copy `.env.example` and fill in as needed.

## Scoring

Papers are ranked by a **Momentum Score** (0-1) combining five signals:

| Signal | Weight | Source |
|--------|--------|--------|
| Recency | 20% | Exponential decay from publish date (7-day half-life) |
| HF Popularity | 20% | HuggingFace daily papers upvote count, tanh-normalized |
| HN Discussion | 25% | Hacker News mentions weighted by points + comments, time-decayed |
| Citations | 20% | Semantic Scholar citation count, tanh-normalized |
| GitHub Stars | 15% | Star count from linked repos, tanh-normalized |

Each paper includes a human-readable explanation of why it ranked where it did.

## Architecture

```
CLI -> Discovery -> Enrichment -> Scoring -> Share (optional) -> Export
        |              |                       |
        +- arXiv API   +- Semantic Scholar     +- deconstructedpapers.com
        +- HuggingFace +- Hacker News
                       +- GitHub
```

See [DESIGN.md](DESIGN.md) for details.

## Tests

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```
