"""Unit tests for the on-the-fly price/multiple math in scripts/collect.py.

No network: a synthetic monthly series is injected into the module's price
store. Run with:  .venv/bin/python -m unittest tests.test_prices
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import collect  # noqa: E402


class PriceMathTests(unittest.TestCase):
    def setUp(self):
        # 60 monthly closes, 2010-01 .. 2014-12, a steady 1% monthly climb.
        closes = [round(100 * (1.01 ** i), 4) for i in range(60)]
        collect._prices = {
            "STEADY": {"start": "2010-01", "closes": closes},
            "GAP": {"start": "2010-01", "closes": [None, None] + closes[2:]},
            "DEAD": None,
        }
        self._closes = closes

    def test_price_at_directions(self):
        self.assertEqual(collect.price_at("STEADY", "2010-01", "after"), self._closes[0])
        self.assertEqual(collect.price_at("STEADY", "2014-12", "before"), self._closes[-1])

    def test_multiple_matches_endpoint_ratio(self):
        expected = round(self._closes[-1] / self._closes[0], 2)
        self.assertEqual(collect.multiple("STEADY", "2010-2014"), expected)
        self.assertEqual(collect.multiple("STEADY", start="2010-01", end="2014-12"), expected)

    def test_gap_skips_to_first_available(self):
        # 'after' from 2010-01 must skip the two leading None months.
        self.assertEqual(collect.price_at("GAP", "2010-01", "after"), self._closes[2])

    def test_out_of_window_is_none(self):
        # A window entirely before the series → no data.
        self.assertIsNone(collect.multiple("STEADY", "2000-2004"))

    def test_missing_and_dead_tickers(self):
        self.assertIsNone(collect.price_at("NOPE", "2010-01"))
        self.assertIsNone(collect.price_at("DEAD", "2010-01"))

    def test_era_bounds_parsing(self):
        self.assertEqual(collect._era_bounds("2010-2014"), ("2010-01", "2014-12"))


if __name__ == "__main__":
    unittest.main()
