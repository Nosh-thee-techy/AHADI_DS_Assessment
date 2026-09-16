"""Zonal sums of WorldPop rasters onto 47 counties, then demographic indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd
import rasterio
from rasterstats import zonal_stats

from src.config import (
    AGE_SEX_CSV,
    CHILD_AGES,
    COUNTY_CSV,
    COUNTY_GEOJSON,
    ELDERLY_AGES,
    WORKING_AGES,
    expected_raster_jobs,
    worldpop_path,
)
from src.utils import setup_logging
from src.validation import run_structure_checks

logger = setup_logging()

AGE_LABELS = {
    "00": "0-1",
    "01": "1-4",
    "05": "5-9",
    "10": "10-14",
    "15": "15-19",
    "20": "20-24",
    "25": "25-29",
    "30": "30-34",
    "35": "35-39",
    "40": "40-44",
    "45": "45-49",
    "50": "50-54",
    "55": "55-59",
    "60": "60-64",
    "65": "65-69",
    "70": "70-74",
    "75": "75-79",
    "80": "80-84",
    "85": "85-89",
    "90": "90+",
}


def _zonal_sum(raster_path, geometries, raster_crs) -> list[float]:
    gdf = geometries.copy()
    if raster_crs is not None:
        gdf = gdf.to_crs(raster_crs)
    stats = zonal_stats(
        gdf.geometry,
        str(raster_path),
        stats="sum",
        nodata=None,
        geojson_out=False,
    )
    values = []
    for item in stats:
        raw = item.get("sum")
        values.append(0.0 if raw is None or (isinstance(raw, float) and np.isnan(raw)) else float(raw))
    return values


def extract_age_sex_table(counties) -> pd.DataFrame:
    jobs = expected_raster_jobs()
    rows: list[dict] = []
    clipped_negatives = 0
    skipped = 0

    for i, (year, sex, age) in enumerate(jobs, start=1):
        path = worldpop_path(year, sex, age)
        if not path.exists():
            skipped += 1
            logger.warning("Skip missing raster %s", path.name)
            continue
        with rasterio.open(path) as src:
            raster_crs = src.crs
        values = _zonal_sum(path, counties, raster_crs)
        neg = sum(1 for v in values if v < 0)
        if neg:
            clipped_negatives += neg
            values = [max(v, 0.0) for v in values]
        for county, population in zip(counties["county"], values, strict=True):
            rows.append(
                {
                    "county": county,
                    "year": year,
                    "sex": "male" if sex == "m" else "female",
                    "age_code": age,
                    "age_group": AGE_LABELS[age],
                    "population": population,
                }
            )
        if i % 20 == 0 or i == len(jobs):
            logger.info("Zonal stats %s/%s (%s)", i, len(jobs), path.name)

    if clipped_negatives:
        logger.warning("Clipped %s negative county-level sums to 0", clipped_negatives)
    if skipped:
        logger.warning("Skipped %s rasters; those age-sex cells are absent from the long table", skipped)

    table = pd.DataFrame(rows)
    logger.info("Age-sex table rows: %s", len(table))
    return table


def _sum_ages(frame: pd.DataFrame, ages: tuple[str, ...], name: str) -> pd.Series:
    return frame.loc[frame["age_code"].isin(ages)].groupby(["county", "year"])["population"].sum().rename(name)


def build_county_indicators(age_sex: pd.DataFrame, counties) -> pd.DataFrame:
    totals = age_sex.groupby(["county", "year"])["population"].sum().rename("total_population")
    children = _sum_ages(age_sex, CHILD_AGES, "children_under_5")
    working = _sum_ages(age_sex, WORKING_AGES, "working_age")
    elderly = _sum_ages(age_sex, ELDERLY_AGES, "elderly_65plus")

    sex_totals = (
        age_sex.groupby(["county", "year", "sex"])["population"]
        .sum()
        .unstack("sex")
        .rename(columns={"male": "male_population", "female": "female_population"})
    )

    out = pd.concat([totals, children, working, elderly, sex_totals], axis=1).reset_index()
    out["sex_ratio"] = out["male_population"] / out["female_population"] * 100
    out["dependency_ratio"] = (out["children_under_5"] + out["elderly_65plus"]) / out["working_age"] * 100
    out["child_dependency_ratio"] = out["children_under_5"] / out["working_age"] * 100
    out["elderly_dependency_ratio"] = out["elderly_65plus"] / out["working_age"] * 100
    out["pct_children"] = out["children_under_5"] / out["total_population"] * 100
    out["pct_elderly"] = out["elderly_65plus"] / out["total_population"] * 100

    area = counties[["county", "area_km2"]]
    out = out.merge(area, on="county", how="left")

    national = out.groupby("year")["total_population"].sum()
    for year, total in national.items():
        logger.info("National total population %s: %s", year, f"{total:,.0f}")

    zeros = out.loc[out["total_population"] <= 0, ["county", "year"]]
    if not zeros.empty:
        logger.warning("Zero/negative total population rows:\n%s", zeros.to_string(index=False))

    columns = [
        "county",
        "year",
        "total_population",
        "children_under_5",
        "working_age",
        "elderly_65plus",
        "sex_ratio",
        "dependency_ratio",
        "child_dependency_ratio",
        "elderly_dependency_ratio",
        "pct_children",
        "pct_elderly",
        "male_population",
        "female_population",
        "area_km2",
    ]
    return out[columns].sort_values(["year", "county"]).reset_index(drop=True)


def run_aggregation() -> tuple[pd.DataFrame, pd.DataFrame]:
    counties = run_structure_checks()
    age_sex = extract_age_sex_table(counties)
    AGE_SEX_CSV.parent.mkdir(parents=True, exist_ok=True)
    age_sex.to_csv(AGE_SEX_CSV, index=False)
    logger.info("Wrote %s", AGE_SEX_CSV)

    indicators = build_county_indicators(age_sex, counties)
    spec_cols = [
        "county",
        "year",
        "total_population",
        "children_under_5",
        "working_age",
        "elderly_65plus",
        "sex_ratio",
        "dependency_ratio",
        "child_dependency_ratio",
        "elderly_dependency_ratio",
        "pct_children",
        "pct_elderly",
    ]
    indicators[spec_cols].to_csv(COUNTY_CSV, index=False)
    logger.info("Wrote %s", COUNTY_CSV)

    simplified = counties.copy()
    simplified["geometry"] = simplified.geometry.simplify(0.01, preserve_topology=True)
    simplified.to_file(COUNTY_GEOJSON, driver="GeoJSON")
    logger.info("Wrote %s", COUNTY_GEOJSON)
    return age_sex, indicators
