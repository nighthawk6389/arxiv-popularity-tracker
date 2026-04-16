from __future__ import annotations

import re


def normalize_arxiv_id(raw: str) -> str:
    raw = raw.strip()
    return re.sub(r"v\d+$", "", raw)


def extract_arxiv_id_from_url(url: str) -> str | None:
    patterns = [
        r"arxiv\.org/(?:abs|pdf)/([\d.]+(?:v\d+)?)",
        r"huggingface\.co/papers/([\d.]+(?:v\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return normalize_arxiv_id(match.group(1))
    return None


def extract_github_url(text: str) -> str | None:
    """Extract a GitHub repo URL from text (abstract, project page, etc.)."""
    match = re.search(r"https?://github\.com/([\w.-]+/[\w.-]+)", text)
    if not match:
        return None
    repo_path = match.group(1).rstrip("/")
    # Strip trailing punctuation (periods, commas) from prose
    repo_path = repo_path.rstrip(".,;:!?)")
    # Strip .git suffix
    if repo_path.endswith(".git"):
        repo_path = repo_path[:-4]
    return f"https://github.com/{repo_path}"


def normalize_title(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title
