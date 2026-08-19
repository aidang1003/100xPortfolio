#!/usr/bin/env python3
"""Build app/membership.json — committed point-in-time S&P 500 membership.

Derives a compact **per-year roster** (index membership as of Jan 1 each year)
from the fja05680 historical-components list, so "who was in the index in year
X" is one small auditable file instead of a 5.5 MB CSV parsed at build time.

    python scripts/build_membership.py   # writes app/membership.json

The components list begins 1996-01-02, so years before that are flagged
`proxied` (they reuse the earliest snapshot) — the same caveat the pipeline has
always carried, now made explicit in the data.
"""

import json
import os
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
import find_candidates as fc  # noqa: E402  (load_components / roster_at)

OUT_PATH = os.path.join(os.path.dirname(HERE), "app", "membership.json")
FIRST_YEAR = 1990  # earliest year the game's eras reach back to
FIRST_SNAPSHOT_YEAR = 1996  # list coverage begins 1996-01-02; earlier = proxied


def build():
    components = fc.load_components()
    last_year = date.today().year
    years = {}
    for y in range(FIRST_YEAR, last_year + 1):
        roster, proxied = fc.roster_at(components, f"{y}-01-01")
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
