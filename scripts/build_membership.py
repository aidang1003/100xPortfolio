#!/usr/bin/env python3
"""Build app/membership.json: S&P 500 roster as of Jan 1 each year. Pre-1996 years are proxied."""

import json
import os
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
import common  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(HERE), "app", "membership.json")
FIRST_YEAR = 1990
FIRST_SNAPSHOT_YEAR = 1996


def build():
    components = common.load_components()
    last_year = date.today().year
    years = {}
    for y in range(FIRST_YEAR, last_year + 1):
        roster, proxied = common.roster_at(components, f"{y}-01-01")
        years[str(y)] = {"proxied": proxied, "tickers": sorted(roster)}
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": "fja05680/sp500 — S&P 500 Historical Components & Changes",
        "note": f"Roster as of Jan 1 each year. Pre-{FIRST_SNAPSHOT_YEAR} years are proxied "
                "from the earliest snapshot (1996-01-02).",
        "years": years,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
        f.write("\n")
    return payload


if __name__ == "__main__":
    p = build()
    yrs = p["years"]
    proxied = [y for y, v in yrs.items() if v["proxied"]]
    print(f"Wrote {OUT_PATH}: {len(yrs)} years ({min(yrs)}–{max(yrs)}), proxied: {proxied}")
    print("roster sizes:", {y: len(yrs[y]['tickers']) for y in sorted(yrs)})
