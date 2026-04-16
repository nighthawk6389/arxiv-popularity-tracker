from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from arxiv_popularity.models import Paper
from arxiv_popularity.providers.github import enrich, _parse_repo, _fetch_stars


def _make_paper(arxiv_id: str = "2401.12345", github_url: str | None = None) -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title="Test", authors=[], abstract="",
        categories=[], published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        github_url=github_url,
    )


class TestParseRepo:
    def test_basic_url(self):
        assert _parse_repo("https://github.com/owner/repo") == ("owner", "repo")

    def test_trailing_slash(self):
        assert _parse_repo("https://github.com/owner/repo/") == ("owner", "repo")

    def test_git_suffix(self):
        assert _parse_repo("https://github.com/owner/repo.git") == ("owner", "repo")

    def test_invalid_url(self):
        assert _parse_repo("https://example.com/foo") is None

    def test_missing_repo(self):
        assert _parse_repo("https://github.com/owner") is None


class TestFetchStars:
    def test_success(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"stargazers_count": 1234}
        with patch("arxiv_popularity.providers.github.fetch_with_retry", return_value=mock_resp):
            assert _fetch_stars("owner", "repo") == 1234

    def test_failure_returns_none(self):
        with patch("arxiv_popularity.providers.github.fetch_with_retry", side_effect=Exception("err")):
            assert _fetch_stars("owner", "repo") is None


class TestEnrich:
    def test_enriches_papers_with_github_url(self):
        paper = _make_paper(github_url="https://github.com/owner/repo")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"stargazers_count": 500}
        with patch("arxiv_popularity.providers.github.fetch_with_retry", return_value=mock_resp):
            enrich([paper])
        assert paper.github_stars == 500

    def test_skips_papers_without_github_url(self):
        paper = _make_paper(github_url=None)
        result = enrich([paper])
        assert paper.github_stars is None

    def test_skips_already_enriched(self):
        paper = _make_paper(github_url="https://github.com/owner/repo")
        paper.github_stars = 100
        with patch("arxiv_popularity.providers.github.fetch_with_retry") as mock_fetch:
            enrich([paper])
            mock_fetch.assert_not_called()
