import importlib.util
import unittest
from datetime import date, datetime
from pathlib import Path

SCRIPT_PATH = Path(__file__).parents[1] / "scripts" / "backfill_draws.py"
spec = importlib.util.spec_from_file_location("backfill_draws", SCRIPT_PATH)
backfill_draws = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backfill_draws)


class BackfillTests(unittest.TestCase):
    def test_candidates_include_existing_and_nominal_dates(self):
        dates = backfill_draws.candidate_dates(["2007-01-17"], date(2007, 2, 20))
        self.assertIn(date(2007, 1, 17), dates)   # shifted draw kept
        self.assertIn(date(2007, 1, 16), dates)   # nominal date still tried
        self.assertIn(date(2007, 2, 1), dates)
        self.assertNotIn(date(2006, 11, 16), dates)
        self.assertEqual(dates, sorted(set(dates)))

    def test_compare_buckets(self):
        existing = {"2020-01-01": "10", "2020-01-16": "20", "2020-02-01": "30"}
        official = {"2020-01-01": "10", "2020-01-16": "21", "2020-03-01": "40"}
        report = backfill_draws.compare(existing, official)
        self.assertEqual(report["matched"], ["2020-01-01"])
        self.assertEqual(report["mismatched"], [("2020-01-16", "20", "21")])
        self.assertEqual(report["missing_from_glo"], ["2020-02-01"])
        self.assertEqual(report["new_from_glo"], [("2020-03-01", "40")])

    def test_retry_then_success(self):
        calls = []

        def flaky(_d):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("boom")
            return "07"

        value = backfill_draws.fetch_with_retry(datetime(2020, 1, 1), fetch=flaky, sleep=lambda _s: None)
        self.assertEqual(value, "07")

    def test_retry_gives_up(self):
        def broken(_d):
            raise RuntimeError("down")

        with self.assertRaises(RuntimeError):
            backfill_draws.fetch_with_retry(datetime(2020, 1, 1), fetch=broken, sleep=lambda _s: None)


if __name__ == "__main__":
    unittest.main()
