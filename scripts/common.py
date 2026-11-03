"""Shared pipeline constants. Must not import other pipeline scripts (cycles)."""

import csv
import io
import json
import os
import urllib.request

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

SP500_CACHE = os.path.join(HERE, ".cache", "sp500.csv")
SP500_URL = "https://raw.githubusercontent.com/fja05680/sp500/master/sp500.csv"

# GICS sector -> game category
with open(os.path.join(os.path.dirname(HERE), "app", "data", "gics_fold.json"), encoding="utf-8") as _f:
    FOLD = json.load(_f)


def sp500_csv():
    """fja05680 sp500.csv text, cached."""
    if not os.path.exists(SP500_CACHE):
        req = urllib.request.Request(SP500_URL, headers={"User-Agent": USER_AGENT})
        text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        os.makedirs(os.path.dirname(SP500_CACHE), exist_ok=True)
        with open(SP500_CACHE, "w", encoding="utf-8") as f:
            f.write(text)
        return text
    with open(SP500_CACHE, encoding="utf-8") as f:
        return f.read()


def load_sector_map():
    """ticker -> (name, sector, sub-industry)"""
    return {
        r["Symbol"].replace(".", "-"): (r["Security"], r["GICS Sector"], r["GICS Sub-Industry"])
        for r in csv.DictReader(io.StringIO(sp500_csv()))
    }
