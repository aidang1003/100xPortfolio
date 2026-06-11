"""Runtime dataset loader.

Loads `app/universe.json` (produced by `scripts/build_universe.py`): the full
S&P 500 universe bucketed into the 8 game categories x 7 eras. Falls back to the
hand-curated catalog if the universe file is missing, so the app always runs.

Exposes the interface the game engine expects: ERAS, INDUSTRIES, STOCKS, cell().
"""

import json
import os

from . import catalog

_UNIVERSE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "universe.json")


def _from_catalog():
    """Fallback: the old hand-curated 6-category catalog."""
    stocks = {
        industry: {era: [dict(s) for s in cells] for era, cells in eras.items()}
        for industry, eras in catalog.CATALOG.items()
    }
    return catalog.INDUSTRIES, catalog.ERAS, stocks


def _load():
    try:
        with open(_UNIVERSE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("stocks") and data.get("industries") and data.get("eras"):
            return data["industries"], data["eras"], data["stocks"]
    except (json.JSONDecodeError, OSError, KeyError):
        pass
    return _from_catalog()


INDUSTRIES, ERAS, STOCKS = _load()


def cell(industry, era):
    """Return the list of pickable stocks for an (industry, era) cell."""
    return STOCKS[industry][era]
