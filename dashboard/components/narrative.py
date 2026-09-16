"""Briefing copy. Short, grounded in the row in front of you."""

from __future__ import annotations

import pandas as pd

from dashboard.components.prepare import UNITS, county_rank, format_value, ordinal


def county_briefing(row: pd.Series, national: pd.Series, column: str, indicator_label: str) -> str:
    name = str(row["county_label"])
    child_gap = row["pct_children"] - national["pct_children"]
    elderly_gap = row["pct_elderly"] - national["pct_elderly"]
    mapped = format_value(row[column], column)
    nat_mapped = format_value(national[column], column)
    units = UNITS[column]
    growth = row["growth_pct"]
    nat_growth = national["growth_pct"]

    if child_gap >= 1.5:
        structure = (
            f"Younger than Kenya overall: {row['pct_children']:.1f}% under 5 "
            f"against {national['pct_children']:.1f}% nationally. "
            "Immunization, IMNCI, and nutrition outreach set the service package here, "
            "not geriatric scale-up."
        )
    elif elderly_gap >= 0.8:
        structure = (
            f"Older than Kenya overall: {row['pct_elderly']:.1f}% aged 65+ "
            f"against {national['pct_elderly']:.1f}%. "
            "NCD clinics and community geriatric follow-up will take a larger share of the county budget."
        )
    else:
        structure = (
            f"Age mix is close to the national profile "
            f"({row['pct_children']:.1f}% under 5, {row['pct_elderly']:.1f}% aged 65+). "
            f"Volume still matters: {row['children_under_5']:,.0f} children under 5 "
            f"and {row['elderly_65plus']:,.0f} adults 65+."
        )

    density = (
        f"Child density is {row['child_density']:.1f} under-5s per km² "
        f"(Kenya {national['child_density']:.1f}). "
        f"Population is {growth:+.1f}% since 2021, against {nat_growth:+.1f}% nationally."
    )
    mapped_line = f"{indicator_label} is {mapped} {units} (Kenya {nat_mapped})."
    return f"{mapped_line} {structure} {density}"


def kenya_briefing(frame: pd.DataFrame, year: int, column: str, indicator_label: str) -> str:
    child = frame.nlargest(3, "pct_children")["county_label"].tolist()
    old = frame.nlargest(3, "pct_elderly")["county_label"].tolist()
    dense = frame.nlargest(3, "child_density")["county_label"].tolist()
    young_share = frame.nlargest(3, "child_dependency_ratio")["county_label"].tolist()
    return (
        f"In {year}, {indicator_label.lower()} ranges from "
        f"{format_value(frame[column].min(), column)} to "
        f"{format_value(frame[column].max(), column)} {UNITS[column]}. "
        f"Youngest age structures: {', '.join(child)}. "
        f"Oldest: {', '.join(old)}. "
        f"Highest under-5 density: {', '.join(dense)} — usually the compact highland and urban counties, "
        f"not the same places as the highest child dependency ({', '.join(young_share)}). "
        "Share and density answer different planning questions; do not treat the population choropleth as a workload map."
    )


def rank_line(frame: pd.DataFrame, county: str, column: str, indicator_label: str) -> str:
    rank, n = county_rank(frame, county, column)
    direction = "highest" if rank == 1 else "lowest" if rank == n else None
    if direction:
        return f"{direction.capitalize()} {indicator_label.lower()} of {n} counties"
    return f"{ordinal(rank)} of {n} counties on {indicator_label.lower()}"


def extremes_html(
    high: list[tuple[str, str]],
    low: list[tuple[str, str]],
    indicator_label: str,
) -> str:
    def _list(rows: list[tuple[str, str]]) -> str:
        items = "".join(f"<li><span>{name}</span><span class='val'>{value}</span></li>" for name, value in rows)
        return f"<ol>{items}</ol>"

    return (
        "<div class='extremes'>"
        f"<div><p class='kicker'>Highest · {indicator_label}</p>{_list(high)}</div>"
        f"<div><p class='kicker'>Lowest · {indicator_label}</p>{_list(low)}</div>"
        "</div>"
    )


def fault_copy(exc: BaseException) -> tuple[str, str]:
    """Headline and what to do. Dry on purpose."""
    name = type(exc).__name__
    text = str(exc)
    if "WidgetAlreadyInstantiated" in name or "cannot be modified after the widget" in text:
        return (
            "The map clicked. The dropdown had not sat down yet.",
            "Refresh, then click again — or pick the county from the list. Same briefing, fewer theatrics.",
        )
    if isinstance(exc, FileNotFoundError) or "Processed data is missing" in text:
        return (
            "The estimates exist. This folder is pretending they do not.",
            "Run python -m src.pipeline --skip-download, then come back. We will stop guessing.",
        )
    return (
        "Forty-seven counties are present and accounted for. This page is not.",
        "Refresh once. If it still lies down, close the tab and start the app again. The CSV did nothing wrong.",
    )


def method_note() -> str:
    return (
        "WorldPop R2025A 1 km constrained estimates, aggregated to GADM Level 1 (47 counties). "
        "Children are ages 0–4 (rasters 00 and 01); working age is 15–64; elderly is 65+. "
        "Child dependency is under-5s per 100 people aged 15–64 — a health-planning ratio, "
        "not the classic 0–14 demographic definition. Display names use official spellings; "
        "the download keeps GADM NAME_1 as gadm_name. 2021–2025 growth is about 8% in every "
        "county in this release, so the spatial story is structure and density, not change. "
        "Not a census."
    )
