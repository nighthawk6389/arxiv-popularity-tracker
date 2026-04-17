from __future__ import annotations

import csv
import json
import logging
import os
from datetime import datetime, timezone
from html import escape

from arxiv_popularity.models import Paper

logger = logging.getLogger("arxiv_popularity.pipeline.export")


def _fmt_stars(count: int | None) -> str:
    """Format star/upvote counts for display: 1234 -> '1.2k'."""
    if count is None or count <= 0:
        return ""
    if count >= 10_000:
        return f"{count // 1000}k"
    if count >= 1_000:
        return f"{count / 1000:.1f}k"
    return str(count)


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
        "hf_upvotes": paper.hf_upvotes,
        "github_url": paper.github_url,
        "github_stars": paper.github_stars,
        "hn_mention_count": len(paper.hn_mentions),
        "hn_total_points": sum(m.points for m in paper.hn_mentions),
        "score": round(paper.total_score, 4),
        "score_breakdown": {
            "recency": round(paper.score_breakdown.recency, 4),
            "citations": round(paper.score_breakdown.citations, 4),
            "hf_popularity": round(paper.score_breakdown.hf_popularity, 4),
            "hn_discussion": round(paper.score_breakdown.hn_discussion, 4),
            "github_stars": round(paper.score_breakdown.github_stars, 4),
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
        "score", "citation_count", "hn_mention_count", "hf_upvotes",
        "github_stars", "explanation",
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
                "hf_upvotes": p.hf_upvotes if p.hf_upvotes > 0 else "",
                "github_stars": p.github_stars if p.github_stars is not None else "",
                "explanation": p.explanation,
            })
    logger.info("Wrote %s (%d papers)", path, len(papers))


def _export_markdown(papers: list[Paper], path: str, top_n: int) -> None:
    top = papers[:top_n]
    lines = [
        "# arXiv Popularity Report",
        "",
        "*Generated " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + "*",
        "",
        "## Top " + str(len(top)) + " Papers",
        "",
        "| # | Title | Date | Score | Cites | HN | HF | GH | Why |",
        "|---|-------|------|-------|-------|----|----|----|-----|",
    ]
    for i, p in enumerate(top, 1):
        cites = str(p.citation_count) if p.citation_count is not None else "-"
        hn = str(len(p.hn_mentions)) if p.hn_mentions else "0"
        hf = str(p.hf_upvotes) if p.hf_upvotes > 0 else ""
        gh = _fmt_stars(p.github_stars) if p.github_stars else ""
        date = p.published.strftime("%Y-%m-%d")
        safe_title = p.title.replace("|", "\\|")
        safe_explanation = p.explanation.replace("|", "\\|")
        title_link = "[" + safe_title + "](" + p.arxiv_url + ")"
        lines.append(
            "| " + str(i) + " | " + title_link + " | " + date + " | "
            + f"{p.total_score:.3f}" + " | " + cites + " | " + hn + " | " + hf
            + " | " + gh + " | " + safe_explanation + " |"
        )

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    logger.info("Wrote %s (top %d)", path, len(top))


_CSS = """\
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f8f9fa; color: #1a1a2e; padding: 2rem; max-width: 1400px; margin: 0 auto; }
h1 { font-size: 1.5rem; font-weight: 700; margin-bottom: 0.25rem; }
.subtitle { color: #666; font-size: 0.85rem; margin-bottom: 1.5rem; }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
thead { background: #1a1a2e; color: white; }
th { padding: 0.75rem 0.5rem; text-align: left; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
td { padding: 0.6rem 0.5rem; border-bottom: 1px solid #eee; font-size: 0.85rem; vertical-align: top; }
tr:hover { background: #f0f4ff; }
.rank { text-align: center; font-weight: 700; color: #888; width: 2rem; }
.title-cell a { color: #1a1a2e; text-decoration: none; font-weight: 600; line-height: 1.3; }
.title-cell a:hover { color: #4361ee; text-decoration: underline; }
.authors { color: #888; font-size: 0.75rem; margin-top: 0.2rem; }
.date { white-space: nowrap; color: #666; }
.score { min-width: 5rem; }
.score-val { font-weight: 700; font-variant-numeric: tabular-nums; }
.score-bar { height: 4px; background: #eee; border-radius: 2px; margin-top: 3px; }
.score-fill { height: 100%; background: #4361ee; border-radius: 2px; }
.num { text-align: center; font-variant-numeric: tabular-nums; }
.signals { text-align: center; }
.badge { display: inline-block; padding: 0.15rem 0.4rem; border-radius: 3px; font-size: 0.7rem; font-weight: 700; margin: 1px; }
.badge.hf { background: #ffd21e; color: #1a1a2e; }
.badge.gh { background: #2ea44f; color: white; }
.explanation { color: #555; font-size: 0.8rem; max-width: 14rem; }
"""


def _export_html(papers: list[Paper], path: str, top_n: int) -> None:
    top = papers[:top_n]
    rows = []
    for i, p in enumerate(top, 1):
        cites = str(p.citation_count) if p.citation_count is not None else "-"
        hn_count = len(p.hn_mentions)
        hn_points = sum(m.points for m in p.hn_mentions)
        hn_display = str(hn_count) + " (" + str(hn_points) + "pts)" if hn_count else "0"

        # HF upvotes badge
        hf_badge = ""
        if p.hf_upvotes > 0:
            hf_badge = '<span class="badge hf">' + str(p.hf_upvotes) + '</span>'

        # GitHub stars badge
        gh_badge = ""
        if p.github_stars is not None and p.github_stars > 0:
            gh_label = _fmt_stars(p.github_stars)
            gh_badge = '<span class="badge gh">' + gh_label + '</span>'

        date = p.published.strftime("%Y-%m-%d")
        authors_short = ", ".join(p.authors[:3])
        if len(p.authors) > 3:
            authors_short += " +" + str(len(p.authors) - 3)

        score_bar_width = min(100, int(p.total_score * 100))

        rows.append(
            "      <tr>\n"
            "        <td class=\"rank\">" + str(i) + "</td>\n"
            "        <td class=\"title-cell\">\n"
            "          <a href=\"" + escape(p.arxiv_url) + "\" target=\"_blank\">" + escape(p.title) + "</a>\n"
            "          <div class=\"authors\">" + escape(authors_short) + "</div>\n"
            "        </td>\n"
            "        <td class=\"date\">" + date + "</td>\n"
            "        <td class=\"score\">\n"
            "          <div class=\"score-val\">" + f"{p.total_score:.3f}" + "</div>\n"
            "          <div class=\"score-bar\"><div class=\"score-fill\" style=\"width:" + str(score_bar_width) + "%\"></div></div>\n"
            "        </td>\n"
            "        <td class=\"num\">" + cites + "</td>\n"
            "        <td class=\"num\">" + hn_display + "</td>\n"
            "        <td class=\"signals\">" + hf_badge + " " + gh_badge + "</td>\n"
            "        <td class=\"explanation\">" + escape(p.explanation) + "</td>\n"
            "      </tr>"
        )

    table_rows = "\n".join(rows)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html = (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>arXiv Popularity Report</title>\n"
        "<style>\n" + _CSS + "</style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>arXiv Popularity Report</h1>\n"
        "  <p class=\"subtitle\">Top " + str(len(top)) + " papers &mdash; Generated " + generated + "</p>\n"
        "  <table>\n"
        "    <thead>\n"
        "      <tr>\n"
        "        <th>#</th><th>Title</th><th>Date</th><th>Score</th><th>Cites</th><th>HN</th><th>Signals</th><th>Why</th>\n"
        "      </tr>\n"
        "    </thead>\n"
        "    <tbody>\n"
        + table_rows + "\n"
        "    </tbody>\n"
        "  </table>\n"
        "</body>\n"
        "</html>"
    )

    with open(path, "w") as f:
        f.write(html)
    logger.info("Wrote %s (top %d)", path, len(top))


_SUBREDDIT_MAP: dict[str, list[str]] = {
    "cs.AI": ["r/MachineLearning", "r/artificial"],
    "cs.LG": ["r/MachineLearning", "r/deeplearning"],
    "cs.CL": ["r/LanguageTechnology", "r/MachineLearning"],
    "cs.CV": ["r/computervision", "r/MachineLearning"],
    "cs.NE": ["r/MachineLearning"],
    "cs.IR": ["r/MachineLearning", "r/InformationRetrieval"],
    "stat.ML": ["r/MachineLearning", "r/statistics"],
}

_HASHTAG_MAP: dict[str, list[str]] = {
    "cs.AI": ["#AI", "#MachineLearning"],
    "cs.LG": ["#DeepLearning", "#ML"],
    "cs.CL": ["#NLP", "#LLM"],
    "cs.CV": ["#ComputerVision", "#AI"],
    "cs.NE": ["#NeuralNetworks", "#AI"],
    "cs.IR": ["#InformationRetrieval", "#AI"],
    "stat.ML": ["#MachineLearning", "#Statistics"],
}


def _subreddits_for(categories: list[str]) -> list[str]:
    subs: list[str] = []
    for cat in categories:
        for s in _SUBREDDIT_MAP.get(cat, []):
            if s not in subs:
                subs.append(s)
    return subs or ["r/MachineLearning"]


def _hashtags_for(categories: list[str]) -> list[str]:
    tags: list[str] = []
    for cat in categories:
        for t in _HASHTAG_MAP.get(cat, []):
            if t not in tags:
                tags.append(t)
    return tags or ["#AI", "#Research"]


def _make_x_post(paper: Paper) -> str:
    """Build an X/Twitter post under 280 characters."""
    hashtags = " ".join(_hashtags_for(paper.categories))
    link = paper.share_url or paper.arxiv_url
    suffix = f"\n\nEquations explained: {link}\n\n{hashtags}"
    max_title = 280 - len(suffix)
    title = paper.title
    if len(title) > max_title:
        title = title[:max_title - 1] + "\u2026"
    return title + suffix


def _export_social_posts(papers: list[Paper], path: str, top_n: int) -> None:
    shared = [p for p in papers[:top_n] if p.share_url]
    if not shared:
        return

    lines = [
        "# Social Posts",
        "",
        f"*{len(shared)} papers with shareable links*",
        "",
    ]

    for i, p in enumerate(shared, 1):
        subs = ", ".join(_subreddits_for(p.categories))

        # Reddit section
        lines.append(f"## {i}. {p.title}")
        lines.append("")
        lines.append(f"**Suggested subreddits:** {subs}")
        lines.append("")
        lines.append(f"**Post title:** {p.title}")
        lines.append("")
        lines.append("**Post body:**")
        lines.append(f"{p.explanation}.")
        lines.append("")
        lines.append(f"Math-focused explanation with all equations broken down: {p.share_url}")
        lines.append("")
        lines.append(f"Paper: {p.arxiv_url}")
        lines.append("")

        # X section
        x_post = _make_x_post(p)
        lines.append("**X post:**")
        lines.append("```")
        lines.append(x_post)
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    logger.info("Wrote %s (%d papers)", path, len(shared))


def export_all(papers: list[Paper], output_dir: str, top_n: int) -> None:
    os.makedirs(output_dir, exist_ok=True)
    _export_json(papers, os.path.join(output_dir, "papers.json"))
    _export_csv(papers, os.path.join(output_dir, "papers.csv"))
    _export_markdown(papers, os.path.join(output_dir, "report.md"), top_n)
    _export_html(papers, os.path.join(output_dir, "report.html"), top_n)
    _export_social_posts(papers, os.path.join(output_dir, "social_posts.md"), top_n)
