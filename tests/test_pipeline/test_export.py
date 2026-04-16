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
        citation_count=42, hf_trending=True, hf_upvotes=55, total_score=0.75,
        score_breakdown=ScoreBreakdown(recency=0.9, citations=0.4, hf_popularity=0.9, hn_discussion=0.3, github_stars=0.0),
        explanation="Strong HF popularity and recency signal",
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
