from __future__ import annotations

import re


def normalize_arxiv_id(raw: str) -> str:
    raw = raw.strip()
    return re.sub(r"v\d+$", "", raw)


def extract_arxiv_id_from_url(url: str) -> str | None:
    patterns = [
        r"arxiv\.org/(?:abs|pdf)/(\S+)",
        r"huggingface\.co/papers/(\S+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return normalize_arxiv_id(match.group(1))
    return None


def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title
