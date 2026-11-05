"""Lineup engine tests."""

import math
import os
import random
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import config, game  # noqa: E402


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

    def test_best_run_tags_its_skips(self):
        legs = game.score(self.picks, seed="test-seed")["best"]["legs"]
        for leg, r in zip(legs, self.rounds):
            self.assertEqual("era" in leg["skips"], leg["eraLabel"] != r["eraLabel"])
            self.assertEqual("region" in leg["skips"], leg["location"] != r["location"])
        for kind in ("era", "region"):
            self.assertLessEqual(sum(kind in l["skips"] for l in legs), 1)

    def test_captured_is_annual_ratio(self):
        res = game.score(self.picks, seed="test-seed")
        expected = max(res["annualPct"], 0) / res["best"]["annualPct"] * 100
        self.assertAlmostEqual(res["capturedPct"], expected, delta=0.1)

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

    def test_accepts_each_skipped_cell(self):
        """A pick may come from the primary cell or from either reel's alternate."""
        rnd = self.data["rounds"][0]
        for era, loc in [(rnd["altEra"], rnd["location"]),        # era skip
                         (rnd["era"], rnd["altLocation"]),        # region skip
                         (rnd["altEra"], rnd["altLocation"])]:    # both, same round
            stock = next(s for s in game.cell_stocks(era, loc)
                         if self.picks[0]["industry"] in s["industries"])
            picks = [dict(p) for p in self.picks]
            picks[0] = {"era": era, "location": loc, "ticker": stock["ticker"],
                        "industry": self.picks[0]["industry"]}
            self.assertEqual(len(game.score(picks, seed="test-seed")["legs"]), 5)

    def test_rejects_unskipped_cell(self):
        """A cell neither reel could have re-rolled into is not pickable."""
        rnd = self.data["rounds"][0]
        other = next(e for e in game.ERAS if e not in (rnd["era"], rnd["altEra"]))
        picks = [dict(p) for p in self.picks]
        picks[0]["era"] = other
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

    def test_skip_alternates_are_deterministic(self):
        # An era skip on round 2 of the daily must land everyone on the same cell.
        a = game.daily_rounds("same-seed")["rounds"]
        b = game.daily_rounds("same-seed")["rounds"]
        alts = lambda rs: [(r["altEra"], r["altLocation"]) for r in rs]  # noqa: E731
        self.assertEqual(alts(a), alts(b))
        for r in a:  # and each alternate is a real re-roll, not the cell you're on
            self.assertNotEqual(r["altEra"], r["era"])
            self.assertNotEqual(r["altLocation"], r["location"])

    def test_many_seeds_are_solvable(self):
        # The matching guard must always yield a lineup-able board.
        for i in range(60):
            rounds = game.daily_rounds(f"seed-{i}")["rounds"]
            self.assertEqual(len(_legal_lineup(rounds)), game.NUM_ROUNDS, f"seed-{i} unsolvable")


class ScoringTests(unittest.TestCase):
    def test_round_score_anchors(self):
        for multiple, expected in [(0, 0), (0.01, 1), (0.5, 5), (0.94, 9), (1, 10), (1.5, 50), (2, 86), (game.ROUND_CAP, 100), (10, 100)]:
            self.assertEqual(game.round_score(multiple), expected, multiple)

    def test_round_score_never_falls_as_return_rises(self):
        scores = [game.round_score(m / 100) for m in range(0, 400)]
        self.assertEqual(scores, sorted(scores))

    def test_bands_split_the_game_score_evenly(self):
        rng = lambda: random.Random(0)  # noqa: E731
        n = len(game._TIERS)
        for i, (verdict, _, _) in enumerate(game._TIERS):
            floor = game._tier_floor(i)
            self.assertAlmostEqual(floor, game.MAX_GAME_SCORE * (n - 1 - i) / n)
            self.assertEqual(game._grade(math.ceil(floor), rng())[1], verdict)
            if i:  # just under a floor falls to the rung below
                self.assertEqual(game._grade(math.ceil(game._tier_floor(i - 1)) - 1, rng())[1], verdict)

    def test_score_reports_round_and_game_scores(self):
        data = game.daily_rounds("test-seed")
        res = game.score(_legal_lineup(data["rounds"]), seed="test-seed")
        for leg in res["legs"]:
            self.assertEqual(leg["score"], game.round_score(leg["multiple"]))
        self.assertEqual(res["gameScore"], sum(l["score"] for l in res["legs"]))

    def test_pot_still_compounds_uncapped(self):
        data = game.daily_rounds("test-seed")
        res = game.score(_legal_lineup(data["rounds"]), seed="test-seed")
        pot = math.prod(l["multiple"] for l in res["legs"])
        self.assertAlmostEqual(res["multiple"], pot, delta=0.05 * pot + 0.01)

    def test_reveal_matches_the_scored_leg(self):
        data = game.daily_rounds("test-seed")
        picks = _legal_lineup(data["rounds"])
        leg = game.score(picks, seed="test-seed")["legs"][0]
        out = game.reveal(picks[0]["era"], picks[0]["location"], picks[0]["ticker"])
        for k in ("ticker", "multiple", "gainPct", "score", "rank", "cellSize", "medal"):
            self.assertEqual(out[k], leg[k])
        with self.assertRaises(ValueError):
            game.reveal(picks[0]["era"], picks[0]["location"], "ZZZZ")


class DayTests(unittest.TestCase):
    def test_day_rolls_at_denver_midnight(self):
        # 05:30 UTC is still the previous day in Denver (23:30 MDT).
        moment = datetime(2026, 8, 20, 5, 30, tzinfo=timezone.utc)
        self.assertEqual(moment.astimezone(config.GAME_TZ).date().isoformat(), "2026-08-19")

    def test_day_number_counts_from_day_one(self):
        self.assertEqual(game.day_number(config.DAY_ONE.isoformat()), 1)
        self.assertEqual(game.day_number("2026-11-13"), 11)

    def test_practice_seed_is_never_a_day(self):
        seeds = {game.practice_seed() for _ in range(50)}
        self.assertEqual(len(seeds), 50)
        self.assertNotIn(game.today_str(), seeds)

    def test_mode_tracks_the_seed(self):
        self.assertEqual(game.daily_rounds()["mode"], "daily")
        self.assertEqual(game.daily_rounds(game.today_str())["mode"], "daily")
        self.assertEqual(game.daily_rounds(game.practice_seed())["mode"], "practice")


if __name__ == "__main__":
    unittest.main()
