"""Structural sanity checks on the committed app/fundamentals.json (no network).

Run: .venv/bin/python -m unittest tests.test_fundamentals
"""

import json
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUND = os.path.join(ROOT, "app", "fundamentals.json")


class FundamentalsShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(FUND, encoding="utf-8") as f:
            cls.data = json.load(f)

    def test_metrics_are_sane_and_optional(self):
        for ticker, eras in self.data.items():
            for era, m in eras.items():
                # price is always present and positive
                self.assertIn("price", m, f"{ticker} {era} missing price")
                self.assertGreater(m["price"], 0)
                # pe / divYield are optional but, when present, sane
                if "pe" in m:
                    self.assertGreater(m["pe"], 0)
                    self.assertLess(m["pe"], 100000)
                if "divYield" in m:
                    self.assertGreaterEqual(m["divYield"], 0)
                    self.assertLess(m["divYield"], 50)  # % — no company yields 50%+

    def test_pe_only_on_recent_eras(self):
        # EDGAR EPS starts ~2009, so no P/E should exist before the 2010 era.
        old = {"1990-1994", "1995-1999", "2000-2004"}
        offenders = [(t, e) for t, eras in self.data.items() for e in eras if e in old and "pe" in eras[e]]
        self.assertEqual(offenders, [], f"unexpected P/E on pre-2009 eras: {offenders[:5]}")

    def test_known_company_present(self):
        self.assertIn("AAPL", self.data)
        self.assertIn("price", self.data["AAPL"]["2020-2024"])


if __name__ == "__main__":
    unittest.main()
