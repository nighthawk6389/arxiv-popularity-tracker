from __future__ import annotations

import math
from datetime import datetime, timezone

from arxiv_popularity.models import Paper, ScoreBreakdown


def _recency_score(paper: Paper, halflife_days: float) -> float:
    age_days = (datetime.now(timezone.utc) - paper.published).total_seconds() / 86400
    lam = math.log(2) / halflife_days
    return math.exp(-lam * max(age_days, 0))


def _hf_score(paper: Paper, scale_factor: float) -> float:
    if paper.hf_upvotes <= 0:
        return 0.0
    return math.tanh(paper.hf_upvotes / scale_factor)


def _hn_score(paper: Paper, halflife_days: float, scale_factor: float) -> float:
    if not paper.hn_mentions:
        return 0.0
    lam = math.log(2) / halflife_days
    total = 0.0
    now = datetime.now(timezone.utc)
    for m in paper.hn_mentions:
        age_days = (now - m.created_at).total_seconds() / 86400
        decay = math.exp(-lam * max(age_days, 0))
        total += decay * (m.points + 2 * m.num_comments)
    return math.tanh(total / scale_factor)


def _citation_score(paper: Paper, scale_factor: float) -> float:
    count = paper.citation_count or 0
    return math.tanh(count / scale_factor)


def _github_score(paper: Paper, scale_factor: float) -> float:
    count = paper.github_stars or 0
    if count <= 0:
        return 0.0
    return math.tanh(count / scale_factor)


def generate_explanation(breakdown: ScoreBreakdown, weights: dict) -> str:
    components = {
        "recency": breakdown.recency * weights["recency"],
        "HF popularity": breakdown.hf_popularity * weights["hf_popularity"],
        "HN discussion": breakdown.hn_discussion * weights["hn_discussion"],
        "citations": breakdown.citations * weights["citations"],
        "GitHub stars": breakdown.github_stars * weights["github_stars"],
    }
    total = sum(components.values())
    if total == 0:
        return "No signals detected"

    fractions = {k: v / total for k, v in components.items()}
    sorted_components = sorted(fractions.items(), key=lambda x: x[1], reverse=True)
    top_name, top_frac = sorted_components[0]
    second_name, second_frac = sorted_components[1]

    has_hn = breakdown.hn_discussion > 0.02
    has_citations = breakdown.citations > 0.05
    has_hf = breakdown.hf_popularity > 0.1
    has_gh = breakdown.github_stars > 0.1
    is_recent = breakdown.recency > 0.5

    # Multi-signal cases first (most interesting)
    if is_recent and has_hf and has_hn and has_gh:
        return "Breakout paper: HF upvotes, HN buzz, and popular repo"
    if is_recent and has_hf and has_hn:
        return "New breakout with HF upvotes and HN discussion"
    if is_recent and has_hf and has_gh:
        return "HF trending with popular GitHub repo"
    if is_recent and has_hf and has_citations:
        return "New trending paper with early citations"
    if is_recent and has_hn and has_gh:
        return "HN discussion with well-starred repo"
    if is_recent and has_hn and has_citations:
        return "Recent paper with strong discussion and citations"
    if is_recent and has_hn:
        return "Recent paper with HN discussion"
    if is_recent and has_hf:
        return "New paper popular on HuggingFace"
    if is_recent and has_gh:
        return "New paper with popular GitHub repo"
    if has_hn and has_citations:
        return "Strong discussion and citation signal"
    if has_gh and has_citations:
        return "Well-starred repo with citations"

    # Single dominant signal
    if top_frac > 0.50:
        return f"Driven mainly by {top_name}"

    if top_frac > 0.30 and second_frac > 0.30:
        return f"Strong {top_name} and {second_name} signal"

    return "Balanced signals across sources"


def score_paper(paper: Paper, config: dict) -> None:
    weights = config["score_weights"]
    halflife = config["recency_halflife_days"]

    recency = _recency_score(paper, halflife)
    hf = _hf_score(paper, config["hf_upvote_scale_factor"])
    hn = _hn_score(paper, halflife, config["hn_scale_factor"])
    citations = _citation_score(paper, config["citation_scale_factor"])
    gh = _github_score(paper, config["github_stars_scale_factor"])

    breakdown = ScoreBreakdown(
        recency=recency,
        citations=citations,
        hf_popularity=hf,
        hn_discussion=hn,
        github_stars=gh,
    )

    total = (
        weights["recency"] * recency
        + weights["hf_popularity"] * hf
        + weights["hn_discussion"] * hn
        + weights["citations"] * citations
        + weights["github_stars"] * gh
    )

    paper.score_breakdown = breakdown
    paper.total_score = total
    paper.explanation = generate_explanation(breakdown, weights)
