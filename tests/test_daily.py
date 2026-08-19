"""Tests for the daily-vs-practice rule at the HTTP layer.

Run: .venv/bin/python -m unittest tests.test_daily
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import DAILY_COOKIE, app, game  # noqa: E402
from tests.test_game import _legal_lineup  # noqa: E402


class DailyModeTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()  # one browser: keeps its own cookie jar

    def _board(self, seed=None):
        url = f"/api/daily?seed={seed}" if seed else "/api/daily"
        return self.client.get(url).get_json()

    def _play(self, board):
        return self.client.post(
            "/api/score", json={"picks": _legal_lineup(board["rounds"]), "seed": board["seed"]})

    def test_first_play_is_the_shared_daily(self):
        board = self._board()
        self.assertEqual(board["mode"], "daily")
        self.assertEqual(board["seed"], game.today_str())
        self.assertEqual(board["dayNumber"], game.day_number(game.today_str()))

    def test_daily_survives_an_abandoned_run(self):
        self._board()  # dealt but never scored
        self.assertEqual(self._board()["mode"], "daily")

    def test_scoring_the_daily_switches_the_session_to_practice(self):
        daily = self._board()
        res = self._play(daily)
        self.assertEqual(res.get_json()["mode"], "daily")
        self.assertEqual(self.client.get_cookie(DAILY_COOKIE).value, game.today_str())

        first, second = self._board(), self._board()
        for board in (first, second):
            self.assertEqual(board["mode"], "practice")
            self.assertNotEqual(board["seed"], game.today_str())
        self.assertNotEqual(first["seed"], second["seed"])  # truly random each time

    def test_practice_does_not_burn_another_session_daily(self):
        self._play(self._board())
        self.assertEqual(app.test_client().get("/api/daily").get_json()["mode"], "daily")

    def test_explicit_seed_resumes_that_board(self):
        board = self._board(game.today_str())
        self.assertEqual(board["mode"], "daily")
        again = self._board(board["seed"])
        self.assertEqual([r["era"] for r in again["rounds"]], [r["era"] for r in board["rounds"]])

    def test_daily_board_is_identical_across_sessions(self):
        keys = lambda b: [(r["era"], r["location"], r["altEra"], r["altLocation"])  # noqa: E731
                          for r in b["rounds"]]
        self.assertEqual(keys(self._board()), keys(app.test_client().get("/api/daily").get_json()))


if __name__ == "__main__":
    unittest.main()
