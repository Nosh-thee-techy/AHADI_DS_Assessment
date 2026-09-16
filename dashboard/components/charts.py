"""Plotly charts for the county age-structure tool."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from dashboard.components.i18n import t
from dashboard.components.prepare import format_value, pad_age_codes

INK = "#1c1917"
MUTED = "#5c574e"
PAPER = "#f3efe6"
MAP_PAPER = "#e2e8e4"
AGE_PAPER = "#e4e6ee"
MALE = "#1e4d7b"
FEMALE = "#9c3412"
COMPARE = "#1f4d3a"
LINE = "#cfc8bc"

# Atlas sequential: paper → ochre → rust → ink. Burden, not a heatmap toy.
LOAD = [
    [0.0, "#f7f1e4"],
    [0.22, "#e4c27a"],
    [0.45, "#c4783a"],
    [0.72, "#8a3e28"],
    [1.0, "#2c1810"],
]
DIVERGE = [
    [0.0, "#3d4f6f"],
    [0.5, "#f4efe6"],
    [1.0, "#8a3e28"],
]

_FONT = dict(family="Segoe UI, Helvetica Neue, Arial, sans-serif", color=INK, size=12)


def theme_palette(theme: str) -> dict:
    if theme == "dark":
        return dict(
            ink="#f0ebe3",
            muted="#b4ada3",
            paper="#161513",
            map="#1a221c",
            age="#1a1d26",
            hover="#2a2722",
            line="#3a3732",
            male="#6ea0d4",
            female="#e08a6a",
            compare="#7dba96",
        )
    return dict(
        ink=INK,
        muted=MUTED,
        paper=PAPER,
        map=MAP_PAPER,
        age=AGE_PAPER,
        hover="#f7f3eb",
        line=LINE,
        male=MALE,
        female=FEMALE,
        compare=COMPARE,
    )


def _layout(
    fig: go.Figure,
    height: int,
    title: str | None = None,
    paper: str = PAPER,
    margin: dict | None = None,
    pal: dict | None = None,
    stack_title_legend: bool = False,
) -> go.Figure:
    pal = pal or theme_palette("light")
    ink = pal["ink"]
    if stack_title_legend and title:
        # Title.y is clamped to [0, 1]; use container coords so the legend
        # sits on a second row in the top margin instead of through the title.
        title_spec = dict(
            text=title,
            font=dict(size=17, color=ink),
            x=0,
            xanchor="left",
            xref="paper",
            y=1,
            yanchor="top",
            yref="container",
            pad=dict(t=10, b=0),
        )
        legend_spec = dict(
            orientation="h",
            yanchor="top",
            y=0.935,
            yref="container",
            x=0,
            xanchor="left",
            font=dict(size=12, color=ink),
            bgcolor="rgba(0,0,0,0)",
            itemsizing="constant",
            tracegroupgap=12,
        )
        default_margin = dict(r=16, t=108, l=16, b=16)
    else:
        title_spec = (
            dict(text=title, font=dict(size=17, color=ink), x=0, xanchor="left") if title else None
        )
        legend_spec = dict(
            orientation="h",
            yanchor="bottom",
            y=1.06 if title else 1.02,
            x=0,
            font=dict(size=12, color=ink),
            bgcolor="rgba(0,0,0,0)",
        )
        default_margin = dict(r=16, t=52 if title else 16, l=16, b=16)
    fig.update_layout(
        height=height,
        margin=margin or default_margin,
        paper_bgcolor=paper,
        plot_bgcolor=paper,
        font=dict(family=_FONT["family"], color=ink, size=12),
        title=title_spec,
        legend=legend_spec,
        hoverlabel=dict(
            bgcolor=pal["hover"],
            bordercolor=ink,
            font=dict(family=_FONT["family"], size=13, color=ink),
            align="left",
        ),
        hovermode="closest",
    )
    return fig


def _hover_customdata(frame: pd.DataFrame, column: str) -> list[list[str]]:
    rows = []
    for row in frame.itertuples(index=False):
        sex = "—" if pd.isna(row.sex_ratio) else f"{row.sex_ratio:.1f}"
        rows.append(
            [
                str(row.county_label),
                format_value(getattr(row, column), column),
                f"{row.total_population:,.0f}",
                f"{row.children_under_5:,.0f}",
                f"{row.pct_children:.1f}",
                f"{row.elderly_65plus:,.0f}",
                f"{row.pct_elderly:.1f}",
                f"{row.dependency_ratio:.1f}",
                f"{row.child_dependency_ratio:.1f}",
                f"{row.elderly_dependency_ratio:.1f}",
                sex,
                f"{row.child_density:.1f}",
            ]
        )
    return rows


def choropleth(
    frame: pd.DataFrame,
    geojson: dict,
    column: str,
    colorbar_title: str,
    title: str,
    palette: dict | None = None,
) -> go.Figure:
    pal = palette or theme_palette("light")
    kwargs = dict(
        geojson=geojson,
        locations=frame["county"],
        z=frame[column],
        featureidkey="properties.county",
        colorscale=DIVERGE if column == "sex_ratio" else LOAD,
        marker_line_width=0.45,
        marker_line_color=pal["ink"],
        colorbar=dict(
            title=dict(text=colorbar_title, side="right", font=dict(size=11, color=pal["muted"])),
            thickness=9,
            len=0.68,
            outlinewidth=0,
            tickfont=dict(size=10, color=pal["muted"]),
            bgcolor=pal["map"],
        ),
        customdata=_hover_customdata(frame, column),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            f"{colorbar_title}: %{{customdata[1]}}<br>"
            f"{t('hover.people')}: %{{customdata[2]}}<br>"
            f"{t('hover.under5')}: %{{customdata[3]}} ({t('hover.pct', pct='%{customdata[4]}')})<br>"
            f"{t('hover.old')}: %{{customdata[5]}} ({t('hover.pct', pct='%{customdata[6]}')})<br>"
            f"{t('hover.dep')}: %{{customdata[7]}}<br>"
            f"{t('hover.child_dep')}: %{{customdata[8]}} · {t('hover.old_dep')}: %{{customdata[9]}}<br>"
            f"{t('hover.sex')}: %{{customdata[10]}}<br>"
            f"{t('hover.density')}: %{{customdata[11]}}"
            "<extra></extra>"
        ),
    )
    if column == "sex_ratio":
        kwargs["zmid"] = 100
    fig = go.Figure(go.Choropleth(**kwargs))
    fig.update_geos(
        visible=False,
        bgcolor=pal["map"],
        projection_type="mercator",
        lonaxis_range=[33.55, 42.15],
        lataxis_range=[-4.95, 5.65],
        showframe=False,
        showcoastlines=False,
        showland=False,
        showocean=False,
        showlakes=False,
        showrivers=False,
        showcountries=False,
    )
    return _layout(
        fig,
        810,
        title,
        paper=pal["map"],
        pal=pal,
        margin=dict(l=8, r=92, t=56, b=8),
    )


def _age_counts(age_sex: pd.DataFrame) -> tuple[list[str], pd.Series, pd.Series]:
    age_sex = pad_age_codes(age_sex)
    grouped = (
        age_sex.groupby(["age_group", "age_code", "sex"], as_index=False)["population"]
        .sum()
        .sort_values("age_code")
    )
    ages = grouped["age_group"].drop_duplicates().tolist()
    males = grouped.loc[grouped["sex"] == "male"].set_index("age_group")["population"].reindex(ages).fillna(0)
    females = grouped.loc[grouped["sex"] == "female"].set_index("age_group")["population"].reindex(ages).fillna(0)
    return ages, males, females


def _pct(series: pd.Series, total: float) -> pd.Series:
    if total <= 0:
        return series * 0.0
    return series / total * 100


def _hover_pairs(counts: pd.Series, pcts: pd.Series) -> list[list[float]]:
    return [[float(count), float(pct)] for count, pct in zip(counts.tolist(), pcts.tolist())]


def _axis_ticks(span: float, mode: str) -> tuple[list[float], list[str]]:
    if mode == "share":
        ticks = [-8.0, -4.0, 0.0, 4.0, 8.0] if span <= 10 else [-12.0, -6.0, 0.0, 6.0, 12.0]
        return ticks, [str(int(abs(tick))) for tick in ticks]
    span = max(span, 1.0)
    magnitude = 10 ** max(0, len(str(int(span))) - 2)
    step = magnitude
    while span / step > 4:
        step *= 2
    ticks = []
    value = 0.0
    while value <= span * 1.02:
        ticks.append(value)
        value += step
    signed = [-tick for tick in reversed(ticks) if tick] + ticks
    return signed, [f"{abs(tick):,.0f}" for tick in signed]


def age_pyramid(
    county_ages: pd.DataFrame,
    overlay_ages: pd.DataFrame | None = None,
    county_name: str = "Kenya",
    overlay_name: str = "Kenya",
    sex: str = "Total",
    title: str | None = None,
    mode: str = "share",
    palette: dict | None = None,
) -> go.Figure:
    pal = palette or theme_palette("light")
    ages, male_n, female_n = _age_counts(county_ages)
    total = float(male_n.sum() + female_n.sum())
    male_p, female_p = _pct(male_n, total), _pct(female_n, total)
    male_x = male_p if mode == "share" else male_n
    female_x = female_p if mode == "share" else female_n
    one_sex = sex != "Total" or float(male_n.sum()) == 0 or float(female_n.sum()) == 0
    hover_male = (
        f"<b>%{{y}}</b> · {t('chart.male')}<br>%{{customdata[0]:,.0f}} {t('chart.people')}<br>"
        f"%{{customdata[1]:.1f}}% {t('chart.of_place')}<extra></extra>"
    )
    hover_female = (
        f"<b>%{{y}}</b> · {t('chart.female')}<br>%{{customdata[0]:,.0f}} {t('chart.people')}<br>"
        f"%{{customdata[1]:.1f}}% {t('chart.of_place')}<extra></extra>"
    )
    hover_one = (
        f"<b>%{{y}}</b><br>%{{customdata[0]:,.0f}} {t('chart.people')}<br>"
        f"%{{customdata[1]:.1f}}% {t('chart.of_place')}<extra></extra>"
    )
    overlay_hover = (
        f"<b>%{{y}}</b> · {overlay_name}"
        f"<br>%{{customdata[0]:,.0f}} {t('chart.people')}<br>%{{customdata[1]:.1f}}% {t('chart.of_place')} "
        f"({overlay_name})<extra></extra>"
    )
    fig = go.Figure()
    show_overlay = overlay_ages is not None and overlay_name != county_name and not overlay_ages.empty
    pyramid_margin = dict(l=92, r=36, t=112 if title else 48, b=72)

    if one_sex:
        use_male = sex == "Male" or float(female_n.sum()) == 0
        values = male_x if use_male else female_x
        counts = male_n if use_male else female_n
        pcts = male_p if use_male else female_p
        colour = pal["male"] if use_male else pal["female"]
        who = t("chart.males") if use_male else t("chart.females")
        fig.add_bar(
            y=ages,
            x=values,
            orientation="h",
            name=county_name,
            marker_color=colour,
            hovertemplate=hover_one,
            customdata=_hover_pairs(counts, pcts),
        )
        if show_overlay:
            o_ages, o_m, o_f = _age_counts(overlay_ages)
            o_total = float(o_m.sum() + o_f.sum())
            o_counts = o_m if use_male else o_f
            o_pcts = _pct(o_counts, o_total)
            o_x = o_pcts if mode == "share" else o_counts
            fig.add_scatter(
                y=o_ages,
                x=o_x,
                mode="lines",
                name=overlay_name,
                line=dict(color=pal["compare"], width=2.4, dash="dot"),
                hovertemplate=overlay_hover,
                customdata=_hover_pairs(o_counts, o_pcts),
            )
        axis_title = t("chart.share_who", who=who) if mode == "share" else t("chart.count_who", who=who)
        fig.update_xaxes(
            title=dict(text=axis_title, font=dict(size=12, color=pal["muted"]), standoff=18),
            gridcolor=pal["line"],
            automargin=True,
        )
        fig.update_yaxes(
            title=None,
            automargin=True,
            tickfont=dict(size=12),
            ticksuffix="  ",
            categoryorder="array",
            categoryarray=ages,
        )
        return _layout(
            fig,
            700,
            title,
            paper=pal["age"],
            margin=pyramid_margin,
            pal=pal,
            stack_title_legend=bool(title),
        )

    fig.add_bar(
        y=ages,
        x=-male_x,
        orientation="h",
        name=t("chart.male_legend"),
        marker_color=pal["male"],
        hovertemplate=hover_male,
        customdata=_hover_pairs(male_n, male_p),
    )
    fig.add_bar(
        y=ages,
        x=female_x,
        orientation="h",
        name=t("chart.female_legend"),
        marker_color=pal["female"],
        hovertemplate=hover_female,
        customdata=_hover_pairs(female_n, female_p),
    )
    if show_overlay:
        o_ages, o_m, o_f = _age_counts(overlay_ages)
        o_total = float(o_m.sum() + o_f.sum())
        o_mp, o_fp = _pct(o_m, o_total), _pct(o_f, o_total)
        o_mx = o_mp if mode == "share" else o_m
        o_fx = o_fp if mode == "share" else o_f
        fig.add_scatter(
            y=o_ages,
            x=-o_mx,
            mode="lines",
            name=overlay_name,
            line=dict(color=pal["compare"], width=2.4, dash="dot"),
            hovertemplate=overlay_hover,
            customdata=_hover_pairs(o_m, o_mp),
        )
        fig.add_scatter(
            y=o_ages,
            x=o_fx,
            mode="lines",
            name=overlay_name,
            line=dict(color=pal["compare"], width=2.4, dash="dot"),
            showlegend=False,
            hovertemplate=overlay_hover,
            customdata=_hover_pairs(o_f, o_fp),
        )
    peak = float(max(male_x.max(), female_x.max()))
    span = max(8.0 if mode == "share" else 1.0, peak * 1.18)
    ticks, ticktext = _axis_ticks(span, mode)
    fig.update_layout(barmode="relative", bargap=0.18)
    fig.update_xaxes(
        range=[-span, span],
        tickvals=ticks,
        ticktext=ticktext,
        title=dict(
            text=t("chart.share_pop") if mode == "share" else t("chart.people_axis"),
            font=dict(size=12, color=pal["muted"]),
            standoff=18,
        ),
        gridcolor=pal["line"],
        zeroline=True,
        zerolinecolor=pal["ink"],
        zerolinewidth=0.8,
        automargin=True,
    )
    fig.update_yaxes(
        title=None,
        automargin=True,
        tickfont=dict(size=12),
        ticksuffix="  ",
        categoryorder="array",
        categoryarray=ages,
    )
    return _layout(
        fig,
        700,
        title,
        paper=pal["age"],
        margin=pyramid_margin,
        pal=pal,
        stack_title_legend=bool(title),
    )


def extremes_rows(frame: pd.DataFrame, column: str, n: int = 5) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    high = frame.nlargest(n, column)
    low = frame.nsmallest(n, column)
    high_rows = [
        (row.county_label, format_value(getattr(row, column), column)) for row in high.itertuples()
    ]
    low_rows = [
        (row.county_label, format_value(getattr(row, column), column)) for row in low.itertuples()
    ]
    return high_rows, low_rows


def load_geojson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
