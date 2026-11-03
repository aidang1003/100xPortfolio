#!/usr/bin/env python3
"""Build app/universe.json. Survivor-only: roster names without metadata or prices
are dropped; landmines.json adds back bankruptcies at 0x."""

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
    companies = _load_json("companies.json")
    membership = _load_json("membership.json")["years"]
    landmines = _load_json("data", "landmines.json")
    try:
        fundamentals = _load_json("fundamentals.json")
    except FileNotFoundError:
        fundamentals = {}

    stocks = {c: {e: [] for e in ERAS} for c in CATEGORIES}
    counts = defaultdict(int)
    for era in ERAS:
        roster = membership[era.split("-")[0]]["tickers"]
        for t in roster:
            co = companies.get(t)
            if not co:
                continue
            mult = collect.multiple(t, era)
            if mult is None:
                continue
            # Bucket by primary industry.
            cat = co["industries"][0]
            entry = {"ticker": t, "name": co["name"], "multiple": mult, "sub": co["sub"],
                     "hq": co["hq"], "industries": co["industries"]}
            metrics = fundamentals.get(t, {}).get(era)
            if metrics:
                entry["metrics"] = metrics
            stocks[cat][era].append(entry)
            counts[era] += 1

    for lm in landmines:
        stocks[lm["category"]][lm["era"]].append({
            "ticker": lm["ticker"], "name": lm["name"], "multiple": lm["multiple"],
            "sub": "Bankruptcy", "industries": [lm["category"]],
            "hq": {"city": "", "state": "", "region": lm["region"]},
        })

    for cat in CATEGORIES:
        for era in ERAS:
            stocks[cat][era].sort(key=lambda s: s["multiple"], reverse=True)

    collect.save_prices()  # persist series fetched on a cache miss

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
