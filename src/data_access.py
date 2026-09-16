"""Programmatic download of WorldPop rasters and GADM boundaries, with caching."""

from __future__ import annotations

import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from src.config import (
    DOWNLOAD_RETRIES,
    DOWNLOAD_TIMEOUT_S,
    DOWNLOAD_WORKERS,
    GADM_DIR,
    GADM_L1_URL,
    GADM_L2_URL,
    expected_raster_jobs,
    worldpop_path,
    worldpop_url,
)
from src.utils import ensure_directories, setup_logging

logger = setup_logging()

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "kenya-population-pipeline/1.0"})


def _download_file(url: str, dest: Path) -> str:
    """Download url to dest unless a non-empty file already exists."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return "cached"

    tmp = dest.with_suffix(dest.suffix + ".part")
    last_error: Exception | None = None
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            with _SESSION.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT_S) as response:
                response.raise_for_status()
                with tmp.open("wb") as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            handle.write(chunk)
            tmp.replace(dest)
            return "downloaded"
        except Exception as exc:  # noqa: BLE001 — retry then raise
            last_error = exc
            logger.warning("Attempt %s failed for %s: %s", attempt, url, exc)
            time.sleep(attempt * 1.5)
    raise RuntimeError(f"Failed to download {url}") from last_error


def download_worldpop_raster(year: int, sex: str, age: str) -> tuple[str, Path]:
    dest = worldpop_path(year, sex, age)
    status = _download_file(worldpop_url(year, sex, age), dest)
    return status, dest


def download_all_worldpop(workers: int = DOWNLOAD_WORKERS) -> dict[str, int]:
    """Fetch all expected male/female 1km rasters. Skips files already on disk."""
    ensure_directories()
    jobs = expected_raster_jobs()
    counts = {"cached": 0, "downloaded": 0, "failed": 0}
    logger.info("WorldPop: %s expected rasters (f/m only, skip totals)", len(jobs))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(download_worldpop_raster, year, sex, age): (year, sex, age)
            for year, sex, age in jobs
        }
        for future in as_completed(futures):
            year, sex, age = futures[future]
            try:
                status, dest = future.result()
                counts[status] += 1
                logger.info("WorldPop %s %s %s → %s (%s)", year, sex, age, dest.name, status)
            except Exception as exc:  # noqa: BLE001
                counts["failed"] += 1
                logger.error("WorldPop missing %s %s %s: %s", year, sex, age, exc)

    logger.info("WorldPop download summary: %s", counts)
    return counts


def _extract_json_from_zip(zip_path: Path, dest_dir: Path) -> Path:
    with zipfile.ZipFile(zip_path) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".json")]
        if not members:
            raise FileNotFoundError(f"No JSON in {zip_path}")
        archive.extractall(dest_dir)
    extracted = dest_dir / Path(members[0]).name
    if not extracted.exists():
        # zip may contain a nested path
        extracted = dest_dir / members[0]
    return extracted


def download_gadm() -> dict[str, Path]:
    """Download GADM Level 1 (counties) and Level 2 (as specified in the brief)."""
    ensure_directories()
    paths: dict[str, Path] = {}
    for label, url in (("l1", GADM_L1_URL), ("l2", GADM_L2_URL)):
        zip_path = GADM_DIR / Path(url).name
        status = _download_file(url, zip_path)
        json_path = _extract_json_from_zip(zip_path, GADM_DIR)
        paths[label] = json_path
        logger.info("GADM %s → %s (%s)", label, json_path.name, status)
    return paths


def download_all() -> None:
    gadm = download_gadm()
    worldpop = download_all_worldpop()
    if worldpop["failed"]:
        logger.warning(
            "Proceeding with %s missing rasters; validation will decide impute vs drop",
            worldpop["failed"],
        )
    logger.info("GADM files: %s", {k: str(v) for k, v in gadm.items()})
