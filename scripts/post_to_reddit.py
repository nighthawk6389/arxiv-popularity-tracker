#!/usr/bin/env python3
"""
Preview parsed Reddit posts from social_posts.md.

Usage:
    python scripts/post_to_reddit.py output/social_posts.md

This is a preview/dry-run tool only. Actual Reddit posting is done
via Claude Code with Chrome browser tools — just say:
    "post the papers from output/social_posts.md to Reddit"
in a Claude Code session.
"""

import os
import re
import sys


def parse_social_posts(path: str) -> list[dict]:
    """Parse social_posts.md into a list of Reddit post dicts."""
    with open(path) as f:
        content = f.read()

    posts = []
    sections = re.split(r"^## \d+\. ", content, flags=re.MULTILINE)

    for section in sections[1:]:
        post: dict = {}

        lines = section.strip().split("\n")
        post["title"] = lines[0].strip()

        match = re.search(r"\*\*Suggested subreddits:\*\*\s*(.+)", section)
        if match:
            subs_raw = match.group(1).strip()
            post["subreddits"] = [s.strip() for s in subs_raw.split(",")]
        else:
            post["subreddits"] = ["r/MachineLearning"]

        body_match = re.search(
            r"\*\*Post body:\*\*\n(.+?)(?=\n\*\*[A-Z]|\n---|\Z)",
            section,
            re.DOTALL,
        )
        if body_match:
            post["body"] = body_match.group(1).strip()
        else:
            post["body"] = ""

        if post["title"] and post["body"]:
            posts.append(post)

    return posts


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/post_to_reddit.py <social_posts.md>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"Error: {path} not found", file=sys.stderr)
        sys.exit(1)

    posts = parse_social_posts(path)
    if not posts:
        print("No posts found in file")
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"{len(posts)} paper(s) ready for Reddit")
    print(f"{'='*60}\n")

    for i, post in enumerate(posts, 1):
        print(f"--- Paper {i} ---")
        print(f"Title:      {post['title']}")
        print(f"Subreddits: {', '.join(post['subreddits'])}")
        print(f"Body:\n{post['body']}")
        print()

    print("To post these to Reddit, run a Claude Code session and say:")
    print('  "post the papers from output/social_posts.md to Reddit"')


if __name__ == "__main__":
    main()
