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
