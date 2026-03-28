from __future__ import annotations

import copy
import os


DEFAULT_CONFIG: dict = {
    "score_weights": {
        "recency": 0.25,
        "hf_trending": 0.20,
        "hn_discussion": 0.30,
        "citations": 0.25,
    },
    "recency_halflife_days": 7,
    "hn_scale_factor": 150,
    "citation_scale_factor": 50,
    "providers": {
        "semantic_scholar": True,
        "hackernews": True,
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
    return cfg
