# Design

## Data Sources

### Discovery
- **arXiv API** - Atom feed at `export.arxiv.org/api/query`. Sorted by submission date, filtered by category and time window.
- **HuggingFace Papers** - Scraped from `huggingface.co/papers`. Extracts arXiv IDs from paper links. Fragile (no official API), fails gracefully.

### Enrichment
- **Semantic Scholar** - Batch API (`POST /graph/v1/paper/batch`) for citation counts. Falls back to individual lookups. Free tier: 100 req/s.
- **Hacker News** - Algolia search API. Searches by arXiv ID, URL, then title. Deduplicates by story ID.
- **Reddit** - Stubbed. Scaffold exists for future implementation.
- **X (Twitter)** - Stubbed. Scaffold only.

## Scoring Model

Weighted sum of four 0-1 normalized components:

- **Recency** (0.25): `exp(-l * days_old)`, l = ln(2)/7 (7-day half-life)
- **HF Trending** (0.20): Binary 1.0/0.0
- **HN Discussion** (0.30): `tanh(sum(decay * (points + 2*comments)) / 150)` with same exponential decay
- **Citations** (0.25): `tanh(citations / 50)`

## Tradeoffs

1. **Mutable dataclass** - Simple, all stages modify in place. No DTOs.
2. **ThreadPoolExecutor** - Stdlib threads for parallel HTTP. No async.
3. **HF scraping** - No official API exists. Fails gracefully.
4. **Single score** - Weighted sum with breakdown. Explainable.
5. **No database** - File output only. Batch CLI tool.

## Matching

Priority: arXiv ID -> arXiv URL -> normalized title.
Normalization strips versions (`v2`), lowercases, removes punctuation.
