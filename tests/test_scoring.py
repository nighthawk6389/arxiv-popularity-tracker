import math
from datetime import datetime, timezone, timedelta
from arxiv_popularity.models import Paper, HNMention, ScoreBreakdown
from arxiv_popularity.scoring import score_paper, generate_explanation
from arxiv_popularity.config import DEFAULT_CONFIG


def _make_paper(**overrides) -> Paper:
    defaults = dict(
        arxiv_id="2401.12345", title="Test", authors=[], abstract="",
        categories=[], published=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
        arxiv_url="https://arxiv.org/abs/2401.12345",
        pdf_url="https://arxiv.org/pdf/2401.12345",
    )
    defaults.update(overrides)
    return Paper(**defaults)


def test_brand_new_paper_has_high_recency():
    paper = _make_paper()
    score_paper(paper, DEFAULT_CONFIG)
    assert paper.score_breakdown.recency > 0.9


def test_old_paper_has_low_recency():
    paper = _make_paper(published=datetime.now(timezone.utc) - timedelta(days=30))
    score_paper(paper, DEFAULT_CONFIG)
    assert paper.score_breakdown.recency < 0.1


def test_hf_trending_boosts_score():
    p1 = _make_paper(hf_trending=False)
    p2 = _make_paper(hf_trending=True)
    score_paper(p1, DEFAULT_CONFIG)
    score_paper(p2, DEFAULT_CONFIG)
    assert p2.total_score > p1.total_score


def test_citations_contribute_to_score():
    p1 = _make_paper(citation_count=0)
    p2 = _make_paper(citation_count=100)
    score_paper(p1, DEFAULT_CONFIG)
    score_paper(p2, DEFAULT_CONFIG)
    assert p2.total_score > p1.total_score


def test_hn_mentions_contribute_to_score():
    mention = HNMention(
        story_id=1, title="HN", points=200, num_comments=100,
        created_at=datetime.now(timezone.utc), url="u",
    )
    p1 = _make_paper()
    p2 = _make_paper()
    p2.hn_mentions = [mention]
    score_paper(p1, DEFAULT_CONFIG)
    score_paper(p2, DEFAULT_CONFIG)
    assert p2.total_score > p1.total_score


def test_explanation_not_empty():
    paper = _make_paper(hf_trending=True, citation_count=50)
    score_paper(paper, DEFAULT_CONFIG)
    assert paper.explanation != ""


def test_score_between_0_and_1():
    paper = _make_paper(hf_trending=True, citation_count=1000)
    mention = HNMention(
        story_id=1, title="HN", points=500, num_comments=200,
        created_at=datetime.now(timezone.utc), url="u",
    )
    paper.hn_mentions = [mention]
    score_paper(paper, DEFAULT_CONFIG)
    assert 0 <= paper.total_score <= 1.0
