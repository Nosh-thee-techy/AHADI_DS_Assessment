"""Checks that do not need rasters on disk."""

import unittest

from src.config import CHILD_AGES, ELDERLY_AGES, EXPECTED_COUNTY_COUNT, WORKING_AGES, expected_raster_jobs


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
