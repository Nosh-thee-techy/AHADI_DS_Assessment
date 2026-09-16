"""Derived indicators for the dashboard, computed from the processed CSVs."""

from __future__ import annotations

import pandas as pd

from src.config import CHILD_AGES, ELDERLY_AGES, WORKING_AGES
from src.utils import tidy_county_name

INDICATORS = {
    "Children per km²": "child_density",
    "Child dependency": "child_dependency_ratio",
    "Share under 5": "pct_children",
    "Share 65+": "pct_elderly",
    "Population": "total_population",
    "Sex ratio": "sex_ratio",
}

UNITS = {
    "child_density": "per km²",
    "child_dependency_ratio": "per 100 aged 15–64",
    "pct_children": "%",
    "pct_elderly": "%",
    "total_population": "people",
    "growth_pct": "% vs 2021",
    "sex_ratio": "males / 100 females",
}

EXPORT_COLUMNS = [
    "gadm_name",
    "county",
    "year",
    "sex",
    "total_population",
    "children_under_5",
    "working_age",
    "elderly_65plus",
    "pct_children",
    "pct_elderly",
    "child_dependency_ratio",
    "elderly_dependency_ratio",
    "dependency_ratio",
    "sex_ratio",
    "area_km2",
    "child_density",
    "growth_pct",
]


def pad_age_codes(age_sex: pd.DataFrame) -> pd.DataFrame:
    """WorldPop codes are 00, 01, 05… Pandas reads the CSV as integers."""
    out = age_sex.copy()
    out["age_code"] = out["age_code"].astype(str).str.zfill(2)
    return out


def areas_from_geojson(geojson: dict) -> dict[str, float]:
    return {
        feature["properties"]["county"]: float(feature["properties"]["area_km2"])
        for feature in geojson["features"]
    }


def _group_sum(year_ages: pd.DataFrame, ages: tuple[str, ...]) -> pd.Series:
    return year_ages.loc[year_ages["age_code"].isin(ages)].groupby("county")["population"].sum()


def indicators_for(
    counties: pd.DataFrame,
    age_sex: pd.DataFrame,
    year: int,
    sex: str,
    areas: dict[str, float],
) -> pd.DataFrame:
    """County table for one year, optionally one sex, plus density and growth."""
    age_sex = pad_age_codes(age_sex)
    year_ages = age_sex.loc[age_sex["year"] == year]
    ages_2021 = age_sex.loc[age_sex["year"] == 2021]
    males = year_ages.loc[year_ages["sex"] == "male"].groupby("county")["population"].sum()
    females = year_ages.loc[year_ages["sex"] == "female"].groupby("county")["population"].sum()
    if sex != "Total":
        year_ages = year_ages.loc[year_ages["sex"] == sex.lower()]
        ages_2021 = ages_2021.loc[ages_2021["sex"] == sex.lower()]

    if sex == "Total":
        out = counties.loc[counties["year"] == year].copy()
    else:
        child = _group_sum(year_ages, CHILD_AGES)
        working = _group_sum(year_ages, WORKING_AGES)
        elderly = _group_sum(year_ages, ELDERLY_AGES)
        total = year_ages.groupby("county")["population"].sum()
        out = counties.loc[counties["year"] == year, ["county", "year"]].copy()
        out["children_under_5"] = out["county"].map(child)
        out["working_age"] = out["county"].map(working)
        out["elderly_65plus"] = out["county"].map(elderly)
        out["total_population"] = out["county"].map(total)
        out["pct_children"] = out["children_under_5"] / out["total_population"] * 100
        out["pct_elderly"] = out["elderly_65plus"] / out["total_population"] * 100
        out["dependency_ratio"] = (out["children_under_5"] + out["elderly_65plus"]) / out["working_age"] * 100
        out["child_dependency_ratio"] = out["children_under_5"] / out["working_age"] * 100
        out["elderly_dependency_ratio"] = out["elderly_65plus"] / out["working_age"] * 100
        out["sex_ratio"] = float("nan")

    out["county_label"] = out["county"].map(tidy_county_name)
    out["males"] = out["county"].map(males)
    out["females"] = out["county"].map(females)
    if sex == "Total":
        out["sex_ratio"] = out["males"] / out["females"] * 100
    out["area_km2"] = out["county"].map(areas)
    out["child_density"] = out["children_under_5"] / out["area_km2"]
    out["pop_2021"] = out["county"].map(ages_2021.groupby("county")["population"].sum())
    out["growth_pct"] = (out["total_population"] - out["pop_2021"]) / out["pop_2021"] * 100
    return out


def national_row(frame: pd.DataFrame) -> pd.Series:
    total = frame["total_population"].sum()
    child = frame["children_under_5"].sum()
    elderly = frame["elderly_65plus"].sum()
    working = frame["working_age"].sum()
    area = frame["area_km2"].sum()
    pop_2021 = frame["pop_2021"].sum()
    females = frame["females"].sum()
    return pd.Series(
        {
            "county": "Kenya",
            "county_label": "Kenya",
            "total_population": total,
            "children_under_5": child,
            "working_age": working,
            "elderly_65plus": elderly,
            "pct_children": child / total * 100,
            "pct_elderly": elderly / total * 100,
            "dependency_ratio": (child + elderly) / working * 100,
            "child_dependency_ratio": child / working * 100,
            "elderly_dependency_ratio": elderly / working * 100,
            "child_density": child / area,
            "growth_pct": (total - pop_2021) / pop_2021 * 100 if pop_2021 else float("nan"),
            "area_km2": area,
            "sex_ratio": frame["males"].sum() / females * 100 if females else float("nan"),
        }
    )


def ordinal(n: int) -> str:
    n = int(n)
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def county_rank(frame: pd.DataFrame, county: str, column: str) -> tuple[int, int]:
    ranks = frame[column].rank(ascending=False, method="min")
    return int(ranks.loc[frame["county"] == county].iloc[0]), len(frame)


def format_value(value: float, column: str) -> str:
    if pd.isna(value):
        return "—"
    if column == "total_population":
        return f"{value:,.0f}"
    if column == "child_density":
        return f"{value:.1f}"
    if column == "sex_ratio":
        return f"{value:.1f}"
    return f"{value:.1f}"


def export_bytes(frame: pd.DataFrame, year: int, sex: str) -> bytes:
    out = frame.copy()
    out.insert(0, "gadm_name", out["county"])
    out["county"] = out["county_label"]
    out["year"] = year
    out["sex"] = "total" if sex == "Total" else sex.lower()
    columns = [col for col in EXPORT_COLUMNS if col in out.columns]
    return out[columns].to_csv(index=False).encode("utf-8")
