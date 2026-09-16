"""Kenya county age-structure explorer for Ministry of Health planning."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import (  # noqa: E402
    COUNT_INDICATORS,
    INDICATORS,
    RATIO_INDICATORS,
    age_pyramid,
    choropleth,
    comparison_bars,
    load_geojson,
)
from dashboard.components.narrative import (  # noqa: E402
    age_structure_context,
    county_note,
    dependency_context,
    policy_implications,
)
from src.config import AGE_SEX_CSV, COUNTY_CSV, COUNTY_GEOJSON  # noqa: E402
from src.utils import tidy_county_name  # noqa: E402

st.set_page_config(
    page_title="Kenya county age structure",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; }
      #moh-bar {
        background: #0f2c3d;
        color: #f4f1ea;
        padding: 0.9rem 1.1rem;
        margin: -1.2rem -1rem 1.2rem -1rem;
      }
      #moh-bar h1 { font-size: 1.35rem; margin: 0; color: #f4f1ea; }
      #moh-bar p { margin: 0.2rem 0 0 0; font-size: 0.9rem; opacity: 0.85; }
      [data-testid="stMetricValue"] { font-size: 1.35rem; }
    </style>
    <div id="moh-bar">
      <h1>Kenya county age structure, 2021–2025</h1>
      <p>WorldPop 1 km constrained estimates aggregated to 47 counties (GADM Level 1)</p>
    </div>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_tables(_county_mtime: float, _age_mtime: float, _geo_mtime: float):
    if not COUNTY_CSV.exists():
        st.error("Processed data is missing. Run `python -m src.pipeline --skip-download` first.")
        st.stop()
    counties = pd.read_csv(COUNTY_CSV)
    counties["county_label"] = counties["county"].map(tidy_county_name)
    age_sex = pd.read_csv(AGE_SEX_CSV)
    geojson = load_geojson(COUNTY_GEOJSON)
    return counties, age_sex, geojson


def _sex_filtered_indicators(base: pd.DataFrame, age_sex: pd.DataFrame, year: int, sex: str) -> pd.DataFrame:
    year_ages = age_sex.loc[age_sex["year"] == year]
    if sex != "Total":
        year_ages = year_ages.loc[year_ages["sex"] == sex.lower()]
    child = year_ages.loc[year_ages["age_code"].isin(["00", "01"])].groupby("county")["population"].sum()
    working = year_ages.loc[year_ages["age_code"].isin(
        ["15", "20", "25", "30", "35", "40", "45", "50", "55", "60"]
    )].groupby("county")["population"].sum()
    elderly = year_ages.loc[year_ages["age_code"].isin(
        ["65", "70", "75", "80", "85", "90"]
    )].groupby("county")["population"].sum()
    total = year_ages.groupby("county")["population"].sum()
    out = base.loc[base["year"] == year].copy()
    out["children_under_5"] = out["county"].map(child)
    out["working_age"] = out["county"].map(working)
    out["elderly_65plus"] = out["county"].map(elderly)
    out["total_population"] = out["county"].map(total)
    out["pct_children"] = out["children_under_5"] / out["total_population"] * 100
    out["pct_elderly"] = out["elderly_65plus"] / out["total_population"] * 100
    out["dependency_ratio"] = (out["children_under_5"] + out["elderly_65plus"]) / out["working_age"] * 100
    out["child_dependency_ratio"] = out["children_under_5"] / out["working_age"] * 100
    out["elderly_dependency_ratio"] = out["elderly_65plus"] / out["working_age"] * 100
    return out


def main() -> None:
    counties, age_sex, geojson = load_tables(
        COUNTY_CSV.stat().st_mtime,
        AGE_SEX_CSV.stat().st_mtime,
        COUNTY_GEOJSON.stat().st_mtime,
    )

    with st.sidebar:
        st.subheader("Filters")
        year = st.selectbox("Year", sorted(counties["year"].unique()), index=len(counties["year"].unique()) - 1)
        sex = st.radio("Sex", ["Total", "Male", "Female"], horizontal=True)
        indicator_label = st.selectbox(
            "Map indicator",
            list(INDICATORS),
            index=list(INDICATORS).index("Child Dependency Ratio"),
        )
        gadm_names = sorted(counties["county"].unique())
        selected = st.multiselect(
            "Counties (optional)",
            gadm_names,
            default=[],
            format_func=tidy_county_name,
        )
        st.caption("Click a county on the map to focus the pyramid. Leave the list empty for national view.")

    column = INDICATORS[indicator_label]
    if sex != "Total" and indicator_label in RATIO_INDICATORS and indicator_label == "Sex Ratio":
        st.sidebar.info("Sex ratio is male/female. Map falls back to children under 5 when a single sex is selected.")
        indicator_label = "Children under 5"
        column = "children_under_5"

    year_frame = _sex_filtered_indicators(counties, age_sex, int(year), sex)

    if "map_counties" not in st.session_state:
        st.session_state.map_counties = []
    focus_names = selected or st.session_state.map_counties
    focus = year_frame.loc[year_frame["county"].isin(focus_names)] if focus_names else year_frame

    kpi_total = focus["total_population"].sum()
    kpi_child = focus["children_under_5"].sum()
    kpi_elderly = focus["elderly_65plus"].sum()
    kpi_working = focus["working_age"].sum()
    kpi_dep = (kpi_child + kpi_elderly) / kpi_working * 100
    sex_slice = age_sex.loc[age_sex["year"] == year]
    if focus_names:
        sex_slice = sex_slice.loc[sex_slice["county"].isin(focus_names)]
    males = sex_slice.loc[sex_slice["sex"] == "male", "population"].sum()
    females = sex_slice.loc[sex_slice["sex"] == "female", "population"].sum()
    kpi_sex = males / females * 100 if females else float("nan")

    national_working = year_frame["working_age"].sum()
    national = pd.Series(
        {
            "total_population": year_frame["total_population"].sum(),
            "children_under_5": year_frame["children_under_5"].sum(),
            "elderly_65plus": year_frame["elderly_65plus"].sum(),
            "dependency_ratio": (
                (year_frame["children_under_5"].sum() + year_frame["elderly_65plus"].sum())
                / national_working
                * 100
            ),
            "pct_children": year_frame["children_under_5"].sum() / year_frame["total_population"].sum() * 100,
            "pct_elderly": year_frame["elderly_65plus"].sum() / year_frame["total_population"].sum() * 100,
        }
    )

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Population", f"{kpi_total:,.0f}")
    c2.metric("Dependency ratio", f"{kpi_dep:.1f}")
    c3.metric("Children under 5", f"{kpi_child:,.0f}  ({kpi_child / kpi_total * 100:.1f}%)")
    c4.metric("Elderly 65+", f"{kpi_elderly:,.0f}  ({kpi_elderly / kpi_total * 100:.1f}%)")
    c5.metric("Sex ratio", "—" if sex != "Total" or pd.isna(kpi_sex) else f"{kpi_sex:.1f}")

    map_col, side_col = st.columns((1.35, 1))
    with map_col:
        map_fig = choropleth(
            year_frame,
            geojson,
            column,
            f"{indicator_label}, {year}" + ("" if sex == "Total" else f" ({sex.lower()})"),
        )
        event = st.plotly_chart(map_fig, use_container_width=True, on_select="rerun", selection_mode="points")
        points = event.selection.get("points", []) if event and event.selection else []
        clicked = [point.get("location") for point in points if point.get("location")]
        if clicked:
            st.session_state.map_counties = clicked
        if not selected:
            selected = st.session_state.map_counties

    pyramid_ages = age_sex.loc[age_sex["year"] == year]
    if sex != "Total":
        pyramid_ages = pyramid_ages.loc[pyramid_ages["sex"] == sex.lower()]
    if selected:
        pyramid_ages = pyramid_ages.loc[pyramid_ages["county"].isin(selected)]
        pyramid_title = f"Age pyramid, {year}: " + ", ".join(tidy_county_name(name) for name in selected[:4])
    else:
        pyramid_title = f"Age pyramid, {year}: Kenya"

    with side_col:
        st.plotly_chart(age_pyramid(pyramid_ages, pyramid_title), use_container_width=True)
        compare = year_frame.nlargest(5, column)[["county", "county_label", column]].copy()
        compare = pd.concat(
            [compare, year_frame.nsmallest(3, column)[["county", "county_label", column]]]
        ).drop_duplicates()
        st.plotly_chart(
            comparison_bars(compare, column, f"Highest / lowest {indicator_label}"),
            use_container_width=True,
        )

    st.subheader("Interpretation")
    st.markdown(dependency_context())
    st.markdown(age_structure_context())
    if selected:
        for county_name in selected:
            row = year_frame.loc[year_frame["county"] == county_name].iloc[0]
            st.info(county_note(row, national))
    else:
        st.caption("Select or click a county for a place-specific reading.")
    st.markdown("**Policy implications from this year’s map**")
    for line in policy_implications(year_frame):
        st.markdown(f"- {line}")


if __name__ == "__main__":
    main()
