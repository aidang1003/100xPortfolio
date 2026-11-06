"""Email list: subscribe, confirm, unsubscribe, daily send, game history. Redis and Resend are faked."""

import json
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import EMAIL_COOKIE, app, game, subscribers  # noqa: E402
from tests.test_game import _legal_lineup  # noqa: E402


class FakeRedis:
    def __init__(self):
        self.data = {}

    def __call__(self, cmd, key, *args):
        d = self.data
        if cmd == "SADD":
            d.setdefault(key, set()).add(args[0])
        elif cmd == "SREM":
            d.get(key, set()).discard(args[0])
        elif cmd == "SISMEMBER":
            return int(args[0] in d.get(key, set()))
        elif cmd == "SMEMBERS":
            return sorted(d.get(key, set()))
        elif cmd == "SMOVE":
            if args[1] not in d.get(key, set()):
                return 0
            d[key].discard(args[1])
            d.setdefault(args[0], set()).add(args[1])
            return 1
        elif cmd == "SET":  # only used as SET NX EX
            if key in d:
                return None
            d[key] = args[0]
            return "OK"
        elif cmd == "RPUSH":
            d.setdefault(key, []).append(args[0])


class SubscriberTests(unittest.TestCase):
    def setUp(self):
        self.redis, self.sent = FakeRedis(), []
        for p in (mock.patch.object(subscribers, "_redis", self.redis),
                  mock.patch.object(subscribers, "_send", self.sent.extend),
                  mock.patch.dict(os.environ, {"LINK_SECRET": "test", "CRON_SECRET": "cron"})):
            p.start()
            self.addCleanup(p.stop)
        self.client = app.test_client()

    def _subscribe(self, email):
        return self.client.post("/api/subscribe", json={"email": email})

    def test_token_round_trip_and_tamper(self):
        token = subscribers.make_token("a@b.co")
        self.assertEqual(subscribers.read_token(token), "a@b.co")
        self.assertIsNone(subscribers.read_token(subscribers.make_token("x@b.co").split(".")[0] + "." + token.split(".")[1]))
        self.assertIsNone(subscribers.read_token("junk"))

    def test_subscribe_is_pending_until_confirmed(self):
        self.assertEqual(self._subscribe("  A@B.co ").status_code, 200)
        self.assertEqual(self.redis.data[subscribers.PENDING], {"a@b.co"})
        self.assertEqual(len(self.sent), 1)
        self.client.get(f"/confirm?k={subscribers.make_token('a@b.co')}")
        self.assertEqual(self.redis.data[subscribers.CONFIRMED], {"a@b.co"})
        self.assertEqual(self.redis.data[subscribers.PENDING], set())

    def test_bad_email_rejected(self):
        self.assertEqual(self._subscribe("nope").status_code, 400)

    def test_confirm_email_sent_once_a_day(self):
        self._subscribe("a@b.co")
        self._subscribe("a@b.co")
        self.assertEqual(len(self.sent), 1)

    def test_unsubscribe_get_and_one_click_post(self):
        for method in ("get", "post"):
            self.redis.data[subscribers.CONFIRMED] = {"a@b.co"}
            res = getattr(self.client, method)(f"/unsubscribe?k={subscribers.make_token('a@b.co')}")
            self.assertEqual(res.status_code, 200)
            self.assertEqual(self.redis.data[subscribers.CONFIRMED], set())

    def test_cron_needs_secret_and_mails_confirmed_only(self):
        self.redis.data[subscribers.CONFIRMED] = {"a@b.co"}
        self.redis.data[subscribers.PENDING] = {"p@b.co"}
        self.assertEqual(self.client.get("/api/cron/daily").status_code, 401)
        res = self.client.get("/api/cron/daily", headers={"Authorization": "Bearer cron"})
        self.assertEqual(res.get_json(), {"sent": 1})
        self.assertEqual(self.sent[0]["to"], ["a@b.co"])
        self.assertIn("List-Unsubscribe", self.sent[0]["headers"])

    def test_email_link_cookie_records_scored_daily(self):
        n = game.day_number(game.today_str())
        res = self.client.get(f"/d/{n}?k={subscribers.make_token('a@b.co')}")
        self.assertEqual(res.status_code, 302)  # token stripped from the address bar
        self.assertIsNotNone(self.client.get_cookie(EMAIL_COOKIE))
        board = self.client.get("/api/daily").get_json()
        self.client.post("/api/score", json={"picks": _legal_lineup(board["rounds"]), "seed": board["seed"]})
        games = [json.loads(g) for g in self.redis.data["games:a@b.co"]]
        self.assertEqual(games[0]["dayNumber"], n)


if __name__ == "__main__":
    unittest.main()
