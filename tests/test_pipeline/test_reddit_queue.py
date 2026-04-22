import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from arxiv_popularity.models import Paper, ScoreBreakdown
from arxiv_popularity.pipeline.reddit_queue import (
    build_queue,
    choose_subreddit,
    generate_reddit_outputs,
    load_history,
)


def _make_paper(
    arxiv_id: str = "2401.00001",
    *,
    title: str = "Paper Title",
    categories: list[str] | None = None,
    hf_trending: bool = True,
    share_url: str | None = None,
    total_score: float = 0.5,
    hf_trending_rank: int | None = 3,
    hf_upvotes: int = 42,
    explanation: str = "Trending on HF",
) -> Paper:
    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        authors=["Alice", "Bob"],
        abstract="Abstract",
        categories=categories if categories is not None else ["cs.LG"],
        published=datetime(2026, 4, 15, tzinfo=timezone.utc),
        updated=datetime(2026, 4, 15, tzinfo=timezone.utc),
        arxiv_url=f"https://arxiv.org/abs/{arxiv_id}",
        pdf_url=f"https://arxiv.org/pdf/{arxiv_id}",
        hf_trending=hf_trending,
        hf_trending_rank=hf_trending_rank,
        hf_upvotes=hf_upvotes,
        share_url=share_url if share_url is not None else (
            f"https://www.deconstructedpapers.com/papers/{arxiv_id}"
        ),
        total_score=total_score,
        score_breakdown=ScoreBreakdown(0.9, 0.4, 0.9, 0.2, 0.0),
        explanation=explanation,
    )


# --- choose_subreddit ---------------------------------------------------------

def test_choose_subreddit_cs_cl():
    assert choose_subreddit(["cs.CL"]) == "r/LanguageTechnology"


def test_choose_subreddit_cs_cv():
    assert choose_subreddit(["cs.CV"]) == "r/computervision"


def test_choose_subreddit_cs_lg():
    assert choose_subreddit(["cs.LG"]) == "r/MachineLearning"


def test_choose_subreddit_stat_ml():
    assert choose_subreddit(["stat.ML"]) == "r/MachineLearning"


def test_choose_subreddit_cs_ai_goes_to_ml_not_artificial():
    # r/artificial is avoided by default
    result = choose_subreddit(["cs.AI"])
    assert result == "r/MachineLearning"
    assert result != "r/artificial"


def test_choose_subreddit_cs_ne_and_cs_ir_go_to_ml():
    assert choose_subreddit(["cs.NE"]) == "r/MachineLearning"
    assert choose_subreddit(["cs.IR"]) == "r/MachineLearning"


def test_choose_subreddit_cl_wins_over_cv():
    # deterministic preference: cs.CL beats cs.CV when both present
    assert choose_subreddit(["cs.CV", "cs.CL"]) == "r/LanguageTechnology"


def test_choose_subreddit_cv_wins_over_ml():
    assert choose_subreddit(["cs.LG", "cs.CV"]) == "r/computervision"


def test_choose_subreddit_fallback_unknown_category():
    assert choose_subreddit(["q-bio.NC"]) == "r/MachineLearning"


def test_choose_subreddit_empty_categories():
    assert choose_subreddit([]) == "r/MachineLearning"


# --- build_queue filtering ----------------------------------------------------

def test_build_queue_requires_hf_trending():
    p = _make_paper(hf_trending=False)
    selected, skipped = build_queue([p], history={})
    assert selected == []


def test_build_queue_requires_share_url():
    p = _make_paper(share_url="")
    p.share_url = None
    selected, _ = build_queue([p], history={})
    assert selected == []


def test_build_queue_selects_qualifying_paper():
    p = _make_paper()
    selected, _ = build_queue([p], history={})
    assert len(selected) == 1
    assert selected[0].arxiv_id == p.arxiv_id


def test_build_queue_caps_at_five():
    papers = [
        _make_paper(arxiv_id=f"2401.0000{i}", total_score=1.0 - i * 0.01)
        for i in range(10)
    ]
    selected, _ = build_queue(papers, history={})
    assert len(selected) == 5


def test_build_queue_emits_fewer_than_three_when_few_qualify():
    # only one qualifies - should still emit 1, not force junk
    good = _make_paper(arxiv_id="2401.00001")
    bad = _make_paper(arxiv_id="2401.00002", hf_trending=False)
    selected, _ = build_queue([good, bad], history={})
    assert len(selected) == 1


def test_build_queue_orders_by_total_score_descending():
    low = _make_paper(arxiv_id="2401.11111", total_score=0.2)
    high = _make_paper(arxiv_id="2401.22222", total_score=0.9)
    mid = _make_paper(arxiv_id="2401.33333", total_score=0.5)
    selected, _ = build_queue([low, high, mid], history={})
    assert [p.arxiv_id for p in selected] == ["2401.22222", "2401.33333", "2401.11111"]


# --- history / repeat suppression ---------------------------------------------

def test_build_queue_skips_paper_posted_within_14_days():
    now = datetime(2026, 4, 18, tzinfo=timezone.utc)
    recent = (now - timedelta(days=5)).isoformat()
    p = _make_paper(arxiv_id="2401.55555")
    history = {"posts": [{"arxiv_id": "2401.55555", "posted_at": recent}]}

    selected, skipped = build_queue([p], history=history, now=now)
    assert selected == []
    assert len(skipped) == 1
    assert skipped[0]["arxiv_id"] == "2401.55555"
    assert skipped[0]["reason"] == "recently_posted"


def test_build_queue_allows_paper_posted_over_14_days_ago():
    now = datetime(2026, 4, 18, tzinfo=timezone.utc)
    old = (now - timedelta(days=20)).isoformat()
    p = _make_paper(arxiv_id="2401.66666")
    history = {"posts": [{"arxiv_id": "2401.66666", "posted_at": old}]}

    selected, _ = build_queue([p], history=history, now=now)
    assert len(selected) == 1
    assert selected[0].arxiv_id == "2401.66666"


def test_build_queue_handles_missing_posts_key_in_history():
    p = _make_paper()
    selected, _ = build_queue([p], history={})
    assert len(selected) == 1


# --- load_history -------------------------------------------------------------

def test_load_history_missing_file_returns_empty(tmp_path):
    path = tmp_path / "does_not_exist.json"
    result = load_history(str(path))
    assert result == {"posts": []}


def test_load_history_reads_existing(tmp_path):
    path = tmp_path / "history.json"
    path.write_text(json.dumps({
        "posts": [{"arxiv_id": "1.1", "posted_at": "2026-01-01T00:00:00+00:00"}]
    }))
    result = load_history(str(path))
    assert result["posts"][0]["arxiv_id"] == "1.1"


# --- outputs ------------------------------------------------------------------

def test_generate_reddit_outputs_creates_both_files(tmp_path):
    p = _make_paper()
    history_path = tmp_path / "history.json"
    generate_reddit_outputs(
        [p],
        output_dir=str(tmp_path),
        history_path=str(history_path),
    )
    assert (tmp_path / "reddit_review.md").exists()
    assert (tmp_path / "reddit_queue.json").exists()


def test_queue_json_has_expected_fields(tmp_path):
    p = _make_paper(arxiv_id="2401.77777", categories=["cs.CL"])
    history_path = tmp_path / "history.json"
    generate_reddit_outputs(
        [p], output_dir=str(tmp_path), history_path=str(history_path)
    )
    data = json.loads((tmp_path / "reddit_queue.json").read_text())
    assert len(data) == 1
    entry = data[0]
    required = {
        "arxiv_id", "title", "subreddit", "body", "share_url", "arxiv_url",
        "hf_trending_rank", "hf_upvotes", "score", "explanation", "categories",
    }
    assert required.issubset(entry.keys())
    assert entry["arxiv_id"] == "2401.77777"
    assert entry["subreddit"] == "r/LanguageTechnology"
    assert entry["share_url"].endswith("/papers/2401.77777")


def test_queue_body_contains_share_url_and_arxiv_url(tmp_path):
    p = _make_paper(arxiv_id="2401.88888")
    history_path = tmp_path / "history.json"
    generate_reddit_outputs(
        [p], output_dir=str(tmp_path), history_path=str(history_path)
    )
    data = json.loads((tmp_path / "reddit_queue.json").read_text())
    body = data[0]["body"]
    assert "deconstructedpapers.com/papers/2401.88888" in body
    assert "arxiv.org/abs/2401.88888" in body


def test_review_md_lists_selected_papers(tmp_path):
    p = _make_paper(arxiv_id="2401.99999", title="My Shiny Paper")
    history_path = tmp_path / "history.json"
    generate_reddit_outputs(
        [p], output_dir=str(tmp_path), history_path=str(history_path)
    )
    content = (tmp_path / "reddit_review.md").read_text()
    assert "My Shiny Paper" in content
    assert "2401.99999" in content
    assert "r/MachineLearning" in content


def test_review_md_shows_skipped_section_when_applicable(tmp_path):
    now = datetime(2026, 4, 18, tzinfo=timezone.utc)
    recent = (now - timedelta(days=3)).isoformat()
    p = _make_paper(arxiv_id="2401.42424", title="Recently Posted")
    history_path = tmp_path / "history.json"
    history_path.write_text(json.dumps({
        "posts": [{"arxiv_id": "2401.42424", "posted_at": recent}]
    }))
    generate_reddit_outputs(
        [p], output_dir=str(tmp_path),
        history_path=str(history_path),
        now=now,
    )
    content = (tmp_path / "reddit_review.md").read_text()
    assert "Skipped" in content or "skipped" in content
    assert "2401.42424" in content


def test_review_md_no_skipped_section_when_nothing_skipped(tmp_path):
    p = _make_paper()
    history_path = tmp_path / "history.json"
    generate_reddit_outputs(
        [p], output_dir=str(tmp_path), history_path=str(history_path)
    )
    content = (tmp_path / "reddit_review.md").read_text()
    # There should not be a "Skipped" heading when no paper was filtered out
    assert "## Skipped" not in content


def test_generate_reddit_outputs_writes_empty_queue_when_nothing_qualifies(tmp_path):
    p = _make_paper(hf_trending=False)
    history_path = tmp_path / "history.json"
    generate_reddit_outputs(
        [p], output_dir=str(tmp_path), history_path=str(history_path)
    )
    data = json.loads((tmp_path / "reddit_queue.json").read_text())
    assert data == []
    # md file should still exist
    assert (tmp_path / "reddit_review.md").exists()


def test_generate_reddit_outputs_does_not_mutate_history_file(tmp_path):
    # queue generation should NOT write to history (posting is out of scope)
    p = _make_paper()
    history_path = tmp_path / "history.json"
    history_path.write_text(json.dumps({"posts": []}))
    before = history_path.read_text()
    generate_reddit_outputs(
        [p], output_dir=str(tmp_path), history_path=str(history_path)
    )
    after = history_path.read_text()
    assert before == after
