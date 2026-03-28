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
    last_exception: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = requests.request(
                method, url, headers=headers, json=json, params=params, timeout=timeout
            )
            if resp.status_code in (429, 503):
                wait = backoff * (2 ** attempt)
                logger.warning("Rate limited (%d) on %s, waiting %.1fs", resp.status_code, url, wait)
                time.sleep(wait)
                last_exception = requests.HTTPError(
                    f"{resp.status_code} for url: {url}", response=resp
                )
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exception = e
            if attempt == max_retries - 1:
                break
            wait = backoff * (2 ** attempt)
            logger.warning("Request to %s failed (%s), retrying in %.1fs", url, e, wait)
            time.sleep(wait)
    raise last_exception or requests.RequestException(f"Failed after {max_retries} retries: {url}")
