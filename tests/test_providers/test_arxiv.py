from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from arxiv_popularity.providers.arxiv import fetch_arxiv_papers, _parse_entry


SAMPLE_ENTRY = {
    "id": "http://arxiv.org/abs/2401.12345v1",
    "title": "Test Paper Title",
    "summary": "This is a test abstract.",
    "authors": [{"name": "Alice"}, {"name": "Bob"}],
    "published": "2024-01-15T00:00:00Z",
    "updated": "2024-01-15T00:00:00Z",
    "arxiv_primary_category": {"term": "cs.AI"},
    "tags": [{"term": "cs.AI"}, {"term": "cs.LG"}],
    "links": [
        {"href": "http://arxiv.org/abs/2401.12345v1", "type": "text/html"},
        {"href": "http://arxiv.org/pdf/2401.12345v1", "type": "application/pdf", "title": "pdf"},
    ],
}


def test_parse_entry():
    paper = _parse_entry(SAMPLE_ENTRY)
    assert paper.arxiv_id == "2401.12345"
    assert paper.title == "Test Paper Title"
    assert paper.authors == ["Alice", "Bob"]
    assert paper.categories == ["cs.AI", "cs.LG"]
    assert paper.arxiv_url == "https://arxiv.org/abs/2401.12345"
    assert paper.pdf_url == "https://arxiv.org/pdf/2401.12345"


def test_fetch_arxiv_papers_filters_by_window():
    with patch("arxiv_popularity.providers.arxiv.feedparser") as mock_fp:
        old_entry = {**SAMPLE_ENTRY, "published": "2020-01-01T00:00:00Z", "updated": "2020-01-01T00:00:00Z"}
        mock_fp.parse.return_value = MagicMock(entries=[SAMPLE_ENTRY, old_entry])
        papers = fetch_arxiv_papers(categories=["cs.AI"], window_days=7, limit=100)
        assert isinstance(papers, list)
