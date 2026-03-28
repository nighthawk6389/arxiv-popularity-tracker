from datetime import datetime, timezone
from arxiv_popularity.models import Paper
from arxiv_popularity.pipeline.score import score_papers
from arxiv_popularity.config import DEFAULT_CONFIG


def _make_paper(arxiv_id: str, citation_count: int = 0) -> Paper:
    return Paper(
        arxiv_id=arxiv_id, title=f"Paper {arxiv_id}", authors=[], abstract="",
        categories=[], published=datetime(2024, 1, 15, tzinfo=timezone.utc),
        updated=datetime(2024, 1, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        citation_count=citation_count,
    )


def test_score_papers_sorts_by_score():
    papers = [_make_paper("2401.11111", citation_count=5), _make_paper("2401.22222", citation_count=500)]
    result = score_papers(papers, DEFAULT_CONFIG)
    assert result[0].arxiv_id == "2401.22222"
    assert result[0].total_score >= result[1].total_score


def test_score_papers_sets_breakdown():
    papers = [_make_paper("2401.11111")]
    result = score_papers(papers, DEFAULT_CONFIG)
    assert result[0].score_breakdown is not None
    assert result[0].explanation != ""
