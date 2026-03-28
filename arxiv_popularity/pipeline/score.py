from __future__ import annotations

import logging

from arxiv_popularity.models import Paper
from arxiv_popularity.scoring import score_paper

logger = logging.getLogger("arxiv_popularity.pipeline.score")


def score_papers(papers: list[Paper], config: dict) -> list[Paper]:
    for paper in papers:
        score_paper(paper, config)

    papers.sort(key=lambda p: p.total_score, reverse=True)
    logger.info("Scored and ranked %d papers", len(papers))
    return papers
