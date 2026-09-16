"""Shared logging, filesystem helpers, and county-name cleanup."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from src.config import DATA_PROCESSED, FIGURES, GADM_DIR, LOG_PATH, WORLDPOP_DIR

# GADM NAME_1 is CamelCase ("HomaBay"). Official county names use a space.
_CAMEL_SPLIT = re.compile(r"(?<=[a-z])(?=[A-Z])")


def tidy_county_name(name: str) -> str:
    """Turn GADM NAME_1 into a readable Kenyan county name.

    HomaBay -> Homa Bay, WestPokot -> West Pokot.
    Hyphenated names (Elgeyo-Marakwet) and Murang'a are left intact.
    """
    return _CAMEL_SPLIT.sub(" ", str(name)).strip()


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
