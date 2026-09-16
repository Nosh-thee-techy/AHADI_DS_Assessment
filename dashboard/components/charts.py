"""Plotly charts for the Streamlit dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

COUNT_INDICATORS = {
    "Total Population": "total_population",
    "Children under 5": "children_under_5",
    "Elderly 65+": "elderly_65plus",
}
RATIO_INDICATORS = {
    "Dependency Ratio": "dependency_ratio",
    "Sex Ratio": "sex_ratio",
    "Child Dependency Ratio": "child_dependency_ratio",
    "Elderly Dependency Ratio": "elderly_dependency_ratio",
}
INDICATORS = {**COUNT_INDICATORS, **RATIO_INDICATORS}

SEQUENTIAL = "YlOrRd"
DIVERGING = "RdBu"


def _color_scale(column: str) -> str:
    return DIVERGING if column == "sex_ratio" else SEQUENTIAL


def choropleth(frame: pd.DataFrame, geojson: dict, column: str, title: str) -> go.Figure:
    choropleth_kwargs = {
        "geojson": geojson,
        "locations": frame["county"],
        "z": frame[column],
        "featureidkey": "properties.county",
        "colorscale": _color_scale(column),
        "marker_line_width": 0.4,
        "marker_line_color": "#333333",
        "colorbar_title": title,
        "customdata": frame[
            [
                "county_label" if "county_label" in frame.columns else "county",
                "total_population",
                "children_under_5",
                "elderly_65plus",
                "dependency_ratio",
                "sex_ratio",
                "pct_children",
                "pct_elderly",
            ]
        ].to_numpy(),
        "hovertemplate": (
            "<b>%{customdata[0]}</b><br>"
            "Total: %{customdata[1]:,.0f}<br>"
            "Under 5: %{customdata[2]:,.0f} (%{customdata[6]:.1f}%)<br>"
            "Elderly 65+: %{customdata[3]:,.0f} (%{customdata[7]:.1f}%)<br>"
            "Dependency ratio: %{customdata[4]:.1f}<br>"
            "Sex ratio: %{customdata[5]:.1f}<extra></extra>"
        ),
    }
    if column == "sex_ratio":
        choropleth_kwargs["zmid"] = 100
    fig = go.Figure(go.Choropleth(**choropleth_kwargs))
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        margin={"r": 0, "t": 40, "l": 0, "b": 0},
        height=560,
        title=title,
        paper_bgcolor="rgba(0,0,0,0)",
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )
    return fig


def age_pyramid(age_sex: pd.DataFrame, title: str) -> go.Figure:
    grouped = (
        age_sex.groupby(["age_group", "age_code", "sex"], as_index=False)["population"]
        .sum()
        .sort_values("age_code")
    )
    ages = grouped["age_group"].drop_duplicates().tolist()
    males = grouped.loc[grouped["sex"] == "male"].set_index("age_group")["population"].reindex(ages).fillna(0)
    females = grouped.loc[grouped["sex"] == "female"].set_index("age_group")["population"].reindex(ages).fillna(0)
    fig = go.Figure()
    fig.add_bar(y=ages, x=-males, orientation="h", name="Male", marker_color="#1f4e79")
    fig.add_bar(y=ages, x=females, orientation="h", name="Female", marker_color="#c44536")
    fig.update_layout(
        barmode="relative",
        title=title,
        xaxis_title="Population (males left, females right)",
        yaxis_title="Age group",
        height=520,
        margin={"t": 40, "l": 70, "r": 20, "b": 40},
        legend={"orientation": "h", "y": 1.02},
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(tickformat=",")
    return fig


def comparison_bars(frame: pd.DataFrame, column: str, title: str) -> go.Figure:
    ordered = frame.sort_values(column, ascending=True)
    y_col = "county_label" if "county_label" in ordered.columns else "county"
    fig = go.Figure(
        go.Bar(
            y=ordered[y_col],
            x=ordered[column],
            orientation="h",
            marker_color="#0f4c5c",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=title,
        yaxis_title="",
        height=max(280, 28 * len(ordered)),
        margin={"t": 40, "l": 110, "r": 20, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def load_geojson(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
