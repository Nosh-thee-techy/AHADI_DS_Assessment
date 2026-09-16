"""Static figures required by the brief: raster map, national timeseries, under-5 vs area."""

from __future__ import annotations

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.plot import show

from src.config import COUNTY_CSV, COUNTY_GEOJSON, FIGURES, worldpop_path
from src.utils import setup_logging, tidy_county_name
from src.validation import clean_display_geometry, load_counties

logger = setup_logging()


def plot_raster_map_2025() -> None:
    """2025 female age 0-1 (WorldPop 00) — the infant cohort for immunization planning."""
    path = worldpop_path(2025, "f", "00")
    counties = load_counties()
    counties = counties.copy()
    counties["geometry"] = counties.geometry.map(clean_display_geometry)
    with rasterio.open(path) as src:
        data = src.read(1).astype("float64")
        nodata = src.nodata
        if nodata is not None:
            data = np.ma.masked_equal(data, nodata)
        data = np.ma.masked_where(data < 0, data)
        fig, ax = plt.subplots(figsize=(8, 10))
        show(data, transform=src.transform, ax=ax, cmap="YlOrRd")
        # Plot polygon edges, not .boundary — holes/simplify artifacts show up as spikes.
        counties.to_crs(src.crs).plot(ax=ax, facecolor="none", edgecolor="#1b1b1b", linewidth=0.4)
        ax.set_title("Kenya, 2025: female population aged 0–12 months (1 km)")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        fig.tight_layout()
        out = FIGURES / "kenya_2025_female_age00_raster.png"
        fig.savefig(out, dpi=150)
        plt.close(fig)
        logger.info("Wrote %s", out)


def plot_national_timeseries() -> None:
    df = pd.read_csv(COUNTY_CSV)
    yearly = df.groupby("year", as_index=False)["total_population"].sum()
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(yearly["year"], yearly["total_population"] / 1_000_000, marker="o", color="#0f4c5c")
    ax.set_title("Kenya total population, 2021–2025 (sum of 47 counties)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Population (millions)")
    ax.set_xticks(yearly["year"])
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    out = FIGURES / "kenya_total_population_timeseries.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    logger.info("Wrote %s", out)


def plot_under5_vs_area() -> None:
    df = pd.read_csv(COUNTY_CSV)
    counties = gpd.read_file(COUNTY_GEOJSON)
    latest = df.loc[df["year"] == df["year"].max()].merge(
        counties[["county", "area_km2"]], on="county", how="left"
    )
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.scatter(latest["area_km2"], latest["children_under_5"] / 1000, alpha=0.8, c="#c44536")
    for _, row in latest.nlargest(5, "children_under_5").iterrows():
        ax.annotate(
            tidy_county_name(row["county"]),
            (row["area_km2"], row["children_under_5"] / 1000),
            fontsize=8,
        )
    ax.set_title(f"Children under 5 vs county area ({int(latest['year'].iloc[0])})")
    ax.set_xlabel("County area (km², equal-area approximation)")
    ax.set_ylabel("Children under 5 (thousands)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    out = FIGURES / "children_under5_vs_county_area.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    logger.info("Wrote %s", out)


def write_figures() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    plot_raster_map_2025()
    plot_national_timeseries()
    plot_under5_vs_area()
