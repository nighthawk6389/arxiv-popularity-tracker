import pytest
from arxiv_popularity.utils import parse_window


def test_parse_window_7d():
    assert parse_window("7d") == 7


def test_parse_window_14d():
    assert parse_window("14d") == 14


def test_parse_window_30d():
    assert parse_window("30d") == 30


def test_parse_window_invalid():
    with pytest.raises(ValueError):
        parse_window("7x")


def test_parse_window_no_unit():
    with pytest.raises(ValueError):
        parse_window("7")


def test_parse_window_zero():
    with pytest.raises(ValueError):
        parse_window("0d")
