from datetime import datetime, timezone
from arxiv_popularity.models import Paper, HNMention, ScoreBreakdown


def test_paper_defaults():
    p = Paper(
        arxiv_id="2401.12345",
        title="Test Paper",
        authors=["Author A"],
        abstract="An abstract.",
        categories=["cs.AI"],
        published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url="https://arxiv.org/abs/2401.12345",
        pdf_url="https://arxiv.org/pdf/2401.12345",
    )
    assert p.citation_count is None
    assert p.hf_trending is False
    assert p.hn_mentions == []
    assert p.total_score == 0.0
    assert p.score_breakdown is None
    assert p.explanation == ""


def test_hn_mention():
    m = HNMention(
        story_id=123,
        title="Show HN: cool paper",
        points=100,
        num_comments=50,
        created_at=datetime(2024, 1, 16, tzinfo=timezone.utc),
        url="https://news.ycombinator.com/item?id=123",
    )
    assert m.points == 100
    assert m.num_comments == 50


def test_score_breakdown():
    sb = ScoreBreakdown(recency=0.8, citations=0.3, hf_trending=1.0, hn_discussion=0.5)
    assert sb.recency == 0.8
