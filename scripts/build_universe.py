#!/usr/bin/env python3
"""Process collected price series into the 8-category S&P 500 universe -> app/universe.json.

Pure assembly from already-collected data: the monthly price-series store
(scripts/data/prices.json) + per-company metadata (app/companies.json) + the
per-era index roster (app/membership.json). No network unless a roster ticker's
series is missing from the store, in which case it's fetched once and saved.

Each era's S&P 500 members are bucketed into 8 game categories (the 11 GICS
sectors with Real Estate, Energy and Communication Services folded in), and
famous bankruptcies are layered on as 0x "landmine" picks (the data is
survivor-only, so they'd otherwise vanish).
"""

import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import collect  # noqa: E402
import common  # noqa: E402

ERAS = common.ERAS
CATEGORIES = common.CATEGORIES
APP = os.path.join(os.path.dirname(HERE), "app")
OUT_PATH = os.path.join(APP, "universe.json")


def _load_json(*parts):
    with open(os.path.join(APP, *parts), encoding="utf-8") as f:
        return json.load(f)


def main():
    companies = _load_json("companies.json")            # name, industries[], sub, hq
    membership = _load_json("membership.json")["years"]  # {year: {tickers: [...]}}
    landmines = _load_json("data", "landmines.json")     # curated bankruptcy 0x picks
    try:
        fundamentals = _load_json("fundamentals.json")   # {ticker: {era: {pe?, price, divYield?}}}
    except FileNotFoundError:
        fundamentals = {}

    stocks = {c: {e: [] for e in ERAS} for c in CATEGORIES}
    counts = defaultdict(int)
    for era in ERAS:
        roster = membership[era.split("-")[0]]["tickers"]
        for t in roster:
            co = companies.get(t)
            if not co:  # no current metadata (delisted) -> excluded (survivor universe)
                continue
            mult = collect.multiple(t, era)  # on-the-fly from the monthly series
            if mult is None:  # delisted / no data -> excluded (survivor universe)
                continue
            # Bucket by primary category; carry the full industries list so the
            # game can honor multi-industry stocks in the one-per-industry lineup.
            cat = co["industries"][0]
            entry = {"ticker": t, "name": co["name"], "multiple": mult, "sub": co["sub"],
                     "hq": co["hq"], "industries": co["industries"]}
            metrics = fundamentals.get(t, {}).get(era)
            if metrics:  # entry P/E · price · div yield — shown at pick time
                entry["metrics"] = metrics
            stocks[cat][era].append(entry)
            counts[era] += 1

    # Layer in the bankruptcy landmines (from app/data/landmines.json).
    for lm in landmines:
        stocks[lm["category"]][lm["era"]].append({
            "ticker": lm["ticker"], "name": lm["name"], "multiple": lm["multiple"],
            "sub": "Bankruptcy", "industries": [lm["category"]],
            "hq": {"city": "", "state": "", "region": lm["region"]},
        })

    # Sort each cell by multiple, best first.
    for cat in CATEGORIES:
        for era in ERAS:
            stocks[cat][era].sort(key=lambda s: s["multiple"], reverse=True)

    collect.save_prices()  # persist any series fetched on a cache miss above

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "companies.json (name/industries/sub/hq) + membership.json (rosters) + Yahoo monthly adj-close series (on-the-fly multiples)",
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
