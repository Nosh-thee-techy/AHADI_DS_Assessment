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
    INDICATORS,
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


class BriefCoverageTests(unittest.TestCase):
    def test_map_dropdown_has_the_brief_metrics(self):
        required = {
            "total_population",
            "children_under_5",
            "elderly_65plus",
            "dependency_ratio",
            "sex_ratio",
            "child_dependency_ratio",
            "elderly_dependency_ratio",
        }
        self.assertTrue(required.issubset(set(INDICATORS.values())))

    def test_map_hover_lists_the_key_indicators(self):
        from dashboard.components.charts import choropleth
        from dashboard.components.i18n import set_lang

        set_lang("en")
        frame = pd.DataFrame(
            {
                "county": ["Nairobi"],
                "county_label": ["Nairobi"],
                "child_density": [40.0],
                "total_population": [4000.0],
                "children_under_5": [400.0],
                "pct_children": [10.0],
                "elderly_65plus": [80.0],
                "pct_elderly": [2.0],
                "dependency_ratio": [17.1],
                "child_dependency_ratio": [14.3],
                "elderly_dependency_ratio": [2.8],
                "sex_ratio": [101.0],
            }
        )
        geojson = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"county": "Nairobi"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[36.7, -1.4], [37.0, -1.4], [37.0, -1.2], [36.7, -1.2], [36.7, -1.4]]],
                    },
                }
            ],
        }
        fig = choropleth(frame, geojson, "child_density", "Children per km²", "Age mix")
        hover = fig.data[0].hovertemplate
        self.assertIn("People", hover)
        self.assertIn("Under 5", hover)
        self.assertIn("Aged 65+", hover)
        self.assertIn("Dependency", hover)
        self.assertIn("Sex ratio", hover)
        self.assertIn("400", fig.data[0].customdata[0][3])
        self.assertGreaterEqual(fig.layout.height, 800)
        self.assertEqual(fig.layout.geo.projection.type, "mercator")

    def test_interpretation_names_clinics_and_two_reads(self):
        from dashboard.components.i18n import set_lang
        from dashboard.components.narrative import interpretation_cards

        set_lang("en")
        frame = pd.DataFrame(
            {
                "county": ["Nairobi", "HomaBay"],
                "county_label": ["Nairobi", "Homa Bay"],
                "pct_children": [10.0, 20.0],
                "pct_elderly": [2.0, 5.0],
                "children_under_5": [400.0, 200.0],
                "elderly_65plus": [80.0, 50.0],
                "child_dependency_ratio": [14.3, 33.3],
                "child_density": [40.0, 4.0],
            }
        )
        national = pd.Series(
            {
                "pct_children": 12.0,
                "pct_elderly": 3.0,
                "children_under_5": 600.0,
                "elderly_65plus": 130.0,
                "child_dependency_ratio": 18.0,
            }
        )
        young = interpretation_cards(frame.iloc[1], national, "Homa Bay", frame)
        blob = " ".join(" ".join(part for part in card) for card in young)
        self.assertEqual(len(young), 3)
        self.assertIn("immunization", blob)
        self.assertIn("different clinics", blob)
        self.assertNotIn("IMNCI", blob)
        self.assertNotIn("NCD", blob)
        close = interpretation_cards(frame.iloc[0], national, "Nairobi", frame)
        close_blob = " ".join(" ".join(part for part in card) for card in close)
        self.assertIn("headcount still matters", close_blob)


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


class FilterEffectTests(unittest.TestCase):
    def setUp(self):
        self.counties = pd.DataFrame(
            {
                "county": ["Nairobi", "Nairobi"],
                "year": [2021, 2025],
                "total_population": [3000.0, 4000.0],
                "children_under_5": [300.0, 400.0],
                "working_age": [2100.0, 2800.0],
                "elderly_65plus": [60.0, 80.0],
                "sex_ratio": [101.0, 101.0],
                "dependency_ratio": [17.1, 17.1],
                "child_dependency_ratio": [14.3, 14.3],
                "elderly_dependency_ratio": [2.9, 2.9],
                "pct_children": [10.0, 10.0],
                "pct_elderly": [2.0, 2.0],
            }
        )
        rows = []
        for year, scale in ((2021, 1.0), (2025, 1.25)):
            for sex, share in (("female", 0.52), ("male", 0.48)):
                rows.extend(
                    [
                        {
                            "county": "Nairobi",
                            "year": year,
                            "sex": sex,
                            "age_code": 0,
                            "age_group": "0-1",
                            "population": 200 * scale * share,
                        },
                        {
                            "county": "Nairobi",
                            "year": year,
                            "sex": sex,
                            "age_code": 15,
                            "age_group": "15-19",
                            "population": 1500 * scale * share,
                        },
                    ]
                )
        self.age_sex = pd.DataFrame(rows)
        self.areas = {"Nairobi": 10.0}

    def test_year_and_sex_change_the_totals(self):
        total_2025 = indicators_for(self.counties, self.age_sex, 2025, "Total", self.areas)
        total_2021 = indicators_for(self.counties, self.age_sex, 2021, "Total", self.areas)
        male_2025 = indicators_for(self.counties, self.age_sex, 2025, "Male", self.areas)
        self.assertGreater(total_2025["total_population"].sum(), total_2021["total_population"].sum())
        self.assertLess(male_2025["total_population"].sum(), total_2025["total_population"].sum())

    def test_reading_has_no_clinic_acronyms(self):
        from dashboard.components.narrative import county_briefing, kenya_briefing, table_analytics

        frame = indicators_for(self.counties, self.age_sex, 2025, "Total", self.areas)
        national = national_row(frame)
        cards = county_briefing(frame.iloc[0], national, "child_density", "Children per km²")
        blob = " ".join(body for _, body in cards + kenya_briefing(frame, 2025, "child_density", "Children per km²"))
        self.assertNotIn("IMNCI", blob)
        self.assertNotIn("NCD", blob)
        self.assertNotIn("choropleth", blob)
        self.assertGreaterEqual(len(cards), 2)
        analysis = table_analytics(frame, national, "child_density", "Children per km²")
        blob2 = " ".join(" ".join(part for part in card) for card in analysis)
        self.assertIn("Nairobi", blob2)
        self.assertNotIn("IMNCI", blob2)
        self.assertEqual(analysis[0][0], "Highest on the table")
        self.assertEqual(len(analysis[0]), 4)


class TableHtmlTests(unittest.TestCase):
    def test_kenya_row_and_pinned_county(self):
        from dashboard.components.narrative import county_table_html

        frame = pd.DataFrame(
            {
                "county": ["Nairobi", "HomaBay"],
                "county_label": ["Nairobi", "Homa Bay"],
                "child_density": [40.0, 4.0],
                "total_population": [4000.0, 1000.0],
                "pct_children": [10.0, 20.0],
                "pct_elderly": [2.0, 5.0],
                "child_dependency_ratio": [14.3, 33.3],
            }
        )
        national = pd.Series(
            {
                "child_density": 22.0,
                "total_population": 5000.0,
                "pct_children": 12.0,
                "pct_elderly": 2.6,
                "child_dependency_ratio": 18.0,
            }
        )
        markup = county_table_html(frame, "child_density", "Children per km²", "Nairobi", national)
        self.assertIn("is-kenya", markup)
        self.assertIn("is-pinned", markup)
        self.assertIn("Homa Bay", markup)
        self.assertIn("Kenya", markup)


class LanguageTests(unittest.TestCase):
    def test_kiswahili_keeps_the_numbers(self):
        from dashboard.components.i18n import set_lang, t
        from dashboard.components.narrative import how_to_html, who_lives_here_html

        set_lang("sw")
        self.addCleanup(lambda: set_lang("en"))
        self.assertIn("kaunti", t("title"))
        how = how_to_html()
        self.assertIn("piramidi", how)
        self.assertIn("kijani", how)
        row = pd.Series(
            {
                "county_label": "Nairobi",
                "total_population": 4000.0,
                "children_under_5": 400.0,
                "elderly_65plus": 80.0,
                "pct_children": 15.7,
                "pct_elderly": 2.0,
                "child_dependency_ratio": 14.3,
            }
        )
        national = pd.Series(
            {
                "total_population": 50000.0,
                "pct_children": 12.6,
                "pct_elderly": 3.4,
                "child_dependency_ratio": 18.0,
                "children_under_5": 6300.0,
                "elderly_65plus": 1700.0,
            }
        )
        takes = who_lives_here_html(row, national, "Nairobi", "Kenya")
        self.assertIn("15.7%", takes)
        self.assertIn("Nani anaishi hapa", takes)

    def test_how_to_puts_pyramid_under_the_map(self):
        from dashboard.components.i18n import set_lang
        from dashboard.components.narrative import how_to_html

        set_lang("en")
        how = how_to_html()
        self.assertIn("under the map", how)
        self.assertIn("green bar", how)
        self.assertIn("Filters", how)


class ChromeTests(unittest.TestCase):
    def test_header_and_footer_name_the_briefing(self):
        from dashboard.components.i18n import set_lang
        from dashboard.components.narrative import site_footer_html, site_header_html

        set_lang("en")
        head = site_header_html()
        foot = site_footer_html()
        self.assertIn("role='banner'", head)
        self.assertIn("Ministry of Health", head)
        self.assertIn("County age structure", head)
        self.assertIn("Planning brief", head)
        self.assertIn("role='contentinfo'", foot)
        self.assertIn("WorldPop", foot)
        self.assertIn("not the census", foot)
        self.assertIn("GADM", foot)

    def test_kiswahili_header_keeps_the_ministry(self):
        from dashboard.components.i18n import set_lang
        from dashboard.components.narrative import site_footer_html, site_header_html

        set_lang("sw")
        self.addCleanup(lambda: set_lang("en"))
        head = site_header_html()
        foot = site_footer_html()
        self.assertIn("Wizara ya Afya", head)
        self.assertIn("Muundo wa umri", head)
        self.assertIn("Chanzo", foot)
        self.assertIn("si sensa", foot)


class PlaceReadingTests(unittest.TestCase):
    def test_who_lives_here_is_numbers_not_a_paragraph(self):
        from dashboard.components.narrative import place_metrics_html, who_lives_here_html

        row = pd.Series(
            {
                "county_label": "Nairobi",
                "total_population": 4000.0,
                "children_under_5": 400.0,
                "elderly_65plus": 80.0,
                "pct_children": 15.7,
                "pct_elderly": 2.0,
                "child_dependency_ratio": 14.3,
            }
        )
        national = pd.Series(
            {
                "total_population": 50000.0,
                "children_under_5": 6300.0,
                "elderly_65plus": 1700.0,
                "pct_children": 12.6,
                "pct_elderly": 3.4,
                "child_dependency_ratio": 18.0,
            }
        )
        takes = who_lives_here_html(row, national, "Nairobi", "Kenya")
        self.assertIn("15.7%", takes)
        self.assertIn("12.6%", takes)
        self.assertIn("Who lives here", takes)
        self.assertNotIn("IMNCI", takes)
        self.assertNotIn("NCD", takes)
        metrics = place_metrics_html(row, national, "Nairobi", "Kenya")
        self.assertIn("15.7%", metrics)
        self.assertIn("Kenya 12.6%", metrics)
        self.assertIn("+3.1 pp vs Kenya", metrics)


class PyramidTests(unittest.TestCase):
    def test_hover_has_count_and_share(self):
        from dashboard.components.charts import age_pyramid

        frame = pd.DataFrame(
            {
                "age_group": ["0-1", "0-1", "15-19", "15-19"],
                "age_code": ["00", "00", "15", "15"],
                "sex": ["male", "female", "male", "female"],
                "population": [40.0, 38.0, 120.0, 110.0],
            }
        )
        overlay = frame.copy()
        overlay["population"] = overlay["population"] * 2
        fig = age_pyramid(frame, overlay, "Nairobi", "Kenya", "Total", "Age mix", "share")
        self.assertIn("people", fig.data[0].hovertemplate)
        self.assertIn("% of this place", fig.data[0].hovertemplate)
        self.assertGreaterEqual(fig.layout.height, 650)
        self.assertEqual(fig.data[0].marker.color, "#1e4d7b")
        self.assertEqual(fig.data[1].marker.color, "#9c3412")
        self.assertTrue(any(trace.name == "Kenya" for trace in fig.data))
        self.assertEqual(fig.layout.title.yref, "container")
        self.assertEqual(fig.layout.legend.yref, "container")
        self.assertGreater(fig.layout.title.y, fig.layout.legend.y)
        self.assertGreaterEqual(fig.layout.margin.t, 100)
        counted = age_pyramid(frame, overlay, "Nairobi", "Kenya", "Total", "Age mix", "count")
        self.assertEqual(counted.layout.xaxis.title.text, "People")


class InspectorTests(unittest.TestCase):
    def test_empty_card_asks_for_a_click(self):
        from dashboard.components.narrative import inspector_html

        empty = inspector_html(None, "child_density", "Children per km²", 2025, "")
        self.assertIn("Click the map", empty)
        self.assertNotIn("Child dependency", empty)


if __name__ == "__main__":
    unittest.main()
