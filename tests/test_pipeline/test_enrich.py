from datetime import datetime, timezone
from unittest.mock import patch
from arxiv_popularity.models import Paper
from arxiv_popularity.pipeline.enrich import enrich_papers


def _make_paper(arxiv_id: str = "2401.12345") -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title="Test", authors=[], abstract="",
        categories=[], published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
    )


def test_enrich_skips_disabled_providers():
    papers = [_make_paper()]
    config = {"providers": {"semantic_scholar": False, "hackernews": False, "reddit": False, "x": False}, "thread_pool_size": 2}
    with patch("arxiv_popularity.providers.semantic_scholar.enrich") as mock_s2, \
         patch("arxiv_popularity.providers.hackernews.enrich") as mock_hn:
        result = enrich_papers(papers, config)
        mock_s2.assert_not_called()
        mock_hn.assert_not_called()
    assert len(result) == 1


def test_enrich_calls_enabled_providers():
    papers = [_make_paper()]
    config = {"providers": {"semantic_scholar": True, "hackernews": True, "reddit": False, "x": False}, "thread_pool_size": 2}
    with patch("arxiv_popularity.providers.semantic_scholar.enrich", return_value=papers) as mock_s2, \
         patch("arxiv_popularity.providers.hackernews.enrich", return_value=papers) as mock_hn:
        enrich_papers(papers, config)
        mock_s2.assert_called_once()
        mock_hn.assert_called_once()
