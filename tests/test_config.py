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
    assert cfg["score_weights"]["recency"] == 0.20


def test_config_has_scale_factors():
    cfg = load_config()
    assert "hf_upvote_scale_factor" in cfg
    assert "github_stars_scale_factor" in cfg


def test_config_has_github_provider():
    cfg = load_config()
    assert "github" in cfg["providers"]
