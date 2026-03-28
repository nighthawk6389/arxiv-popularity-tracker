from __future__ import annotations

import argparse
import logging
import time

from arxiv_popularity.config import load_config
from arxiv_popularity.pipeline.discover import discover
from arxiv_popularity.pipeline.enrich import enrich_papers
from arxiv_popularity.pipeline.score import score_papers
from arxiv_popularity.pipeline.export import export_all
from arxiv_popularity.utils import parse_window, setup_logging

logger = logging.getLogger("arxiv_popularity")


def run(args: argparse.Namespace) -> None:
    config = load_config()
    window_days = parse_window(args.window)

    start = time.time()

    # 1. Discover
    logger.info("=== Stage 1: Discovery ===")
    papers = discover(args.categories, window_days, args.limit)

    # 2. Enrich
    logger.info("=== Stage 2: Enrichment ===")
    papers = enrich_papers(papers, config)

    # 3. Score
    logger.info("=== Stage 3: Scoring ===")
    papers = score_papers(papers, config)

    # 4. Export
    logger.info("=== Stage 4: Export ===")
    export_all(papers, args.output_dir, args.top)

    elapsed = time.time() - start
    logger.info("Done in %.1fs. Output in %s/", elapsed, args.output_dir)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="arxiv_popularity",
        description="Track which arXiv papers are getting attention and why.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="Run the full pipeline")
    run_parser.add_argument("--categories", nargs="+", default=["cs.AI", "cs.LG"],
                            help="arXiv categories to search (default: cs.AI cs.LG)")
    run_parser.add_argument("--window", default="7d",
                            help="Lookback window, e.g. 7d, 14d, 30d (default: 7d)")
    run_parser.add_argument("--limit", type=int, default=100,
                            help="Max papers to discover (default: 100)")
    run_parser.add_argument("--top", type=int, default=50,
                            help="Number of papers in ranked report (default: 50)")
    run_parser.add_argument("--output-dir", default="output",
                            help="Output directory (default: output)")
    run_parser.add_argument("-v", "--verbose", action="store_true",
                            help="Enable debug logging")

    args = parser.parse_args()
    setup_logging(getattr(args, "verbose", False))

    if args.command == "run":
        run(args)
    else:
        parser.print_help()
