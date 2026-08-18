"""Tests for the (era, location) one-per-industry lineup engine.

Run: .venv/bin/python -m unittest tests.test_game
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import game  # noqa: E402


def _legal_lineup(rounds):
    """Greedily build a valid lineup (a distinct industry per round)."""
    used, picks = set(), []
    for r in rounds:
        for s in r["stocks"]:
            opts = [i for i in s["industries"] if i not in used]
            if opts:
                used.add(opts[0])
                picks.append({"era": r["era"], "location": r["location"],
                              "ticker": s["ticker"], "industry": opts[0]})
                break
    return picks


class LineupEngineTests(unittest.TestCase):
    def setUp(self):
        self.data = game.daily_rounds("test-seed")
        self.rounds = self.data["rounds"]
        self.picks = _legal_lineup(self.rounds)

    def test_five_rounds_each_era_and_location(self):
        self.assertEqual(len(self.rounds), game.NUM_ROUNDS)
        for r in self.rounds:
            self.assertIn(r["location"], game.LOCATIONS)
            self.assertTrue(r["stocks"])

    def test_pick_payload_hides_outcome(self):
        s = self.rounds[0]["stocks"][0]
        self.assertNotIn("multiple", s)       # outcome hidden at pick time
        self.assertIn("industries", s)        # slots the client needs
        self.assertIn("metrics", s)           # entry metrics shown

    def test_a_legal_lineup_exists_and_scores(self):
        self.assertEqual(len(self.picks), game.NUM_ROUNDS)
        self.assertEqual(len({p["industry"] for p in self.picks}), game.NUM_ROUNDS)
        res = game.score(self.picks, seed="test-seed")
        self.assertEqual(len(res["legs"]), game.NUM_ROUNDS)
        self.assertGreaterEqual(res["multiple"], 0)

    def test_rejects_duplicate_industry(self):
        picks = [dict(p) for p in self.picks]
        # Force the last pick to reuse the first pick's industry (if that stock supports it).
        picks[-1]["industry"] = picks[0]["industry"]
        with self.assertRaises(ValueError):
            game.score(picks, seed="test-seed")

    def test_rejects_wrong_location(self):
        picks = [dict(p) for p in self.picks]
        picks[0]["location"] = "Nowhere"
        with self.assertRaises(ValueError):
            game.score(picks, seed="test-seed")

    def test_rejects_unknown_ticker(self):
        picks = [dict(p) for p in self.picks]
        picks[0]["ticker"] = "ZZZZ"
        with self.assertRaises(ValueError):
            game.score(picks, seed="test-seed")

    def test_seed_determinism(self):
        a = game.daily_rounds("same-seed")["rounds"]
        b = game.daily_rounds("same-seed")["rounds"]
        self.assertEqual([(r["era"], r["location"]) for r in a],
                         [(r["era"], r["location"]) for r in b])

    def test_many_seeds_are_solvable(self):
        # The matching guard must always yield a lineup-able board.
        for i in range(60):
            rounds = game.daily_rounds(f"seed-{i}")["rounds"]
            self.assertEqual(len(_legal_lineup(rounds)), game.NUM_ROUNDS, f"seed-{i} unsolvable")


if __name__ == "__main__":
    unittest.main()
