from __future__ import annotations

import logging
import re
import time

import requests


logger = logging.getLogger("arxiv_popularity")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_window(window: str) -> int:
    match = re.fullmatch(r"(\d+)d", window)
    if not match:
        raise ValueError(f"Invalid window format '{window}'. Use format like '7d', '14d', '30d'.")
    days = int(match.group(1))
    if days <= 0:
        raise ValueError(f"Window must be positive, got {days}d.")
    return days


def fetch_with_retry(
    url: str,
    *,
    method: str = "GET",
    headers: dict | None = None,
    json: dict | None = None,
    params: dict | None = None,
    max_retries: int = 3,
    backoff: float = 1.0,
    timeout: int = 30,
) -> requests.Response:
    for attempt in range(max_retries):
        try:
            resp = requests.request(
                method, url, headers=headers, json=json, params=params, timeout=timeout
            )
            if resp.status_code == 429:
                wait = backoff * (2 ** attempt)
                logger.warning("Rate limited on %s, waiting %.1fs", url, wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise
            wait = backoff * (2 ** attempt)
            logger.warning("Request to %s failed (%s), retrying in %.1fs", url, e, wait)
            time.sleep(wait)
    raise requests.RequestException(f"Failed after {max_retries} retries: {url}")
