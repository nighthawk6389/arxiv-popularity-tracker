from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class HNMention:
    story_id: int
    title: str
    points: int
    num_comments: int
    created_at: datetime
    url: str


@dataclass
class ScoreBreakdown:
    recency: float
    citations: float
    hf_trending: float
    hn_discussion: float


@dataclass
class Paper:
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    categories: list[str]
    published: datetime
    updated: datetime
    arxiv_url: str
    pdf_url: str

    citation_count: int | None = None
    semantic_scholar_id: str | None = None
    hf_trending: bool = False
    hf_trending_rank: int | None = None
    hn_mentions: list[HNMention] = field(default_factory=list)

    total_score: float = 0.0
    score_breakdown: ScoreBreakdown | None = None
    explanation: str = ""
