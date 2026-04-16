from __future__ import annotations

import copy
import os


DEFAULT_CONFIG: dict = {
    "score_weights": {
        "recency": 0.20,
        "hf_popularity": 0.20,
        "hn_discussion": 0.25,
        "citations": 0.20,
        "github_stars": 0.15,
    },
    "recency_halflife_days": 7,
    "hn_scale_factor": 150,
    "citation_scale_factor": 50,
    "hf_upvote_scale_factor": 30,
    "github_stars_scale_factor": 500,
    "providers": {
        "semantic_scholar": True,
        "hackernews": True,
        "github": True,
        "reddit": False,
        "x": False,
    },
    "thread_pool_size": 8,
}


def load_config() -> dict:
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        cfg["semantic_scholar_api_key"] = api_key
    gh_token = os.environ.get("GITHUB_TOKEN")
    if gh_token:
        cfg["github_token"] = gh_token
    return cfg
