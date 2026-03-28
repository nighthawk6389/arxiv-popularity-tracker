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

Papers are ranked by a **Momentum Score** (0-1) combining four signals:

| Signal | Weight | Source |
|--------|--------|--------|
| Recency | 25% | Exponential decay from publish date (7-day half-life) |
| HF Trending | 20% | Binary - is the paper on HuggingFace daily papers? |
| HN Discussion | 30% | Hacker News mentions weighted by points + comments, time-decayed |
| Citations | 25% | Semantic Scholar citation count, tanh-normalized |

Each paper includes a human-readable explanation of why it ranked where it did.

## Architecture

```
CLI -> Discovery -> Enrichment -> Scoring -> Export
        |              |
        +- arXiv API   +- Semantic Scholar (citations)
        +- HuggingFace +- Hacker News (discussion)
```

See [DESIGN.md](DESIGN.md) for details.
