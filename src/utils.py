"""Shared logging and filesystem helpers."""

from __future__ import annotations

import logging
from pathlib import Path

from src.config import DATA_PROCESSED, FIGURES, GADM_DIR, LOG_PATH, WORLDPOP_DIR


def ensure_directories() -> None:
    for path in (WORLDPOP_DIR, GADM_DIR, DATA_PROCESSED, FIGURES):
        path.mkdir(parents=True, exist_ok=True)


def setup_logging(log_path: Path | None = None) -> logging.Logger:
    """Log to stdout and the validation log file."""
    ensure_directories()
    logger = logging.getLogger("kenya_pop")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    logger.addHandler(stream)

    file_handler = logging.FileHandler(log_path or LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger
