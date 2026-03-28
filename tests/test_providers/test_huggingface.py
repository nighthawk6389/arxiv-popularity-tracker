from unittest.mock import patch, MagicMock
from arxiv_popularity.providers.huggingface import fetch_hf_trending_ids, _extract_arxiv_ids


def test_extract_arxiv_ids_from_html():
    html = '''
    <a href="/papers/2401.12345">Paper 1</a>
    <a href="/papers/2401.67890">Paper 2</a>
    <a href="/other/link">Not a paper</a>
    '''
    ids = _extract_arxiv_ids(html)
    assert ids == ["2401.12345", "2401.67890"]


def test_extract_arxiv_ids_deduplicates():
    html = '''
    <a href="/papers/2401.12345">Paper 1</a>
    <a href="/papers/2401.12345">Paper 1 again</a>
    '''
    ids = _extract_arxiv_ids(html)
    assert ids == ["2401.12345"]


def test_fetch_hf_trending_returns_empty_on_failure():
    with patch("arxiv_popularity.providers.huggingface.fetch_with_retry") as mock_fetch:
        mock_fetch.side_effect = Exception("Network error")
        ids = fetch_hf_trending_ids()
        assert ids == []
