"""Shared constants + source-CSV loader for the data pipeline.

Stdlib-only, no app/Flask imports, and no dependency on any other pipeline
script — so every build step can import this without creating a cycle.
"""

import csv
import io
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))

# Display ticker -> data-provider (Yahoo) symbol when they differ.
SYMBOL = {"BRK": "BRK-B", "FB": "META"}

USER_AGENT = "Mozilla/5.0 (100xPortfolio collector)"

# The 5-year eras the slot machine can land on (data windows).
ERAS = [
    "1990-1994",
    "1995-1999",
    "2000-2004",
    "2005-2009",
    "2010-2014",
    "2015-2019",
    "2020-2024",
]

# The 8 game categories (11 GICS sectors fold into these; see app/data/gics_fold.json).
CATEGORIES = [
    "Technology",
    "Healthcare",
    "Financials",
    "Consumer Discretionary",
    "Consumer Staples",
    "Industrials",
    "Utilities",
    "Materials",
]

SP500_CACHE = os.path.join(HERE, ".cache", "sp500.csv")
SP500_URL = "https://raw.githubusercontent.com/fja05680/sp500/master/sp500.csv"

# 11 GICS sectors -> the 8 game categories (Comm Svcs -> Tech, Real Estate ->
# Financials, Energy -> Materials). Editable data, not code.
with open(os.path.join(os.path.dirname(HERE), "app", "data", "gics_fold.json"), encoding="utf-8") as _f:
    FOLD = json.load(_f)


def sp500_csv():
    """Raw text of the fja05680 sp500.csv (Security / GICS / HQ), cached locally."""
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
    """ticker -> (name, GICS sector, sub-industry)."""
    return {
        r["Symbol"].replace(".", "-"): (r["Security"], r["GICS Sector"], r["GICS Sub-Industry"])
        for r in csv.DictReader(io.StringIO(sp500_csv()))
    }
