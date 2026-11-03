"""Loads app/universe.json (built by scripts/build_universe.py)."""

import json
import os

_UNIVERSE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "universe.json")


def _load():
    with open(_UNIVERSE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["industries"], data["eras"], data["stocks"]


INDUSTRIES, ERAS, STOCKS = _load()


def cell(industry, era):
    return STOCKS[industry][era]
