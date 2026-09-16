"""Indicator arithmetic on a tiny synthetic table."""

import unittest

import pandas as pd

from src.aggregation import build_county_indicators


class AggregationIndicatorTests(unittest.TestCase):
    def test_indicators_from_known_counts(self):
        age_sex = pd.DataFrame(
            [
                {"county": "Nairobi", "year": 2025, "sex": "female", "age_code": "00", "age_group": "0-1", "population": 100},
                {"county": "Nairobi", "year": 2025, "sex": "male", "age_code": "01", "age_group": "1-4", "population": 150},
                {"county": "Nairobi", "year": 2025, "sex": "female", "age_code": "15", "age_group": "15-19", "population": 400},
                {"county": "Nairobi", "year": 2025, "sex": "male", "age_code": "20", "age_group": "20-24", "population": 600},
                {"county": "Nairobi", "year": 2025, "sex": "female", "age_code": "65", "age_group": "65-69", "population": 50},
                {"county": "Nairobi", "year": 2025, "sex": "male", "age_code": "70", "age_group": "70-74", "population": 30},
                {"county": "Nairobi", "year": 2025, "sex": "female", "age_code": "10", "age_group": "10-14", "population": 70},
            ]
        )
        counties = pd.DataFrame({"county": ["Nairobi"], "area_km2": [700.0]})
        out = build_county_indicators(age_sex, counties).iloc[0]
        self.assertEqual(out["children_under_5"], 250)
        self.assertEqual(out["working_age"], 1000)
        self.assertEqual(out["elderly_65plus"], 80)
        self.assertEqual(out["total_population"], 1400)
        self.assertAlmostEqual(
            out["sex_ratio"],
            (150 + 600 + 30) / (100 + 400 + 50 + 70) * 100,
        )
        self.assertAlmostEqual(out["dependency_ratio"], 33.0)
        self.assertAlmostEqual(out["pct_children"], 250 / 1400 * 100)
