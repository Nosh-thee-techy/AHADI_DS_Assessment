"""CRS, inventory, and boundary checks. Aggregation logs pixel-level issues."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import rasterio

from src.config import (
    AGE_CODES,
    EXPECTED_COUNTY_COUNT,
    GADM_DIR,
    SEXES,
    TARGET_CRS,
    YEARS,
    expected_raster_jobs,
    worldpop_path,
)
from src.utils import setup_logging

logger = setup_logging()


def list_present_rasters() -> list[Path]:
    jobs = expected_raster_jobs()
    present = []
    missing = []
    for year, sex, age in jobs:
        path = worldpop_path(year, sex, age)
        if path.exists() and path.stat().st_size > 0:
            present.append(path)
        else:
            missing.append((year, sex, age))
    logger.info("Raster inventory: %s present, %s missing of %s expected", len(present), len(missing), len(jobs))
    for year, sex, age in missing:
        logger.warning("Missing raster year=%s sex=%s age=%s", year, sex, age)
    return present


def load_counties() -> gpd.GeoDataFrame:
    """Use GADM Level 1 (47 counties). Log why the brief's Level 2 file is the wrong grain."""
    l1_path = GADM_DIR / "gadm41_KEN_1.json"
    l2_path = GADM_DIR / "gadm41_KEN_2.json"
    l1 = gpd.read_file(l1_path)
    l2 = gpd.read_file(l2_path)
    logger.info("GADM Level 1 features: %s (file %s)", len(l1), l1_path.name)
    logger.info("GADM Level 2 features: %s (file %s)", len(l2), l2_path.name)

    if len(l1) != EXPECTED_COUNTY_COUNT:
        raise ValueError(f"Expected {EXPECTED_COUNTY_COUNT} counties in Level 1, found {len(l1)}")

    logger.info(
        "Decision: aggregate to GADM Level 1 NAME_1. The brief links Level 2 and asks "
        "for 47 counties; Level 2 is %s sub-county units, not counties.",
        len(l2),
    )

    if l1.crs is None:
        logger.warning("GADM CRS missing; assuming %s", TARGET_CRS)
        l1 = l1.set_crs(TARGET_CRS)
    elif str(l1.crs) != TARGET_CRS and l1.crs.to_epsg() != 4326:
        logger.info("Reprojecting counties from %s to %s", l1.crs, TARGET_CRS)
        l1 = l1.to_crs(TARGET_CRS)
    else:
        logger.info("County CRS OK: %s", l1.crs)

    counties = l1.rename(columns={"NAME_1": "county"})[["county", "geometry"]].copy()
    # Equal-area projection for a rough km2 figure used in the under-5 vs size scatter.
    counties["area_km2"] = counties.to_crs(6933).area / 1_000_000
    names = sorted(counties["county"].tolist())
    logger.info("Counties (%s): %s", len(names), ", ".join(names))
    return counties


def inspect_sample_raster(path: Path, counties: gpd.GeoDataFrame) -> dict:
    with rasterio.open(path) as src:
        info = {
            "path": str(path),
            "crs": str(src.crs),
            "bounds": src.bounds,
            "nodata": src.nodata,
            "width": src.width,
            "height": src.height,
        }
        logger.info("Sample raster %s CRS=%s nodata=%s size=%sx%s", path.name, src.crs, src.nodata, src.width, src.height)
        if src.crs is None:
            logger.warning("Raster has no CRS; zonal stats will assume coordinates match counties")
        elif src.crs.to_epsg() != 4326:
            logger.info("Raster CRS is %s; counties will be reprojected to the raster for extraction", src.crs)

        sample = src.read(1, window=rasterio.windows.Window(0, 0, min(200, src.width), min(200, src.height)))
        neg = int((sample < 0).sum()) if src.nodata is None else int(((sample < 0) & (sample != src.nodata)).sum())
        if neg:
            logger.warning("Sample window contains %s negative values; aggregation will clip negatives to 0", neg)
    return info


def run_structure_checks() -> gpd.GeoDataFrame:
    present = list_present_rasters()
    if not present:
        raise FileNotFoundError("No WorldPop rasters on disk. Run: python -m src.pipeline --download-only")
    counties = load_counties()
    inspect_sample_raster(present[0], counties)
    logger.info("Expected age codes: %s", ", ".join(AGE_CODES))
    logger.info("Expected sexes: %s (WorldPop 't' totals are not downloaded)", ", ".join(SEXES))
    logger.info("Years: %s", ", ".join(str(y) for y in YEARS))
    return counties
