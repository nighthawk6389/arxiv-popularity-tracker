from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from arxiv_popularity.models import Paper
from arxiv_popularity.providers.hackernews import enrich, _search_hn, _dedupe_mentions


def _make_paper(arxiv_id: str = "2401.12345") -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title="Attention Is All You Need", authors=[], abstract="",
        categories=[], published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
    )


def test_search_hn_returns_mentions():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "hits": [
            {
                "objectID": "123",
                "title": "Attention paper on HN",
                "points": 200,
                "num_comments": 80,
                "created_at": "2024-01-16T12:00:00Z",
                "url": "https://arxiv.org/abs/2401.12345",
            }
        ]
    }
    with patch("arxiv_popularity.providers.hackernews.fetch_with_retry", return_value=mock_resp):
        mentions = _search_hn("2401.12345")
    assert len(mentions) == 1
    assert mentions[0].points == 200


def test_dedupe_mentions():
    from arxiv_popularity.models import HNMention
    m1 = HNMention(story_id=1, title="A", points=10, num_comments=5,
                   created_at=datetime(2024, 1, 15, tzinfo=timezone.utc), url="u1")
    m2 = HNMention(story_id=1, title="A", points=10, num_comments=5,
                   created_at=datetime(2024, 1, 15, tzinfo=timezone.utc), url="u1")
    m3 = HNMention(story_id=2, title="B", points=20, num_comments=10,
                   created_at=datetime(2024, 1, 16, tzinfo=timezone.utc), url="u2")
    result = _dedupe_mentions([m1, m2, m3])
    assert len(result) == 2


def test_enrich_does_not_crash_on_failure():
    paper = _make_paper()
    with patch("arxiv_popularity.providers.hackernews.fetch_with_retry", side_effect=Exception("fail")):
        result = enrich([paper])
    assert result[0].hn_mentions == []
