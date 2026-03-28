from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from arxiv_popularity.models import Paper
from arxiv_popularity.providers.semantic_scholar import enrich


def _make_paper(arxiv_id: str = "2401.12345") -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title="Test", authors=[], abstract="",
        categories=[], published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
    )


def test_enrich_sets_citation_count():
    paper = _make_paper()
    batch_response = MagicMock()
    batch_response.json.return_value = [
        {"paperId": "s2-123", "citationCount": 42, "externalIds": {"ArXiv": "2401.12345"}}
    ]

    with patch("arxiv_popularity.providers.semantic_scholar.fetch_with_retry") as mock_fetch:
        mock_fetch.return_value = batch_response
        result = enrich([paper])
    assert result[0].citation_count == 42
    assert result[0].semantic_scholar_id == "s2-123"


def test_enrich_handles_missing_paper():
    paper = _make_paper()
    batch_response = MagicMock()
    batch_response.json.return_value = [None]

    with patch("arxiv_popularity.providers.semantic_scholar.fetch_with_retry") as mock_fetch:
        mock_fetch.return_value = batch_response
        result = enrich([paper])
    assert result[0].citation_count is None


def test_enrich_handles_batch_failure_with_individual_fallback():
    paper = _make_paper()

    individual_response = MagicMock()
    individual_response.json.return_value = {
        "paperId": "s2-123", "citationCount": 10
    }

    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Batch failed")
        return individual_response

    with patch("arxiv_popularity.providers.semantic_scholar.fetch_with_retry") as mock_fetch:
        mock_fetch.side_effect = side_effect
        result = enrich([paper])
    assert result[0].citation_count == 10
