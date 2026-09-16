"""Public-health interpretation copy driven by the processed county table."""

from __future__ import annotations

import pandas as pd


def dependency_context() -> str:
    return (
        "A dependency ratio is the number of people who typically need care "
        "(young children and older adults) relative to the working-age population, "
        "times 100. WorldPop here uses children **under 5** plus adults **65+**, "
        "divided by ages **15–64**. That is a health-planning lens, not the classic "
        "demographic 0–14 definition: it flags immunization, nutrition, and geriatric "
        "load against the workforce that finances services."
    )


def age_structure_context() -> str:
    return (
        "High child shares mean routine immunization, paediatric beds, and nutrition "
        "programmes have to reach more people per worker. High elderly shares shift "
        "the package toward chronic disease, rehabilitation, and geriatric care. "
        "A high overall dependency ratio is a financing problem: the same working-age "
        "base is asked to support both ends of the age distribution."
    )


def _label(row: pd.Series) -> str:
    return str(row["county_label"] if "county_label" in row.index else row["county"])


def county_note(row: pd.Series, national: pd.Series) -> str:
    name = _label(row)
    child_gap = row["pct_children"] - national["pct_children"]
    elderly_gap = row["pct_elderly"] - national["pct_elderly"]
    if child_gap >= 1.5:
        focus = (
            f"{name} has a younger profile than the national mix "
            f"({row['pct_children']:.1f}% under 5 vs {national['pct_children']:.1f}% nationally). "
            "Prioritise outreach immunization, IMNCI, and nutrition screening rather than "
            "scaling geriatric capacity first."
        )
    elif elderly_gap >= 0.8:
        focus = (
            f"{name} is ageing faster than the country overall "
            f"({row['pct_elderly']:.1f}% aged 65+ vs {national['pct_elderly']:.1f}%). "
            "NCD clinics, hypertension/diabetes follow-up, and community geriatric care "
            "will take a larger share of the county budget."
        )
    else:
        focus = (
            f"{name} sits near the national age mix. Watch the absolute counts: "
            f"{row['children_under_5']:,.0f} children under 5 and {row['elderly_65plus']:,.0f} "
            "adults 65+ still set the floor for service volume even when percentages look average."
        )
    return (
        f"{focus} Dependency ratio is {row['dependency_ratio']:.1f} "
        f"(national {national['dependency_ratio']:.1f})."
    )


def policy_implications(year_frame: pd.DataFrame) -> list[str]:
    """Two implications grounded in this year's county ranks, not generic boilerplate."""
    name_col = "county_label" if "county_label" in year_frame.columns else "county"
    child = year_frame.nlargest(3, "pct_children")
    elderly = year_frame.nlargest(3, "pct_elderly")
    dep = year_frame.nlargest(3, "dependency_ratio")
    child_names = ", ".join(child[name_col].tolist())
    elderly_names = ", ".join(elderly[name_col].tolist())
    dep_names = ", ".join(dep[name_col].tolist())
    return [
        (
            f"Immunization and RMNCAH financing should follow the child-share map, not just "
            f"total population. Highest % under 5 in this year: {child_names}. "
            "These counties need dose tracking and cold-chain density even where overall "
            "headcount looks small on a national choropleth."
        ),
        (
            f"NCD and geriatric investment should not wait for a national 'ageing Kenya' headline. "
            f"Highest % 65+: {elderly_names}. Highest overall dependency: {dep_names}. "
            "That split is a two-track health system: youth-heavy ASAL/northern counties "
            "versus an emerging older caseload in parts of Central and the highlands."
        ),
    ]
