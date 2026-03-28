from __future__ import annotations

import math
from datetime import datetime, timezone

from arxiv_popularity.models import Paper, ScoreBreakdown


def _recency_score(paper: Paper, halflife_days: float) -> float:
    age_days = (datetime.now(timezone.utc) - paper.published).total_seconds() / 86400
    lam = math.log(2) / halflife_days
    return math.exp(-lam * max(age_days, 0))


def _hf_score(paper: Paper) -> float:
    return 1.0 if paper.hf_trending else 0.0


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


def generate_explanation(breakdown: ScoreBreakdown, weights: dict) -> str:
    components = {
        "recency": breakdown.recency * weights["recency"],
        "HF trending": breakdown.hf_trending * weights["hf_trending"],
        "HN discussion": breakdown.hn_discussion * weights["hn_discussion"],
        "citations": breakdown.citations * weights["citations"],
    }
    total = sum(components.values())
    if total == 0:
        return "No signals detected"

    fractions = {k: v / total for k, v in components.items()}
    sorted_components = sorted(fractions.items(), key=lambda x: x[1], reverse=True)
    top_name, top_frac = sorted_components[0]
    second_name, second_frac = sorted_components[1]

    # Special case: recent + trending
    if fractions.get("recency", 0) > 0.2 and fractions.get("HF trending", 0) > 0.2:
        return "New breakout paper with trending signal"

    if top_frac > 0.50:
        return f"Driven mainly by {top_name}"

    if top_frac > 0.30 and second_frac > 0.30:
        return f"Strong {top_name} and {second_name} signal"

    return "Balanced signals across sources"


def score_paper(paper: Paper, config: dict) -> None:
    weights = config["score_weights"]
    halflife = config["recency_halflife_days"]

    recency = _recency_score(paper, halflife)
    hf = _hf_score(paper)
    hn = _hn_score(paper, halflife, config["hn_scale_factor"])
    citations = _citation_score(paper, config["citation_scale_factor"])

    breakdown = ScoreBreakdown(
        recency=recency,
        citations=citations,
        hf_trending=hf,
        hn_discussion=hn,
    )

    total = (
        weights["recency"] * recency
        + weights["hf_trending"] * hf
        + weights["hn_discussion"] * hn
        + weights["citations"] * citations
    )

    paper.score_breakdown = breakdown
    paper.total_score = total
    paper.explanation = generate_explanation(breakdown, weights)
