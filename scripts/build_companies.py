#!/usr/bin/env python3
"""Build app/companies.json: name, industries, HQ, CIK per ticker from fja05680 sp500.csv."""

import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402

OUT_PATH = os.path.join(os.path.dirname(HERE), "app", "companies.json")

# State -> US Census region
_REGIONS = {
    "Northeast": ["Connecticut", "Maine", "Massachusetts", "New Hampshire", "Rhode Island",
                  "Vermont", "New Jersey", "New York", "Pennsylvania"],
    "Midwest": ["Illinois", "Indiana", "Michigan", "Ohio", "Wisconsin", "Iowa", "Kansas",
                "Minnesota", "Missouri", "Nebraska", "North Dakota", "South Dakota"],
    "South": ["Delaware", "Florida", "Georgia", "Maryland", "North Carolina", "South Carolina",
              "Virginia", "West Virginia", "District of Columbia", "Alabama", "Kentucky",
              "Mississippi", "Tennessee", "Arkansas", "Louisiana", "Oklahoma", "Texas"],
    "West": ["Arizona", "Colorado", "Idaho", "Montana", "Nevada", "New Mexico", "Utah",
             "Wyoming", "Alaska", "California", "Hawaii", "Oregon", "Washington"],
}
STATE_REGION = {s: r for r, states in _REGIONS.items() for s in states}
US_STATES = set(STATE_REGION)

# Industries added beyond the GICS one.
MULTI_INDUSTRY = {
    "AMZN": ["Technology"],
    "TSLA": ["Technology"],
}


def _parse_hq(location):
    """'Cupertino, California' -> {city, state, region}; foreign -> region 'International'."""
    parts = [p.strip() for p in location.split(",")]
    if len(parts) >= 2 and parts[-1] in US_STATES:
        state = parts[-1]
        return {"city": parts[0], "state": state, "region": STATE_REGION[state]}
    return {"city": parts[0] if parts else "", "state": parts[-1] if len(parts) > 1 else "",
            "region": "International"}


def build():
    # Not load_sector_map(): it drops HQ.
    companies = {}
    for r in csv.DictReader(io.StringIO(common.sp500_csv())):
        sym = r["Symbol"].replace(".", "-")
        cat = common.FOLD.get(r["GICS Sector"])
        if cat is None:
            continue
        industries = [cat] + [i for i in MULTI_INDUSTRY.get(sym, []) if i != cat]
        entry = {
            "name": r["Security"].removesuffix(" (The)"),  # "Home Depot (The)" -> "Home Depot"
            "industries": industries,
            "sub": r["GICS Sub-Industry"],
            "hq": _parse_hq(r.get("Headquarters Location", "")),
        }
        cik = (r.get("CIK") or "").strip()
        if cik:
            entry["cik"] = int(cik)
        companies[sym] = entry
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(companies.items())), f, indent=1)
        f.write("\n")
    return companies


if __name__ == "__main__":
    c = build()
    regions = {}
    multi = sum(1 for v in c.values() if len(v["industries"]) > 1)
    for v in c.values():
        regions[v["hq"]["region"]] = regions.get(v["hq"]["region"], 0) + 1
    print(f"Wrote {OUT_PATH}: {len(c)} companies, {multi} multi-industry")
    print("by region:", dict(sorted(regions.items(), key=lambda x: -x[1])))
