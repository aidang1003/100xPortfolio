#!/usr/bin/env python3
"""Process cached returns into the 8-category S&P 500 universe -> app/universe.json.

Pure assembly from already-collected data: the durable returns cache
(scripts/data/returns_cache.json) + the GICS sector map (fja05680 sp500.csv) +
the per-era index roster. No network unless a roster ticker's multiple is
missing from the cache, in which case it's fetched once via collect and saved.

Each era's S&P 500 members are bucketed into 8 game categories (the 11 GICS
sectors with Real Estate, Energy and Communication Services folded in). Curated
blurbs are overlaid where we have them, and famous bankruptcies are layered on
as 0x "landmine" picks (the data is survivor-only, so they'd otherwise vanish).
"""

import csv
import io
import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import collect  # noqa: E402
import find_candidates as fc  # noqa: E402  (roster history loader + catalog)

catalog = fc.catalog
ERAS = catalog.ERAS
OUT_PATH = os.path.join(os.path.dirname(HERE), "app", "universe.json")
SP500_CACHE = os.path.join(HERE, ".cache", "sp500.csv")
SP500_URL = "https://raw.githubusercontent.com/fja05680/sp500/master/sp500.csv"

# 11 GICS sectors -> 8 game categories (the three sparse-in-early-eras sectors
# fold into the nearest fit: Comm Svcs -> Tech, Real Estate -> Financials,
# Energy -> Materials).
FOLD = {
    "Information Technology": "Technology",
    "Communication Services": "Technology",
    "Health Care": "Healthcare",
    "Financials": "Financials",
    "Real Estate": "Financials",
    "Consumer Discretionary": "Consumer Discretionary",
    "Consumer Staples": "Consumer Staples",
    "Industrials": "Industrials",
    "Utilities": "Utilities",
    "Materials": "Materials",
    "Energy": "Materials",
}
CATEGORIES = [
    "Technology", "Healthcare", "Financials", "Consumer Discretionary",
    "Consumer Staples", "Industrials", "Utilities", "Materials",
]

# Famous flameouts, layered in as 0x gotcha picks for the era they collapsed
# (the survivor-only data set can't supply them). (ticker, name, era, mult, cat, blurb)
LANDMINES = [
    ("ENE", "Enron", "2000-2004", 0.0, "Materials", "Accounting-fraud implosion. Bankrupt 2001."),
    ("WCOM", "WorldCom", "2000-2004", 0.0, "Technology", "$11B accounting fraud. Bankrupt 2002."),
    ("GBLX", "Global Crossing", "2000-2004", 0.0, "Technology", "Fiber-optic empire drowns in debt. Bankrupt 2002."),
    ("PETS", "Pets.com", "2000-2004", 0.0, "Consumer Discretionary", "The sock puppet goes to zero."),
    ("NT", "Nortel Networks", "2005-2009", 0.0, "Technology", "Telecom-equipment giant collapses. Bankrupt 2009."),
    ("LEH", "Lehman Brothers", "2005-2009", 0.0, "Financials", "September 2008. The one that broke the system."),
    ("BSC", "Bear Stearns", "2005-2009", 0.06, "Financials", "March 2008 fire-sale to JPM at ~$2/share."),
    ("WM", "Washington Mutual", "2005-2009", 0.0, "Financials", "Largest bank failure in U.S. history. 2008."),
    ("CC", "Circuit City", "2005-2009", 0.0, "Consumer Discretionary", "Big-box electronics chain liquidates by 2009."),
    ("GM", "General Motors", "2005-2009", 0.0, "Consumer Discretionary", "2009 bankruptcy wipes out the old GM."),
    ("EK", "Eastman Kodak", "2010-2014", 0.02, "Technology", "Invented digital, then killed by it. Bankrupt 2012."),
    ("BBI", "Blockbuster", "2010-2014", 0.0, "Consumer Discretionary", "Passed on buying Netflix. Bankrupt 2010."),
    ("SUNE", "SunEdison", "2015-2019", 0.0, "Technology", "Solar darling's debt binge implodes. Bankrupt 2016."),
    ("SHLD", "Sears", "2015-2019", 0.02, "Consumer Discretionary", "An American retail icon fades to nothing. 2018."),
    ("RSH", "RadioShack", "2015-2019", 0.0, "Consumer Discretionary", "The corner electronics store runs out of road. 2015."),
    ("BBBY", "Bed Bath & Beyond", "2020-2024", 0.0, "Consumer Discretionary", "Meme mania can't stop the bankruptcy. 2023."),
    ("JCP", "JCPenney", "2020-2024", 0.0, "Consumer Discretionary", "Century-old department store undone by COVID. 2020."),
    ("SIVB", "SVB Financial", "2020-2024", 0.0, "Financials", "March 2023 bank run. Gone in 48 hours."),
]


def load_sector_map():
    """ticker -> (name, GICS sector, sub-industry), cached locally."""
    if os.path.exists(SP500_CACHE):
        text = open(SP500_CACHE, encoding="utf-8").read()
    else:
        req = urllib.request.Request(SP500_URL, headers={"User-Agent": collect.USER_AGENT})
        text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        os.makedirs(os.path.dirname(SP500_CACHE), exist_ok=True)
        open(SP500_CACHE, "w", encoding="utf-8").write(text)
    out = {}
    for r in csv.DictReader(io.StringIO(text)):
        sym = r["Symbol"].replace(".", "-")
        out[sym] = (r["Security"], r["GICS Sector"], r["GICS Sub-Industry"])
    return out


def blurb_overlay():
    """(ticker, era) -> curated blurb, from the hand-written catalog."""
    out = {}
    for eras in catalog.CATALOG.values():
        for era, stocks in eras.items():
            for s in stocks:
                out[(s["ticker"], era)] = s["blurb"]
    return out


def main():
    sect = load_sector_map()
    components = fc.load_components()
    cache = collect._load()
    blurbs = blurb_overlay()

    stocks = {c: {e: [] for e in ERAS} for c in CATEGORIES}
    counts = defaultdict(int)
    for era in ERAS:
        roster, _ = fc.roster_at(components, f"{era.split('-')[0]}-01-01")
        for t in roster:
            if t not in sect:
                continue
            mult = cache.get(f"{era}|{t}")
            if mult is None:  # delisted / no data -> excluded (survivor universe)
                continue
            name, gics, sub = sect[t]
            cat = FOLD.get(gics)
            if cat is None:
                continue
            entry = {"ticker": t, "name": name, "multiple": mult, "sub": sub}
            if (t, era) in blurbs:
                entry["blurb"] = blurbs[(t, era)]
            stocks[cat][era].append(entry)
            counts[era] += 1

    # Layer in the bankruptcy landmines.
    for ticker, name, era, mult, cat, blurb in LANDMINES:
        stocks[cat][era].append({"ticker": ticker, "name": name, "multiple": mult, "sub": "Bankruptcy", "blurb": blurb})

    # Sort each cell by multiple, best first.
    for cat in CATEGORIES:
        for era in ERAS:
            stocks[cat][era].sort(key=lambda s: s["multiple"], reverse=True)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo (cached 5y adj-close returns) + GICS sectors (fja05680 sp500.csv)",
        "eras": ERAS,
        "industries": CATEGORIES,
        "stocks": stocks,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
        f.write("\n")

    total = sum(len(stocks[c][e]) for c in CATEGORIES for e in ERAS)
    print(f"Wrote {OUT_PATH}: {total} entries across {len(CATEGORIES)} categories x {len(ERAS)} eras")
    print(f"\n{'category':24}" + "".join(f"{e[:7]:>9}" for e in ERAS))
    for c in CATEGORIES:
        print(f"{c:24}" + "".join(f"{len(stocks[c][e]):>9}" for e in ERAS))


if __name__ == "__main__":
    main()
