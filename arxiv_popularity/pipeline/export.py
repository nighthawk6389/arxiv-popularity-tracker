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
        "# arXiv Popularity Report",
        "",
        "*Generated " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC") + "*",
        "",
        "## Top " + str(len(top)) + " Papers",
        "",
        "| # | Title | Date | Score | Cites | HN | HF | Why |",
        "|---|-------|------|-------|-------|----|----|-----|",
    ]
    for i, p in enumerate(top, 1):
        cites = str(p.citation_count) if p.citation_count is not None else "-"
        hn = str(len(p.hn_mentions)) if p.hn_mentions else "0"
        hf = "Yes" if p.hf_trending else ""
        date = p.published.strftime("%Y-%m-%d")
        title_link = "[" + p.title + "](" + p.arxiv_url + ")"
        lines.append(
            "| " + str(i) + " | " + title_link + " | " + date + " | "
            + f"{p.total_score:.3f}" + " | " + cites + " | " + hn + " | " + hf
            + " | " + p.explanation + " |"
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
.badges { text-align: center; }
.badge { display: inline-block; padding: 0.15rem 0.4rem; border-radius: 3px; font-size: 0.7rem; font-weight: 700; }
.badge.hf { background: #ffd21e; color: #1a1a2e; }
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
        hf_badge = '<span class="badge hf">HF</span>' if p.hf_trending else ""
        date = p.published.strftime("%Y-%m-%d")
        authors_short = ", ".join(p.authors[:3])
        if len(p.authors) > 3:
            authors_short += " +" + str(len(p.authors) - 3)

        score_bar_width = int(p.total_score * 100)

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
            "        <td class=\"badges\">" + hf_badge + "</td>\n"
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
        "        <th>#</th><th>Title</th><th>Date</th><th>Score</th><th>Cites</th><th>HN</th><th>HF</th><th>Why</th>\n"
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


def export_all(papers: list[Paper], output_dir: str, top_n: int) -> None:
    os.makedirs(output_dir, exist_ok=True)
    _export_json(papers, os.path.join(output_dir, "papers.json"))
    _export_csv(papers, os.path.join(output_dir, "papers.csv"))
    _export_markdown(papers, os.path.join(output_dir, "report.md"), top_n)
    _export_html(papers, os.path.join(output_dir, "report.html"), top_n)
