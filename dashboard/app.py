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

st.set_page_config(
    page_title="County age structure · Kenya",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS_PATH = Path(__file__).resolve().parent / "assets" / "app.css"
DARK_CSS_PATH = Path(__file__).resolve().parent / "assets" / "app-dark.css"
PLOTLY_CONFIG = {"displayModeBar": False, "scrollZoom": False}
BOOT_ERROR: BaseException | None = None

try:
    from dashboard.components.charts import age_pyramid, choropleth, extremes_rows, load_geojson, theme_palette  # noqa: E402
    from dashboard.components.i18n import set_lang, t  # noqa: E402
    from dashboard.components.narrative import (  # noqa: E402
        cards_html,
        county_table_html,
        extremes_line,
        fault_copy,
        how_to_html,
        inspector_html,
        interpretation_cards,
        place_metrics_html,
        site_footer_html,
        site_header_html,
        rank_line,
        table_analytics,
        who_lives_here_html,
    )
    from dashboard.components.prepare import (  # noqa: E402
        INDICATORS,
        areas_from_geojson,
        export_bytes,
        format_value,
        indicators_for,
        national_row,
        pad_age_codes,
    )
    from src.config import AGE_SEX_CSV, COUNTY_CSV, COUNTY_GEOJSON  # noqa: E402
    from src.utils import tidy_county_name  # noqa: E402
except Exception as exc:  # noqa: BLE001 — show it on the page, not as a redacted Streamlit box
    BOOT_ERROR = exc


@st.cache_data(show_spinner=False)
def load_tables(_county_mtime: float, _age_mtime: float, _geo_mtime: float):
    if not COUNTY_CSV.exists():
        raise FileNotFoundError(COUNTY_CSV)
    counties = pd.read_csv(COUNTY_CSV)
    age_sex = pad_age_codes(pd.read_csv(AGE_SEX_CSV))
    geojson = load_geojson(COUNTY_GEOJSON)
    return counties, age_sex, geojson


def _show_fault(exc: BaseException) -> None:
    headline = "Forty-seven counties are present and accounted for. This page is not."
    advice = "Refresh once. If it still lies down, close the tab and start the app again."
    kicker = "Briefing interrupted"
    ministry = "Ministry of Health · Kenya"
    title = "County age structure"
    fix_label = "If you are the person who has to fix this"
    try:
        headline, advice = fault_copy(exc)
        kicker, ministry, title = t("fault.kicker"), t("ministry"), t("title")
        fix_label = t("fault.fix")
    except Exception:
        if isinstance(exc, ImportError):
            headline = "The page loaded faster than its own files."
            advice = "Refresh. If the pink box comes back, stop Streamlit and start it again from the project folder."
    try:
        chrome = site_header_html()
    except Exception:
        chrome = (
            "<div class='site-header' role='banner'><div class='site-header-inner'>"
            "<div class='site-header-copy'>"
            f"<p class='kicker'>{html.escape(ministry)}</p>"
            f"<p class='page-title'>{html.escape(title)}</p>"
            "</div></div></div>"
        )
    _paint(
        chrome
        + f"""
        <div class="fault">
          <p class="kicker">{html.escape(kicker)}</p>
          <h2 class="place-name">{html.escape(headline)}</h2>
          <p class="briefing">{html.escape(advice)}</p>
          <p class="fault-code">{html.escape(type(exc).__name__)}</p>
        </div>
        """
    )
    with st.expander(fix_label):
        st.code("".join(traceback.format_exception(exc)), language="text")


def _kpi_strip(row: pd.Series, place: str, year: int, sex: str) -> str:
    who = t("sex.all") if sex == "Total" else t(f"sex.{sex}").lower()
    cells = [
        (t("kpi.population"), format_value(row["total_population"], "total_population"), f"{place} · {year} · {who}"),
        (t("kpi.density"), format_value(row["child_density"], "child_density"), t("kpi.under5_unit")),
        (
            t("kpi.under5"),
            f"{row['pct_children']:.1f}%",
            t("kpi.children", n=f"{row['children_under_5']:,.0f}"),
        ),
        (
            t("kpi.dependency"),
            format_value(row["child_dependency_ratio"], "child_dependency_ratio"),
            t("kpi.dep_unit"),
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


def _paint(markup: str) -> None:
    """HTML via st.html so Markdown cannot eat CSS (#MainMenu) or the table."""
    if markup and str(markup).strip():
        st.html(markup)


def _clicked_county(event, allowed: list[str]) -> str | None:
    try:
        selection = getattr(event, "selection", None)
        if not selection:
            return None
        points = selection.get("points", []) if hasattr(selection, "get") else getattr(selection, "points", [])
        if not points:
            return None
        point = points[0]
        if isinstance(point, dict):
            loc = point.get("location") or point.get("geo") or point.get("hovertext")
        else:
            loc = getattr(point, "location", None)
        loc = str(loc) if loc is not None else ""
        if loc in allowed:
            return loc
    except (AttributeError, IndexError, KeyError, TypeError):
        return None
    return None


def _render() -> None:
    counties, age_sex, geojson = load_tables(
        COUNTY_CSV.stat().st_mtime,
        AGE_SEX_CSV.stat().st_mtime,
        COUNTY_GEOJSON.stat().st_mtime,
    )
    _paint(site_header_html())
    _paint(how_to_html())
    areas = areas_from_geojson(geojson)
    years = sorted(int(year) for year in counties["year"].unique())
    gadm_names = sorted(counties["county"].unique())
    allowed = ["Kenya", *gadm_names]

    if "focus_county" not in st.session_state:
        st.session_state.focus_county = "Kenya"
    pending = st.session_state.pop("pending_county", None)
    if pending in allowed:
        st.session_state.focus_county = pending
    if st.session_state.focus_county not in allowed:
        st.session_state.focus_county = "Kenya"

    with st.sidebar:
        _paint(
            f'<div class="rail"><p class="kicker">{html.escape(t("ministry"))}</p>'
            f'<p class="rail-title">{html.escape(t("rail_title"))}</p></div>'
        )
        lang_choice = st.radio(
            t("language"),
            ["en", "sw"],
            format_func=lambda code: "English" if code == "en" else "Kiswahili",
            horizontal=True,
            key="lang",
        )
        set_lang(lang_choice)
        st.radio(
            t("theme"),
            ["light", "dark"],
            format_func=lambda code: t(f"theme.{code}"),
            horizontal=True,
            key="theme",
        )
        year = st.selectbox(t("year"), years, index=len(years) - 1, key="year")
        sex = st.selectbox(
            t("sex"),
            ["Total", "Male", "Female"],
            format_func=lambda name: t(f"sex.{name}"),
            key="sex",
        )
        map_options = [name for name, col in INDICATORS.items() if not (sex != "Total" and col == "sex_ratio")]
        if st.session_state.get("map_indicator") not in map_options:
            st.session_state.map_indicator = map_options[0]
        indicator_key = st.selectbox(
            t("map"),
            map_options,
            format_func=lambda name: t(f"indicator.{INDICATORS[name]}"),
            key="map_indicator",
        )
        st.selectbox(
            t("county"),
            ["Kenya"] + gadm_names,
            format_func=lambda name: "Kenya" if name == "Kenya" else tidy_county_name(name),
            key="focus_county",
        )
        compare_options = ["Kenya"] + [name for name in gadm_names if name != st.session_state.focus_county]
        if st.session_state.get("compare_with") not in compare_options:
            st.session_state.compare_with = "Kenya"
        st.selectbox(
            t("compare"),
            compare_options,
            format_func=lambda name: "Kenya" if name == "Kenya" else tidy_county_name(name),
            key="compare_with",
        )
        legacy_unit = st.session_state.get("pyramid_unit")
        if legacy_unit == "People":
            st.session_state.pyramid_unit = "count"
        elif legacy_unit == "Share of population (%)":
            st.session_state.pyramid_unit = "share"
        pyramid_mode = st.radio(
            t("age_mix"),
            ["share", "count"],
            format_func=lambda mode: t(f"pyramid.{mode}"),
            horizontal=True,
            key="pyramid_unit",
        )
        column = INDICATORS[indicator_key]
        shown = t(f"indicator.{column}")
        year_frame = indicators_for(counties, age_sex, int(year), sex, areas)
        st.download_button(
            t("download"),
            data=export_bytes(year_frame, int(year), sex),
            file_name=f"kenya_county_age_structure_{year}_{sex.lower()}.csv",
            mime="text/csv",
            width="stretch",
        )
        _paint(f"<p class='method'>{html.escape(t('footer.rail'))}</p>")

    national = national_row(year_frame)
    focus_name = st.session_state.focus_county
    compare_name = st.session_state.compare_with
    hit = year_frame.loc[year_frame["county"] == focus_name]
    if focus_name == "Kenya" or hit.empty:
        focus_name = "Kenya"
        focus_row = national
        place = "Kenya"
    else:
        focus_row = hit.iloc[0]
        place = tidy_county_name(focus_name)
    if compare_name == "Kenya" or compare_name == focus_name:
        compare_name = "Kenya"
        compare_row = national
        compare_label = "Kenya"
    else:
        compare_hit = year_frame.loc[year_frame["county"] == compare_name]
        if compare_hit.empty:
            compare_name = "Kenya"
            compare_row = national
            compare_label = "Kenya"
        else:
            compare_row = compare_hit.iloc[0]
            compare_label = tidy_county_name(compare_name)
    sex_label = t("sex.all") if sex == "Total" else t(f"sex.{sex}").lower()
    vs_bit = "" if compare_label == place else f" · vs {compare_label}"
    view_line = f"{place} · {year} · {sex_label} · {shown}{vs_bit}"
    pal = theme_palette(st.session_state.get("theme", "light"))

    _paint(f"<p class='view-line'>{html.escape(view_line)}</p>")
    _paint(_kpi_strip(national, "Kenya", int(year), sex))

    if focus_name == "Kenya":
        rank = t("rank.kenya", year=year)
        peek = inspector_html(None, column, shown, int(year), rank)
    else:
        rank = rank_line(year_frame, focus_name, column, shown)
        peek = inspector_html(
            focus_row,
            column,
            shown,
            int(year),
            rank,
            compare_row,
            compare_label,
        )
    analytics = table_analytics(
        year_frame,
        national,
        column,
        shown,
        None if focus_name == "Kenya" else focus_name,
    )

    _paint(f"<div class='section-head section-head-map'><p class='kicker'>{html.escape(t('section.map'))}</p></div>")
    only = "" if sex == "Total" else f" · {t('sex.only', who=t(f'sex.{sex}').lower())}"
    map_title = f"{shown}, {year}{only}"
    map_fig = choropleth(year_frame, geojson, column, shown, map_title, pal)
    map_col, peek_col = st.columns((3.0, 0.9), gap="medium")
    with map_col:
        event = st.plotly_chart(
            map_fig,
            width="stretch",
            on_select="rerun",
            selection_mode="points",
            config=PLOTLY_CONFIG,
            theme=None,
            key=f"county_map_{year}_{sex}_{column}",
        )
        clicked = _clicked_county(event, gadm_names)
        if "last_map_click" not in st.session_state:
            st.session_state.last_map_click = None
        if clicked and clicked != st.session_state.last_map_click:
            st.session_state.last_map_click = clicked
            if clicked != st.session_state.focus_county:
                st.session_state.pending_county = clicked
                st.rerun()
        high, low = extremes_rows(year_frame, column)
        _paint(
            f"<p class='caption-quiet'>{html.escape(t('map.hover', extremes=extremes_line(high, low)))}</p>"
        )
    with peek_col:
        _paint(peek)

    pyramid_year = age_sex.loc[age_sex["year"] == year]
    if sex != "Total":
        pyramid_year = pyramid_year.loc[pyramid_year["sex"] == sex.lower()]
    pyramid_local = pyramid_year if focus_name == "Kenya" else pyramid_year.loc[pyramid_year["county"] == focus_name]
    overlay = pyramid_year if compare_name == "Kenya" else pyramid_year.loc[pyramid_year["county"] == compare_name]
    unit_words = t("pyramid.unit_share") if pyramid_mode == "share" else t("pyramid.unit_count")
    if compare_label == place:
        pyramid_title = t("pyramid.title", place=place, year=year)
        pyramid_caption = t("pyramid.caption", unit=unit_words)
    else:
        pyramid_title = t("pyramid.title_vs", place=place, other=compare_label, year=year)
        pyramid_caption = t("pyramid.caption_vs", place=place, other=compare_label, unit=unit_words)
    if sex != "Total":
        pyramid_title += f" · {t('sex.only', who=t(f'sex.{sex}').lower())}"

    _paint(f"<div class='section-head section-head-age'><p class='kicker'>{html.escape(t('section.age'))}</p></div>")
    _paint(place_metrics_html(focus_row, compare_row, place, compare_label))
    _paint(
        who_lives_here_html(
            focus_row,
            compare_row,
            place,
            compare_label,
            year_frame if place == compare_label else None,
        )
    )
    st.plotly_chart(
        age_pyramid(
            pyramid_local,
            overlay,
            place,
            compare_label,
            sex,
            pyramid_title,
            pyramid_mode,
            pal,
        ),
        width="stretch",
        config=PLOTLY_CONFIG,
        theme=None,
        key=f"pyramid_{year}_{sex}_{focus_name}_{compare_name}_{pyramid_mode}",
    )
    _paint(f"<p class='caption-quiet'>{html.escape(pyramid_caption)}</p>")

    _paint(
        f"<div class='section-head section-head-read'><p class='kicker'>{html.escape(t('section.interpret'))}</p></div>"
    )
    _paint(cards_html(interpretation_cards(focus_row, national, place, year_frame)))

    _paint(f"<div class='section-head section-head-table'><p class='kicker'>{html.escape(t('section.table'))}</p></div>")
    _paint(f"<p class='caption-quiet'>{html.escape(t('table.caption', indicator=shown))}</p>")
    _paint(
        county_table_html(
            year_frame,
            column,
            shown,
            None if focus_name == "Kenya" else focus_name,
            national,
        )
    )
    _paint(f"<div class='section-head section-head-read'><p class='kicker'>{html.escape(t('section.read'))}</p></div>")
    _paint(cards_html(analytics))
    _paint(site_footer_html())


def main() -> None:
    st.html(CSS_PATH)
    if BOOT_ERROR is not None:
        _show_fault(BOOT_ERROR)
        return
    choice = st.session_state.get("lang", "en")
    set_lang(choice if choice in ("en", "sw") else "en")
    if st.session_state.get("theme") == "dark":
        st.html(DARK_CSS_PATH)
    try:
        _render()
    except Exception as exc:
        _show_fault(exc)


if __name__ == "__main__":
    main()
