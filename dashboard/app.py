"""Kenya county age-structure tool for Ministry of Health planning."""

from __future__ import annotations

import html
import sys
import traceback
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.components.charts import age_pyramid, choropleth, extremes_rows, load_geojson  # noqa: E402
from dashboard.components.narrative import (  # noqa: E402
    county_briefing,
    extremes_html,
    fault_copy,
    kenya_briefing,
    method_note,
    rank_line,
)
from dashboard.components.prepare import (  # noqa: E402
    INDICATORS,
    UNITS,
    areas_from_geojson,
    export_bytes,
    format_value,
    indicators_for,
    national_row,
    pad_age_codes,
)
from src.config import AGE_SEX_CSV, COUNTY_CSV, COUNTY_GEOJSON  # noqa: E402
from src.utils import tidy_county_name  # noqa: E402

st.set_page_config(
    page_title="County age structure · Kenya",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CSS = (Path(__file__).resolve().parent / "assets" / "app.css").read_text(encoding="utf-8")
PLOTLY_CONFIG = {"displayModeBar": False, "scrollZoom": False}


@st.cache_data(show_spinner=False)
def load_tables(_county_mtime: float, _age_mtime: float, _geo_mtime: float):
    if not COUNTY_CSV.exists():
        raise FileNotFoundError(COUNTY_CSV)
    counties = pd.read_csv(COUNTY_CSV)
    age_sex = pad_age_codes(pd.read_csv(AGE_SEX_CSV))
    geojson = load_geojson(COUNTY_GEOJSON)
    return counties, age_sex, geojson


def _show_fault(exc: BaseException) -> None:
    headline, advice = fault_copy(exc)
    st.markdown(
        f"""
        <div class="masthead">
          <div class="masthead-rule"></div>
          <p class="kicker">Ministry of Health · Kenya</p>
          <h1>County age structure</h1>
        </div>
        <div class="fault">
          <p class="kicker">Briefing interrupted</p>
          <h2 class="place-name">{html.escape(headline)}</h2>
          <p class="briefing">{html.escape(advice)}</p>
          <p class="fault-code">{html.escape(type(exc).__name__)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("If you are the person who has to fix this"):
        st.code("".join(traceback.format_exception(exc)), language="text")


def _kpi_strip(row: pd.Series, place: str, year: int) -> str:
    cells = [
        ("Population", format_value(row["total_population"], "total_population"), f"{place} · {year}"),
        ("Children per km²", format_value(row["child_density"], "child_density"), "under 5 / km²"),
        (
            "Child dependency",
            format_value(row["child_dependency_ratio"], "child_dependency_ratio"),
            "per 100 aged 15–64",
        ),
        (
            "Share under 5",
            f"{row['pct_children']:.1f}%",
            f"{row['children_under_5']:,.0f} children",
        ),
        (
            "Growth since 2021",
            f"{row['growth_pct']:+.1f}%",
            "this geography",
        ),
    ]
    html_parts = ['<div class="kpi-row">']
    for label, value, sub in cells:
        html_parts.append(
            "<div class='kpi'>"
            f"<p class='kpi-label'>{label}</p>"
            f"<p class='kpi-value'>{value}</p>"
            f"<p class='kpi-sub'>{sub}</p>"
            "</div>"
        )
    html_parts.append("</div>")
    return "".join(html_parts)


def _render() -> None:
    counties, age_sex, geojson = load_tables(
        COUNTY_CSV.stat().st_mtime,
        AGE_SEX_CSV.stat().st_mtime,
        COUNTY_GEOJSON.stat().st_mtime,
    )
    st.markdown(
        """
        <div class="masthead">
          <div class="masthead-rule"></div>
          <p class="kicker">Ministry of Health · Kenya</p>
          <h1>County age structure</h1>
          <p class="lede">
            WorldPop 1 km constrained estimates, 2021–2025. Forty-seven counties.
            Click the map. The dossier on the right is that county against Kenya.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    areas = areas_from_geojson(geojson)
    years = sorted(int(year) for year in counties["year"].unique())
    gadm_names = sorted(counties["county"].unique())

    if "focus_county" not in st.session_state:
        st.session_state.focus_county = "Kenya"
    pending = st.session_state.pop("pending_county", None)
    if pending is not None:
        st.session_state.focus_county = pending

    year_col, sex_col, map_col, county_col, down_col = st.columns(
        [0.72, 0.78, 1.35, 1.25, 0.85],
        vertical_alignment="bottom",
    )
    with year_col:
        year = st.selectbox("Year", years, index=len(years) - 1)
    with sex_col:
        sex = st.selectbox("Sex", ["Total", "Male", "Female"])
    map_options = [name for name, col in INDICATORS.items() if not (sex != "Total" and col == "sex_ratio")]
    if st.session_state.get("map_indicator") not in map_options:
        st.session_state.map_indicator = map_options[0]
    with map_col:
        indicator_label = st.selectbox("Map", map_options, key="map_indicator")
    with county_col:
        st.selectbox(
            "County",
            ["Kenya"] + gadm_names,
            format_func=lambda name: "Kenya" if name == "Kenya" else tidy_county_name(name),
            key="focus_county",
        )

    column = INDICATORS[indicator_label]

    year_frame = indicators_for(counties, age_sex, int(year), sex, areas)
    national = national_row(year_frame)
    focus_name = st.session_state.focus_county
    focus_row = national if focus_name == "Kenya" else year_frame.loc[year_frame["county"] == focus_name].iloc[0]
    place = "Kenya" if focus_name == "Kenya" else tidy_county_name(focus_name)

    with down_col:
        st.download_button(
            "Download CSV",
            data=export_bytes(year_frame, int(year), sex),
            file_name=f"kenya_county_age_structure_{year}_{sex.lower()}.csv",
            mime="text/csv",
            width="stretch",
        )

    st.markdown(_kpi_strip(focus_row, place, int(year)), unsafe_allow_html=True)

    stage, dossier = st.columns((1.42, 1), gap="medium")
    with stage:
        sex_note = "" if sex == "Total" else f" · {sex.lower()} only"
        st.markdown(
            f"<p class='caption-quiet'>{indicator_label}, {year}{sex_note}. Click a county.</p>",
            unsafe_allow_html=True,
        )
        map_fig = choropleth(year_frame, geojson, column, UNITS[column])
        event = st.plotly_chart(
            map_fig,
            width="stretch",
            on_select="rerun",
            selection_mode="points",
            config=PLOTLY_CONFIG,
            theme=None,
            key="county_map",
        )
        points = event.selection.get("points", []) if event and event.selection else []
        clicked = [point.get("location") for point in points if point.get("location")]
        if "last_map_click" not in st.session_state:
            st.session_state.last_map_click = None
        if clicked and clicked[0] != st.session_state.last_map_click:
            st.session_state.last_map_click = clicked[0]
            if clicked[0] != st.session_state.focus_county:
                st.session_state.pending_county = clicked[0]
                st.rerun()
        high, low = extremes_rows(year_frame, column)
        st.markdown(extremes_html(high, low, indicator_label), unsafe_allow_html=True)

    pyramid_national = age_sex.loc[age_sex["year"] == year]
    if focus_name == "Kenya":
        pyramid_local = pyramid_national
        overlay = None
        pyramid_caption = "National age structure as a share of population."
    else:
        pyramid_local = pyramid_national.loc[pyramid_national["county"] == focus_name]
        overlay = pyramid_national
        pyramid_caption = f"{place} as a share of its own population. Dotted line is Kenya."

    with dossier:
        st.markdown("<p class='kicker'>County dossier</p>", unsafe_allow_html=True)
        st.markdown(f"<h2 class='place-name'>{place}</h2>", unsafe_allow_html=True)
        if focus_name == "Kenya":
            st.markdown(
                f"<p class='rankline'>{year} · 47 counties on this map</p>",
                unsafe_allow_html=True,
            )
            brief = kenya_briefing(year_frame, int(year), column, indicator_label)
        else:
            st.markdown(
                f"<p class='rankline'>{rank_line(year_frame, focus_name, column, indicator_label)}</p>",
                unsafe_allow_html=True,
            )
            brief = county_briefing(focus_row, national, column, indicator_label)
        st.plotly_chart(
            age_pyramid(pyramid_local, overlay, place),
            width="stretch",
            config=PLOTLY_CONFIG,
            theme=None,
        )
        st.markdown(f"<p class='caption-quiet'>{pyramid_caption}</p>", unsafe_allow_html=True)
        st.markdown(f"<div class='briefing'><p>{brief}</p></div>", unsafe_allow_html=True)

    st.markdown(f"<p class='method'>{method_note()}</p>", unsafe_allow_html=True)


def main() -> None:
    st.set_option("client.showErrorDetails", "none")
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
    try:
        _render()
    except Exception as exc:
        _show_fault(exc)


if __name__ == "__main__":
    main()
