from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from arxiv_popularity.models import Paper
from arxiv_popularity.pipeline.share import share_papers


def _make_paper(arxiv_id: str = "2401.12345") -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title="Test Paper", authors=["Alice"],
        abstract="Abstract", categories=["cs.AI"],
        published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        total_score=0.75, explanation="Strong signals",
    )


def test_share_skips_when_no_api_key():
    papers = [_make_paper()]
    result = share_papers(papers, {}, top_n=5)
    assert result[0].share_url is None


def test_share_sets_url_on_success():
    papers = [_make_paper()]
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"url": "/papers/abc123", "cached": False}

    config = {"dp_api_key": "dp_live_test", "dp_base_url": "https://www.deconstructedpapers.com"}

    with patch("arxiv_popularity.pipeline.share.fetch_with_retry", return_value=mock_resp), \
         patch("arxiv_popularity.pipeline.share.time.sleep"):
        share_papers(papers, config, top_n=5)

    assert papers[0].share_url == "https://www.deconstructedpapers.com/papers/abc123"


def test_share_handles_api_failure_gracefully():
    papers = [_make_paper()]
    config = {"dp_api_key": "dp_live_test"}

    with patch("arxiv_popularity.pipeline.share.fetch_with_retry", side_effect=Exception("API down")), \
         patch("arxiv_popularity.pipeline.share.time.sleep"):
        result = share_papers(papers, config, top_n=5)

    assert result[0].share_url is None


def test_share_only_processes_top_n():
    papers = [_make_paper(f"2401.{i:05d}") for i in range(10)]
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"url": "/papers/x", "cached": True}
    config = {"dp_api_key": "dp_live_test"}

    with patch("arxiv_popularity.pipeline.share.fetch_with_retry", return_value=mock_resp) as mock_fetch, \
         patch("arxiv_popularity.pipeline.share.time.sleep"):
        share_papers(papers, config, top_n=3)

    assert mock_fetch.call_count == 3
    assert papers[0].share_url is not None
    assert papers[3].share_url is None


def test_share_sleeps_between_papers():
    papers = [_make_paper(f"2401.{i:05d}") for i in range(3)]
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"url": "/papers/x", "cached": True}
    config = {"dp_api_key": "dp_live_test"}

    with patch("arxiv_popularity.pipeline.share.fetch_with_retry", return_value=mock_resp), \
         patch("arxiv_popularity.pipeline.share.time.sleep") as mock_sleep:
        share_papers(papers, config, top_n=3)

    # 3 papers -> 2 sleeps (between papers, not before first or after last)
    assert mock_sleep.call_count == 2
    mock_sleep.assert_called_with(60)
