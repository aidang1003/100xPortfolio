"""Shared pipeline constants. Must not import other pipeline scripts (cycles)."""

import csv
import io
import json
import os
import urllib.request
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))

# Display ticker -> Yahoo symbol.
SYMBOL = {"BRK": "BRK-B", "FB": "META"}

USER_AGENT = "Mozilla/5.0 (100xPortfolio collector)"

ERAS = [
    "1990-1994",
    "1995-1999",
    "2000-2004",
    "2005-2009",
    "2010-2014",
    "2015-2019",
    "2020-2024",
]

CATEGORIES = [
    "Technology",
    "Financials",
    "Consumer",
    "Health & Utilities",
    "Industry & Energy",
]

_FJA = "https://raw.githubusercontent.com/fja05680/sp500/master/"
_CACHE = os.path.join(HERE, ".cache")

# GICS sector -> game category
with open(os.path.join(os.path.dirname(HERE), "app", "data", "gics_fold.json"), encoding="utf-8") as _f:
    FOLD = json.load(_f)


def _fja_csv(name, cache_name):
    """fja05680 CSV text, cached."""
    path = os.path.join(_CACHE, cache_name)
    if not os.path.exists(path):
        req = urllib.request.Request(_FJA + quote(name), headers={"User-Agent": USER_AGENT})
        text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        os.makedirs(_CACHE, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return text
    with open(path, encoding="utf-8") as f:
        return f.read()


def sp500_csv():
    """Current members: Security / GICS / HQ / CIK."""
    return _fja_csv("sp500.csv", "sp500.csv")


def load_components():
    """Membership history: [(date, [tickers])] ascending. Starts 1996-01-02."""
    text = _fja_csv("S&P 500 Historical Components & Changes (Updated).csv", "sp500_components.csv")
    reader = csv.reader(text.splitlines())
    next(reader, None)
    rows = [(r[0], [t.strip() for t in r[1].split(",") if t.strip()]) for r in reader if len(r) >= 2]
    return sorted(rows, key=lambda r: r[0])


def roster_at(components, date_str):
    """-> (tickers, proxied). proxied = date predates the list; earliest snapshot used."""
    pick = None
    for d, tickers in components:
        if d > date_str:
            break
        pick = tickers
    return (components[0][1], True) if pick is None else (pick, False)


def load_sector_map():
    """ticker -> (name, sector, sub-industry)"""
    return {
        r["Symbol"].replace(".", "-"): (r["Security"], r["GICS Sector"], r["GICS Sub-Industry"])
        for r in csv.DictReader(io.StringIO(sp500_csv()))
    }
