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
# (the survivor-only data set can't supply them, so without these the old eras
# show almost nothing but winners). (ticker, name, era, mult, cat, blurb)
#
# Display tickers are the recognizable forms (EK, not the EKDKQ bankruptcy
# symbol). Multiples are the holder's outcome buying at era start: 0.0 for a
# wipeout, a small fraction for a fire-sale / ~90% collapse.
LANDMINES = [
    # 1990-1994 — proxied era, zero survivor losers; the S&L crisis + early-90s recession.
    ("PN", "Pan Am", "1990-1994", 0.0, "Industrials", "The iconic airline runs out of altitude. Ceased flying Dec 1991."),
    ("WANG", "Wang Laboratories", "1990-1994", 0.0, "Technology", "Minicomputer pioneer crushed by the PC. Bankrupt 1992."),
    ("NEB", "Bank of New England", "1990-1994", 0.0, "Financials", "Seized by regulators in the 1991 credit crunch."),
    # 1995-1999 — dot-com run-up, but plenty of old-economy names imploded.
    ("FTL", "Fruit of the Loom", "1995-1999", 0.0, "Consumer Discretionary", "Underwear giant unravels under its debt. Bankrupt 1999."),
    ("SOC", "Sunbeam", "1995-1999", 0.2, "Consumer Discretionary", "'Chainsaw Al' Dunlap's accounting fraud unravels. 1998."),
    ("IRID", "Iridium", "1995-1999", 0.0, "Technology", "Motorola's $5B satellite-phone moonshot. Bankrupt 1999."),
    # 2000-2004 — the dot-com / telecom bust.
    ("ENE", "Enron", "2000-2004", 0.0, "Materials", "Accounting-fraud implosion. Bankrupt 2001."),
    ("WCOM", "WorldCom", "2000-2004", 0.0, "Technology", "$11B accounting fraud. Bankrupt 2002."),
    ("GBLX", "Global Crossing", "2000-2004", 0.0, "Technology", "Fiber-optic empire drowns in debt. Bankrupt 2002."),
    ("PETS", "Pets.com", "2000-2004", 0.0, "Consumer Discretionary", "The sock puppet goes to zero."),
    ("LU", "Lucent Technologies", "2000-2004", 0.07, "Technology", "Telecom-gear darling falls ~90% as the bubble bursts."),
    ("KM", "Kmart", "2000-2004", 0.0, "Consumer Discretionary", "Then the largest retail bankruptcy in U.S. history. 2002."),
    # 2005-2009 — the global financial crisis.
    ("NT", "Nortel Networks", "2005-2009", 0.0, "Technology", "Telecom-equipment giant collapses. Bankrupt 2009."),
    ("LEH", "Lehman Brothers", "2005-2009", 0.0, "Financials", "September 2008. The one that broke the system."),
    ("BSC", "Bear Stearns", "2005-2009", 0.06, "Financials", "March 2008 fire-sale to JPM at ~$2/share."),
    ("WM", "Washington Mutual", "2005-2009", 0.0, "Financials", "Largest bank failure in U.S. history. 2008."),
    ("CFC", "Countrywide Financial", "2005-2009", 0.07, "Financials", "Subprime poster child sold to BofA for scraps. 2008."),
    ("FNM", "Fannie Mae", "2005-2009", 0.02, "Financials", "Mortgage giant seized by the government. Sept 2008."),
    ("FRE", "Freddie Mac", "2005-2009", 0.02, "Financials", "Into federal conservatorship as housing collapses. 2008."),
    ("WB", "Wachovia", "2005-2009", 0.08, "Financials", "Sold to Wells Fargo in the 2008 panic."),
    ("GGP", "General Growth Properties", "2005-2009", 0.05, "Financials", "Mall-REIT giant buried by debt. Bankrupt 2009."),
    ("CC", "Circuit City", "2005-2009", 0.0, "Consumer Discretionary", "Big-box electronics chain liquidates by 2009."),
    ("GM", "General Motors", "2005-2009", 0.0, "Consumer Discretionary", "2009 bankruptcy wipes out the old GM."),
    # 2010-2014 — long bull market, but the wreckage of the crisis kept landing.
    ("EK", "Eastman Kodak", "2010-2014", 0.02, "Technology", "Invented digital, then killed by it. Bankrupt 2012."),
    ("BBI", "Blockbuster", "2010-2014", 0.0, "Consumer Discretionary", "Passed on buying Netflix. Bankrupt 2010."),
    ("MF", "MF Global", "2010-2014", 0.0, "Financials", "Corzine's brokerage makes a fatal sovereign-debt bet. Bankrupt 2011."),
    ("BGP", "Borders Group", "2010-2014", 0.0, "Consumer Discretionary", "Bookstore chain shelved by Amazon. Liquidated 2011."),
    ("DYN", "Dynegy", "2010-2014", 0.0, "Utilities", "Power producer collapses under its debt. Bankrupt 2011."),
    ("DNDN", "Dendreon", "2010-2014", 0.0, "Healthcare", "Provenge cancer-vaccine maker burns through its cash. Bankrupt 2014."),
    # 2015-2019 — retail apocalypse + the energy bust.
    ("SUNE", "SunEdison", "2015-2019", 0.0, "Technology", "Solar darling's debt binge implodes. Bankrupt 2016."),
    ("SHLD", "Sears", "2015-2019", 0.02, "Consumer Discretionary", "An American retail icon fades to nothing. 2018."),
    ("RSH", "RadioShack", "2015-2019", 0.0, "Consumer Discretionary", "The corner electronics store runs out of road. 2015."),
    ("VRX", "Valeant Pharmaceuticals", "2015-2019", 0.1, "Healthcare", "Price-gouging scandal vaporizes ~90% of its value. 2016."),
    ("WFT", "Weatherford", "2015-2019", 0.0, "Materials", "Oilfield-services giant drowns in debt. Bankrupt 2019."),
    ("CHK", "Chesapeake Energy", "2015-2019", 0.12, "Materials", "Shale-gas pioneer's debt binge collapses ~85%."),
    ("FTR", "Frontier Communications", "2015-2019", 0.05, "Technology", "Rural-telecom rollup falls ~95% under its debt."),
    # 2020-2024 — the 2023 banking crisis + the meme-stock hangover.
    ("BBBY", "Bed Bath & Beyond", "2020-2024", 0.0, "Consumer Discretionary", "Meme mania can't stop the bankruptcy. 2023."),
    ("JCP", "JCPenney", "2020-2024", 0.0, "Consumer Discretionary", "Century-old department store undone by COVID. 2020."),
    ("SIVB", "SVB Financial", "2020-2024", 0.0, "Financials", "March 2023 bank run. Gone in 48 hours."),
    ("SBNY", "Signature Bank", "2020-2024", 0.0, "Financials", "Seized by regulators days after SVB. March 2023."),
    ("FRC", "First Republic Bank", "2020-2024", 0.0, "Financials", "Third major U.S. bank to fall in 2023. Seized in May."),
    ("WE", "WeWork", "2020-2024", 0.0, "Financials", "From a $47B valuation to bankruptcy. 2023."),
    ("RAD", "Rite Aid", "2020-2024", 0.0, "Consumer Staples", "Drugstore chain buckles under debt and opioid suits. 2023."),
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
