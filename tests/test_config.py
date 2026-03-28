from arxiv_popularity.config import DEFAULT_CONFIG, load_config


def test_default_config_has_required_keys():
    assert "score_weights" in DEFAULT_CONFIG
    assert "providers" in DEFAULT_CONFIG
    assert "thread_pool_size" in DEFAULT_CONFIG


def test_weights_sum_to_one():
    weights = DEFAULT_CONFIG["score_weights"]
    assert abs(sum(weights.values()) - 1.0) < 0.001


def test_load_config_returns_defaults():
    cfg = load_config()
    assert cfg["score_weights"]["recency"] == 0.25
