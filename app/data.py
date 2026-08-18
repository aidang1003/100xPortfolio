"""Runtime dataset loader.

Loads `app/universe.json` (produced by `scripts/build_universe.py`): the full
S&P 500 universe bucketed into the 8 game categories x 7 eras.

Exposes the interface the game engine expects: ERAS, INDUSTRIES, STOCKS, cell().
"""

import json
import os

_UNIVERSE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "universe.json")


def _load():
    with open(_UNIVERSE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data["industries"], data["eras"], data["stocks"]


INDUSTRIES, ERAS, STOCKS = _load()


def cell(industry, era):
    """Return the list of pickable stocks for an (industry, era) cell."""
    return STOCKS[industry][era]
