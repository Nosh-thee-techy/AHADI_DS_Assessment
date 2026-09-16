"""Checks that do not need rasters on disk."""

import unittest

from src.config import CHILD_AGES, ELDERLY_AGES, EXPECTED_COUNTY_COUNT, WORKING_AGES, expected_raster_jobs
from src.utils import tidy_county_name


class ValidationRulesTests(unittest.TestCase):
    def test_under_five_is_two_worldpop_codes(self):
        self.assertEqual(CHILD_AGES, ("00", "01"))

    def test_working_age_excludes_10_14_and_65(self):
        self.assertNotIn("10", WORKING_AGES)
        self.assertNotIn("65", WORKING_AGES)
        self.assertEqual(WORKING_AGES[0], "15")
        self.assertEqual(WORKING_AGES[-1], "60")

    def test_elderly_starts_at_65(self):
        self.assertEqual(ELDERLY_AGES[0], "65")
        self.assertIn("90", ELDERLY_AGES)

    def test_expected_raster_count_is_five_years_two_sexes_twenty_ages(self):
        jobs = expected_raster_jobs()
        self.assertEqual(len(jobs), 200)
        self.assertEqual(EXPECTED_COUNTY_COUNT, 47)
        self.assertTrue(all(sex in {"f", "m"} for _, sex, _ in jobs))

    def test_display_cleanup_drops_thin_sliver_parts(self):
        from shapely.geometry import MultiPolygon, Polygon

        from src.validation import clean_display_geometry

        main = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        sliver = Polygon([(1, 0.5), (8, 0.49), (8, 0.51)])
        cleaned = clean_display_geometry(MultiPolygon([main, sliver]))
        self.assertGreater(cleaned.area, 0.9)
        self.assertLess(cleaned.bounds[2], 2)

    def test_display_cleanup_drops_sharp_digitizing_spike(self):
        from shapely.geometry import Polygon

        from src.validation import clean_display_geometry

        # Square with a long sharp triangle on the left, like GADM Embu.
        spiked = Polygon(
            [(0, 0), (1, 0), (1, 1), (0, 1), (0, 0.51), (-2, 0.5), (0, 0.49)]
        )
        cleaned = clean_display_geometry(spiked)
        self.assertGreater(cleaned.bounds[0], -0.5)

    def test_gadm_camelcase_becomes_official_county_name(self):
        self.assertEqual(tidy_county_name("HomaBay"), "Homa Bay")
        self.assertEqual(tidy_county_name("WestPokot"), "West Pokot")
        self.assertEqual(tidy_county_name("TaitaTaveta"), "Taita Taveta")
        self.assertEqual(tidy_county_name("TanaRiver"), "Tana River")
        self.assertEqual(tidy_county_name("TransNzoia"), "Trans Nzoia")
        self.assertEqual(tidy_county_name("UasinGishu"), "Uasin Gishu")
        self.assertEqual(tidy_county_name("Elgeyo-Marakwet"), "Elgeyo-Marakwet")
        self.assertEqual(tidy_county_name("Murang'a"), "Murang'a")
        self.assertEqual(tidy_county_name("Nairobi"), "Nairobi")
