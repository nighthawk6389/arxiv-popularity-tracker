from unittest.mock import patch, MagicMock
from arxiv_popularity.providers.huggingface import (
    fetch_hf_trending_ids,
    fetch_hf_daily_papers,
    get_hf_upvotes,
    get_hf_project_pages,
    get_hf_github_data,
    _extract_arxiv_ids,
    _hf_cache,
)


def _make_api_response():
    """Create a mock HF daily papers API response."""
    return [
        {
            "paper": {
                "id": "2401.12345",
                "upvotes": 42,
                "title": "Cool Paper",
                "projectPage": "https://coolpaper.io",
                "githubRepo": "https://github.com/user/repo",
                "githubStars": 1500,
            }
        },
        {
            "paper": {
                "id": "2401.67890v2",
                "upvotes": 15,
                "title": "Another Paper",
                "projectPage": None,
                "githubRepo": None,
            }
        },
    ]


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
    _hf_cache.clear()
    with patch("arxiv_popularity.providers.huggingface.fetch_with_retry") as mock_fetch:
        mock_fetch.side_effect = Exception("Network error")
        ids = fetch_hf_trending_ids()
        assert ids == []


def test_fetch_hf_daily_papers_parses_json():
    _hf_cache.clear()
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_api_response()
    with patch("arxiv_popularity.providers.huggingface.fetch_with_retry", return_value=mock_resp):
        papers = fetch_hf_daily_papers()
    assert len(papers) == 2
    assert papers[0].arxiv_id == "2401.12345"
    assert papers[0].upvotes == 42
    assert papers[0].title == "Cool Paper"
    assert papers[0].github_repo == "https://github.com/user/repo"
    assert papers[0].github_stars == 1500
    # Version suffix stripped
    assert papers[1].arxiv_id == "2401.67890"
    assert papers[1].upvotes == 15
    assert papers[1].github_repo is None
    assert papers[1].github_stars is None


def test_fetch_passes_sort_trending():
    _hf_cache.clear()
    mock_resp = MagicMock()
    mock_resp.json.return_value = []
    with patch("arxiv_popularity.providers.huggingface.fetch_with_retry", return_value=mock_resp) as mock_fetch:
        fetch_hf_daily_papers(sort="trending")
        call_kwargs = mock_fetch.call_args
        assert call_kwargs.kwargs.get("params", {}).get("sort") == "trending"


def test_get_hf_upvotes_from_cache():
    _hf_cache.clear()
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_api_response()
    with patch("arxiv_popularity.providers.huggingface.fetch_with_retry", return_value=mock_resp):
        fetch_hf_daily_papers()
    upvotes = get_hf_upvotes()
    assert upvotes["2401.12345"] == 42
    assert upvotes["2401.67890"] == 15


def test_get_hf_project_pages_filters_none():
    _hf_cache.clear()
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_api_response()
    with patch("arxiv_popularity.providers.huggingface.fetch_with_retry", return_value=mock_resp):
        fetch_hf_daily_papers()
    pages = get_hf_project_pages()
    assert "2401.12345" in pages
    assert "2401.67890" not in pages


def test_get_hf_github_data():
    _hf_cache.clear()
    mock_resp = MagicMock()
    mock_resp.json.return_value = _make_api_response()
    with patch("arxiv_popularity.providers.huggingface.fetch_with_retry", return_value=mock_resp):
        fetch_hf_daily_papers()
    gh_data = get_hf_github_data()
    assert "2401.12345" in gh_data
    assert gh_data["2401.12345"] == ("https://github.com/user/repo", 1500)
    assert "2401.67890" not in gh_data
