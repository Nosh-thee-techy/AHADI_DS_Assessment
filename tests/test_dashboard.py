"""Dashboard helpers that do not need Streamlit running."""

import unittest

import pandas as pd

from dashboard.components.prepare import (
    pad_age_codes,
    indicators_for,
    national_row,
    ordinal,
    county_rank,
    export_bytes,
)


class AgeCodePaddingTests(unittest.TestCase):
    def test_integer_codes_become_worldpop_strings(self):
        frame = pd.DataFrame({"age_code": [0, 1, 5, 90]})
        padded = pad_age_codes(frame)
        self.assertEqual(padded["age_code"].tolist(), ["00", "01", "05", "90"])


class IndicatorTests(unittest.TestCase):
    def setUp(self):
        self.counties = pd.DataFrame(
            {
                "county": ["HomaBay", "Nairobi"],
                "year": [2025, 2025],
                "total_population": [1000.0, 4000.0],
                "children_under_5": [200.0, 400.0],
                "working_age": [600.0, 2800.0],
                "elderly_65plus": [50.0, 80.0],
                "sex_ratio": [98.0, 101.0],
                "dependency_ratio": [41.7, 17.1],
                "child_dependency_ratio": [33.3, 14.3],
                "elderly_dependency_ratio": [8.3, 2.9],
                "pct_children": [20.0, 10.0],
                "pct_elderly": [5.0, 2.0],
            }
        )
        rows = []
        for county, total, child in [("HomaBay", 800, 160), ("Nairobi", 3500, 350)]:
            for year in (2021, 2025):
                scale = 1.0 if year == 2021 else 1.25
                rows.append(
                    {
                        "county": county,
                        "year": year,
                        "sex": "female",
                        "age_code": 0,
                        "age_group": "0-1",
                        "population": child * 0.4 * scale / 2,
                    }
                )
                rows.append(
                    {
                        "county": county,
                        "year": year,
                        "sex": "male",
                        "age_code": 1,
                        "age_group": "1-4",
                        "population": child * 0.6 * scale / 2,
                    }
                )
                rows.append(
                    {
                        "county": county,
                        "year": year,
                        "sex": "female",
                        "age_code": 15,
                        "age_group": "15-19",
                        "population": total * 0.3 * scale / 2,
                    }
                )
                rows.append(
                    {
                        "county": county,
                        "year": year,
                        "sex": "male",
                        "age_code": 65,
                        "age_group": "65-69",
                        "population": total * 0.05 * scale / 2,
                    }
                )
        self.age_sex = pd.DataFrame(rows)
        self.areas = {"HomaBay": 50.0, "Nairobi": 10.0}

    def test_child_density_uses_gadm_area(self):
        frame = indicators_for(self.counties, self.age_sex, 2025, "Total", self.areas)
        nairobi = frame.loc[frame["county"] == "Nairobi"].iloc[0]
        self.assertAlmostEqual(nairobi["child_density"], 40.0)
        self.assertEqual(nairobi["county_label"], "Nairobi")

    def test_homabay_display_name_splits(self):
        frame = indicators_for(self.counties, self.age_sex, 2025, "Total", self.areas)
        label = frame.loc[frame["county"] == "HomaBay", "county_label"].iloc[0]
        self.assertEqual(label, "Homa Bay")

    def test_growth_is_against_2021(self):
        frame = indicators_for(self.counties, self.age_sex, 2025, "Total", self.areas)
        self.assertTrue((frame["growth_pct"] > 0).all())

    def test_national_density_is_total_children_over_total_area(self):
        frame = indicators_for(self.counties, self.age_sex, 2025, "Total", self.areas)
        national = national_row(frame)
        expected = frame["children_under_5"].sum() / frame["area_km2"].sum()
        self.assertAlmostEqual(national["child_density"], expected)

    def test_export_keeps_gadm_and_display_names(self):
        frame = indicators_for(self.counties, self.age_sex, 2025, "Total", self.areas)
        text = export_bytes(frame, 2025, "Total").decode("utf-8")
        self.assertIn("gadm_name", text)
        self.assertIn("HomaBay", text)
        self.assertIn("Homa Bay", text)


class RankTests(unittest.TestCase):
    def test_ordinal_and_rank(self):
        self.assertEqual(ordinal(1), "1st")
        self.assertEqual(ordinal(2), "2nd")
        self.assertEqual(ordinal(3), "3rd")
        self.assertEqual(ordinal(11), "11th")
        frame = pd.DataFrame({"county": ["A", "B", "C"], "child_density": [10.0, 40.0, 20.0]})
        rank, n = county_rank(frame, "B", "child_density")
        self.assertEqual((rank, n), (1, 3))


class FaultCopyTests(unittest.TestCase):
    def test_widget_error_is_not_a_traceback(self):
        from dashboard.components.narrative import fault_copy

        class StreamlitWidgetAlreadyInstantiatedError(Exception):
            pass

        headline, advice = fault_copy(
            StreamlitWidgetAlreadyInstantiatedError("st.session_state.focus_county cannot be modified after the widget")
        )
        self.assertIn("dropdown", headline.lower())
        self.assertNotIn("Traceback", headline)
        self.assertIn("Refresh", advice)

    def test_missing_file_tells_you_to_run_the_pipeline(self):
        from dashboard.components.narrative import fault_copy

        headline, advice = fault_copy(FileNotFoundError("kenya_population_by_county.csv"))
        self.assertIn("pretending", headline.lower())
        self.assertIn("pipeline", advice)


class ExtremesTests(unittest.TestCase):
    def test_namedtuple_rows_format(self):
        from dashboard.components.charts import extremes_rows

        frame = pd.DataFrame(
            {
                "county_label": ["Nairobi", "Mandera", "Garissa"],
                "child_density": [900.0, 7.0, 1.2],
            }
        )
        high, low = extremes_rows(frame, "child_density", n=2)
        self.assertEqual(high[0][0], "Nairobi")
        self.assertEqual(low[0][0], "Garissa")


if __name__ == "__main__":
    unittest.main()
