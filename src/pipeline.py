"""Entry point: download → validate → aggregate → figures."""

from __future__ import annotations

import argparse

from src.aggregation import run_aggregation
from src.data_access import download_all
from src.utils import ensure_directories, setup_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Kenya county population pipeline")
    parser.add_argument(
        "--download-only",
        action="store_true",
        help="Fetch WorldPop rasters and GADM boundaries, then stop.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Use cached rasters only; do not hit the network.",
    )
    args = parser.parse_args()

    ensure_directories()
    logger = setup_logging()
    logger.info("Pipeline start")
    if not args.skip_download:
        download_all()
    if args.download_only:
        logger.info("Download-only run complete")
        return
    run_aggregation()
    logger.info("Pipeline complete")


if __name__ == "__main__":
    main()
