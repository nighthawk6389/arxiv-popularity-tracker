from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from arxiv_popularity.models import Paper

logger = logging.getLogger("arxiv_popularity.pipeline.reddit_queue")

DEFAULT_HISTORY_PATH = "state/reddit_post_history.json"
REPEAT_SUPPRESSION_DAYS = 14
MAX_POSTS_PER_DAY = 5

_ML_CATEGORIES = {"cs.LG", "stat.ML", "cs.AI", "cs.NE", "cs.IR"}


@dataclass
class _Skipped:
    arxiv_id: str
    title: str
    reason: str
    posted_at: str | None = None

    def to_dict(self) -> dict:
        d = {"arxiv_id": self.arxiv_id, "title": self.title, "reason": self.reason}
        if self.posted_at:
            d["posted_at"] = self.posted_at
        return d


def choose_subreddit(categories: list[str]) -> str:
    """Deterministic one-subreddit-per-paper rule. Avoids r/artificial."""
    if "cs.CL" in categories:
        return "r/LanguageTechnology"
    if "cs.CV" in categories:
        return "r/computervision"
    if any(c in _ML_CATEGORIES for c in categories):
        return "r/MachineLearning"
    return "r/MachineLearning"


def load_history(path: str) -> dict:
    """Read the post history JSON file. Returns {'posts': []} if missing."""
    if not os.path.exists(path):
        return {"posts": []}
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("Could not parse history at %s, treating as empty", path)
        return {"posts": []}
    if "posts" not in data or not isinstance(data.get("posts"), list):
        return {"posts": []}
    return data


def _recently_posted_ids(history: dict, now: datetime) -> dict[str, str]:
    """Return {arxiv_id: posted_at_iso} for posts within the suppression window."""
    cutoff = now - timedelta(days=REPEAT_SUPPRESSION_DAYS)
    out: dict[str, str] = {}
    for entry in history.get("posts", []):
        arxiv_id = entry.get("arxiv_id")
        posted_at = entry.get("posted_at")
        if not arxiv_id or not posted_at:
            continue
        try:
            ts = datetime.fromisoformat(posted_at)
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff:
            out[arxiv_id] = posted_at
    return out


def build_queue(
    papers: list[Paper],
    history: dict | None = None,
    max_posts: int = MAX_POSTS_PER_DAY,
    now: datetime | None = None,
) -> tuple[list[Paper], list[dict]]:
    """Select up to max_posts qualifying papers; return (selected, skipped_entries).

    A paper qualifies if it is hf_trending, has a share_url, and was not posted
    to Reddit within the last REPEAT_SUPPRESSION_DAYS days (per history).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    history = history or {}
    recent = _recently_posted_ids(history, now)

    qualifying = [p for p in papers if p.hf_trending and p.share_url]
    qualifying.sort(key=lambda p: p.total_score, reverse=True)

    selected: list[Paper] = []
    skipped: list[_Skipped] = []
    for p in qualifying:
        if p.arxiv_id in recent:
            skipped.append(_Skipped(
                arxiv_id=p.arxiv_id,
                title=p.title,
                reason="recently_posted",
                posted_at=recent[p.arxiv_id],
            ))
            continue
        if len(selected) < max_posts:
            selected.append(p)
    return selected, [s.to_dict() for s in skipped]


def _make_body(paper: Paper) -> str:
    explanation = paper.explanation.rstrip(".")
    lines = [
        f"{explanation}.",
        "",
        f"Math-focused explanation with all equations broken down: {paper.share_url}",
        "",
        f"Paper: {paper.arxiv_url}",
    ]
    return "\n".join(lines)


def _queue_entry(paper: Paper) -> dict:
    return {
        "arxiv_id": paper.arxiv_id,
        "title": paper.title,
        "subreddit": choose_subreddit(paper.categories),
        "body": _make_body(paper),
        "share_url": paper.share_url,
        "arxiv_url": paper.arxiv_url,
        "hf_trending_rank": paper.hf_trending_rank,
        "hf_upvotes": paper.hf_upvotes,
        "score": round(paper.total_score, 4),
        "explanation": paper.explanation,
        "categories": list(paper.categories),
    }


def _write_queue_json(entries: list[dict], path: str) -> None:
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)
    logger.info("Wrote %s (%d entries)", path, len(entries))


def _write_review_markdown(
    entries: list[dict], skipped: list[dict], path: str
) -> None:
    lines = [
        "# Reddit Review Queue",
        "",
        f"*Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
    ]

    if entries:
        lines.append(f"## Selected ({len(entries)})")
        lines.append("")
        for i, e in enumerate(entries, 1):
            lines.append(f"### {i}. {e['title']}")
            lines.append("")
            lines.append(f"- **arXiv:** `{e['arxiv_id']}` — {e['arxiv_url']}")
            lines.append(f"- **Subreddit:** {e['subreddit']}")
            lines.append(
                f"- **Signals:** score={e['score']:.3f}, "
                f"HF rank={e['hf_trending_rank']}, HF upvotes={e['hf_upvotes']}"
            )
            lines.append(f"- **Share URL:** {e['share_url']}")
            lines.append("")
            lines.append("**Post body:**")
            lines.append("")
            lines.append("```")
            lines.append(e["body"])
            lines.append("```")
            lines.append("")
    else:
        lines.append("## Selected (0)")
        lines.append("")
        lines.append("_No papers qualified for the queue._")
        lines.append("")

    if skipped:
        lines.append(f"## Skipped ({len(skipped)})")
        lines.append("")
        lines.append("| arXiv ID | Title | Reason | Posted At |")
        lines.append("|----------|-------|--------|-----------|")
        for s in skipped:
            title = s["title"].replace("|", "\\|")
            lines.append(
                f"| `{s['arxiv_id']}` | {title} | {s['reason']} | "
                f"{s.get('posted_at', '')} |"
            )
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    logger.info("Wrote %s", path)


def generate_reddit_outputs(
    papers: list[Paper],
    output_dir: str,
    history_path: str | None = None,
    max_posts: int = MAX_POSTS_PER_DAY,
    now: datetime | None = None,
) -> list[dict]:
    """Build the queue and write reddit_review.md + reddit_queue.json."""
    os.makedirs(output_dir, exist_ok=True)
    if history_path is None:
        history_path = DEFAULT_HISTORY_PATH
    history = load_history(history_path)

    selected, skipped = build_queue(
        papers, history=history, max_posts=max_posts, now=now,
    )
    entries = [_queue_entry(p) for p in selected]

    _write_queue_json(entries, os.path.join(output_dir, "reddit_queue.json"))
    _write_review_markdown(
        entries, skipped, os.path.join(output_dir, "reddit_review.md"),
    )
    logger.info(
        "Reddit queue: %d selected, %d skipped (suppression window %dd)",
        len(entries), len(skipped), REPEAT_SUPPRESSION_DAYS,
    )
    return entries
