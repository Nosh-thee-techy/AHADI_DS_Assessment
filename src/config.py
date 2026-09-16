"""Paths, WorldPop URL contract, and demographic age groupings."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
WORLDPOP_DIR = DATA_RAW / "worldpop"
GADM_DIR = DATA_RAW / "gadm"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
FIGURES = OUTPUTS / "figures"
LOG_PATH = DATA_PROCESSED / "validation_log.txt"

COUNTY_CSV = DATA_PROCESSED / "kenya_population_by_county.csv"
AGE_SEX_CSV = DATA_PROCESSED / "kenya_population_age_sex.csv"
COUNTY_GEOJSON = DATA_PROCESSED / "kenya_counties_simplified.geojson"

YEARS = (2021, 2022, 2023, 2024, 2025)
SEXES = ("f", "m")  # skip WorldPop "t" totals; we sum male + female
AGE_CODES = (
    "00",
    "01",
    "05",
    "10",
    "15",
    "20",
    "25",
    "30",
    "35",
    "40",
    "45",
    "50",
    "55",
    "60",
    "65",
    "70",
    "75",
    "80",
    "85",
    "90",
)

# WorldPop R2025A splits under-5 into 0-12 months (00) and 1-4 years (01).
CHILD_AGES = ("00", "01")
WORKING_AGES = ("15", "20", "25", "30", "35", "40", "45", "50", "55", "60")
ELDERLY_AGES = ("65", "70", "75", "80", "85", "90")

WORLDPOP_FILENAME = "ken_{sex}_{age}_{year}_CN_1km_R2025A_UA_v1.tif"
WORLDPOP_URL = (
    "https://worldpop-public-data.soton.ac.uk/GIS/AgeSex_structures/"
    "Global_2015_2030/R2025A/{year}/KEN/v1/1km_ua/constrained/{filename}"
)

# Brief links Level 2, but Kenya counties are GADM Level 1 (47 units).
GADM_L1_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_KEN_1.json.zip"
GADM_L2_URL = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_KEN_2.json.zip"

EXPECTED_COUNTY_COUNT = 47
TARGET_CRS = "EPSG:4326"

DOWNLOAD_TIMEOUT_S = 120
DOWNLOAD_WORKERS = 8
DOWNLOAD_RETRIES = 3


def worldpop_filename(year: int, sex: str, age: str) -> str:
    return WORLDPOP_FILENAME.format(sex=sex, age=age, year=year)


def worldpop_url(year: int, sex: str, age: str) -> str:
    filename = worldpop_filename(year, sex, age)
    return WORLDPOP_URL.format(year=year, filename=filename)


def worldpop_path(year: int, sex: str, age: str) -> Path:
    return WORLDPOP_DIR / str(year) / worldpop_filename(year, sex, age)


def expected_raster_jobs() -> list[tuple[int, str, str]]:
    return [(year, sex, age) for year in YEARS for sex in SEXES for age in AGE_CODES]
