"""Plotly charts for the county age-structure tool."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from dashboard.components.prepare import format_value, pad_age_codes

INK = "#1c1917"
MUTED = "#5c574e"
PAPER = "#f3efe6"
MALE = "#3d4f6f"
FEMALE = "#8a3e28"
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


def _layout(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(r=8, t=8, l=8, b=8),
        paper_bgcolor=PAPER,
        plot_bgcolor=PAPER,
        font=_FONT,
        title=None,
        legend=dict(
            orientation="h",
            y=1.02,
            x=0,
            font=dict(size=11, color=MUTED),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def choropleth(frame: pd.DataFrame, geojson: dict, column: str, colorbar_title: str) -> go.Figure:
    custom = frame[
        [
            "county_label",
            "total_population",
            "children_under_5",
            "pct_children",
            "elderly_65plus",
            "pct_elderly",
            "child_dependency_ratio",
            "child_density",
            "growth_pct",
            column,
        ]
    ].to_numpy()
    kwargs = dict(
        geojson=geojson,
        locations=frame["county"],
        z=frame[column],
        featureidkey="properties.county",
        colorscale=DIVERGE if column == "sex_ratio" else LOAD,
        marker_line_width=0.45,
        marker_line_color=INK,
        colorbar=dict(
            title=dict(text=colorbar_title, side="right", font=dict(size=11, color=MUTED)),
            thickness=9,
            len=0.68,
            outlinewidth=0,
            tickfont=dict(size=10, color=MUTED),
            bgcolor=PAPER,
        ),
        customdata=custom,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            f"{colorbar_title}: %{{customdata[9]:.1f}}<br>"
            "Population: %{customdata[1]:,.0f}<br>"
            "Under 5: %{customdata[2]:,.0f} (%{customdata[3]:.1f}%)<br>"
            "65+: %{customdata[4]:,.0f} (%{customdata[5]:.1f}%)<br>"
            "Child dependency: %{customdata[6]:.1f}<br>"
            "Children / km²: %{customdata[7]:.1f}<br>"
            "Growth since 2021: %{customdata[8]:.1f}%<extra></extra>"
        ),
    )
    if column == "sex_ratio":
        kwargs["zmid"] = 100
        kwargs["hovertemplate"] = kwargs["hovertemplate"].replace(
            f"{colorbar_title}: %{{customdata[9]:.1f}}",
            "Sex ratio: %{customdata[9]:.1f}",
        )
    if column == "total_population":
        kwargs["hovertemplate"] = kwargs["hovertemplate"].replace(
            f"{colorbar_title}: %{{customdata[9]:.1f}}<br>",
            "",
        )
    fig = go.Figure(go.Choropleth(**kwargs))
    fig.update_geos(fitbounds="locations", visible=False, bgcolor=PAPER)
    return _layout(fig, 620)


def _age_shares(age_sex: pd.DataFrame) -> tuple[list[str], pd.Series, pd.Series, float]:
    age_sex = pad_age_codes(age_sex)
    grouped = (
        age_sex.groupby(["age_group", "age_code", "sex"], as_index=False)["population"]
        .sum()
        .sort_values("age_code")
    )
    ages = grouped["age_group"].drop_duplicates().tolist()
    males = grouped.loc[grouped["sex"] == "male"].set_index("age_group")["population"].reindex(ages).fillna(0)
    females = grouped.loc[grouped["sex"] == "female"].set_index("age_group")["population"].reindex(ages).fillna(0)
    total = float(males.sum() + females.sum())
    if total <= 0:
        return ages, males, females, 0.0
    return ages, males / total * 100, females / total * 100, total


def age_pyramid(
    county_ages: pd.DataFrame,
    national_ages: pd.DataFrame | None = None,
    county_name: str = "Kenya",
) -> go.Figure:
    ages, males, females, _ = _age_shares(county_ages)
    fig = go.Figure()
    fig.add_bar(
        y=ages,
        x=-males,
        orientation="h",
        name="Male" if county_name == "Kenya" else f"{county_name} · male",
        marker_color=MALE,
        hovertemplate="%{y} male: %{customdata:.2f}%<extra></extra>",
        customdata=males,
    )
    fig.add_bar(
        y=ages,
        x=females,
        orientation="h",
        name="Female" if county_name == "Kenya" else f"{county_name} · female",
        marker_color=FEMALE,
        hovertemplate="%{y} female: %{customdata:.2f}%<extra></extra>",
        customdata=females,
    )
    if national_ages is not None and county_name != "Kenya":
        nat_ages, nat_m, nat_f, _ = _age_shares(national_ages)
        fig.add_scatter(
            y=nat_ages,
            x=-nat_m,
            mode="lines",
            name="Kenya",
            line=dict(color=INK, width=1.35, dash="dot"),
            hovertemplate="Kenya %{y} male: %{customdata:.2f}%<extra></extra>",
            customdata=nat_m,
        )
        fig.add_scatter(
            y=nat_ages,
            x=nat_f,
            mode="lines",
            name="Kenya",
            line=dict(color=INK, width=1.35, dash="dot"),
            showlegend=False,
            hovertemplate="Kenya %{y} female: %{customdata:.2f}%<extra></extra>",
            customdata=nat_f,
        )
    span = max(8.0, float(max(males.max(), females.max())) * 1.12)
    ticks = [-8, -4, 0, 4, 8] if span <= 10 else [-12, -6, 0, 6, 12]
    fig.update_layout(barmode="relative", bargap=0.12)
    fig.update_xaxes(
        range=[-span, span],
        tickvals=ticks,
        ticktext=[str(abs(t)) for t in ticks],
        title=dict(text="Share of population (%)", font=dict(size=11, color=MUTED)),
        gridcolor=LINE,
        zeroline=True,
        zerolinecolor=INK,
        zerolinewidth=0.6,
    )
    fig.update_yaxes(title=None, automargin=True)
    return _layout(fig, 430)


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
