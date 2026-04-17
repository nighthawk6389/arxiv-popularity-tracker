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


def _make_shared_paper(arxiv_id: str = "2401.12345") -> Paper:
    p = _make_scored_paper(arxiv_id)
    p.share_url = f"https://www.deconstructedpapers.com/papers/{arxiv_id}"
    return p


def test_social_posts_created_when_share_urls_present(tmp_path):
    papers = [_make_shared_paper()]
    export_all(papers, output_dir=str(tmp_path), top_n=50)
    assert (tmp_path / "social_posts.md").exists()


def test_social_posts_not_created_without_share_urls(tmp_path):
    papers = [_make_scored_paper()]
    export_all(papers, output_dir=str(tmp_path), top_n=50)
    assert not (tmp_path / "social_posts.md").exists()


def test_social_posts_contain_share_url(tmp_path):
    papers = [_make_shared_paper()]
    export_all(papers, output_dir=str(tmp_path), top_n=50)
    content = (tmp_path / "social_posts.md").read_text()
    assert "deconstructedpapers.com/papers/2401.12345" in content
    assert "Test Paper" in content


def test_social_posts_contain_subreddit_suggestions(tmp_path):
    papers = [_make_shared_paper()]
    export_all(papers, output_dir=str(tmp_path), top_n=50)
    content = (tmp_path / "social_posts.md").read_text()
    assert "r/MachineLearning" in content


def test_social_posts_x_post_under_280_chars(tmp_path):
    p = _make_shared_paper()
    p.title = "A" * 300  # very long title
    export_all([p], output_dir=str(tmp_path), top_n=50)
    content = (tmp_path / "social_posts.md").read_text()
    # Extract the X post between ``` markers
    blocks = content.split("```")
    for block in blocks[1::2]:  # odd-indexed blocks are inside ```
        assert len(block.strip()) <= 280


def test_social_posts_contain_hashtags(tmp_path):
    papers = [_make_shared_paper()]
    export_all(papers, output_dir=str(tmp_path), top_n=50)
    content = (tmp_path / "social_posts.md").read_text()
    assert "#AI" in content or "#MachineLearning" in content
