#!/usr/bin/env python3
"""Generate COVERAGE.md: the stock-coverage chart plus a gap analysis against the
current S&P 500 (survivorship bias + current members missing from every era)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import find_candidates as fc  # noqa: E402  (roster history)
import collect  # noqa: E402  (returns cache)
import build_universe as bu  # noqa: E402  (sector map + fold)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "COVERAGE.md")


def lbl(era):
    s = era.split("-")[0]
    return f"{s}-{int(s) + 5}"


def main():
    uni = json.load(open(os.path.join(ROOT, "app", "universe.json"), encoding="utf-8"))
    cats, eras, S = uni["industries"], uni["eras"], uni["stocks"]
    sect = bu.load_sector_map()  # ticker -> (name, GICS sector, sub-industry)
    comp = fc.load_components()
    cache = collect._load()

    out = []
    w = out.append

    w("# Stock coverage — 100xPortfolio universe")
    w("")
    w(f"Generated from `app/universe.json` (built {uni['generatedAt'][:10]}). Each cell is the")
    w("number of pickable stocks for that category × era.")
    w("")
    w("| Category | " + " | ".join(lbl(e) for e in eras) + " | **Total** |")
    w("|" + "---|" * (len(eras) + 2))
    coltot = {e: 0 for e in eras}
    grand = 0
    for c in cats:
        vals = [len(S[c][e]) for e in eras]
        for e, v in zip(eras, vals):
            coltot[e] += v
        grand += sum(vals)
        w("| " + c + " | " + " | ".join(str(v) for v in vals) + f" | **{sum(vals)}** |")
    w("| **Total** | " + " | ".join(f"**{coltot[e]}**" for e in eras) + f" | **{grand}** |")
    w("")

    w("## Why the per-era totals are ~130–390, not ~500")
    w("")
    w("The S&P 500 held ~500 names in every era, but each era cell is built by intersecting")
    w("that era's index roster with **today's** sector map (`sp500.csv`, 503 names). Any")
    w("company that was in the index then but has since been acquired, delisted, or dropped")
    w("has no current sector and is excluded — **survivorship bias**, worst in the old eras")
    w("(only ~39% of the 2000 index is still listed today).")
    w("")
    w("| Era | In S&P that era | Kept in game | Dropped: no longer in index | Dropped: no return data |")
    w("|---|---|---|---|---|")
    for e in eras:
        roster = fc.roster_at(comp, e.split("-")[0] + "-01-01")[0]
        in_sect = [t for t in roster if t in sect]
        has = [t for t in in_sect if cache.get(e + "|" + t) is not None]
        w(f"| {lbl(e)} | {len(roster)} | {len(has)} | {len(roster) - len(in_sect)} | {len(in_sect) - len(has)} |")
    w("")
    w('"Kept in game" is survivors-with-data (the era totals above, minus a few curated')
    w('landmines). The dominant loss is **"no longer in index"** — historical members we have')
    w("no current GICS sector for, so they can't be bucketed.")
    w("")

    uni_tk = {s["ticker"] for c in cats for e in eras for s in S[c][e]}
    missing = sorted(t for t in sect if t not in uni_tk)
    w(f"## {len(missing)} current S&P 500 members missing from every era")
    w("")
    w("A separate gap: the universe uses each era's **start-date** roster, so companies added")
    w("to the index later never appear. Marquee omissions: **Tesla** (added Dec 2020),")
    w("**Meta**, **Berkshire Hathaway**, **Uber**, **Palantir**, **Coinbase**, **Airbnb**,")
    w("**KKR**, **Blackstone**, **CrowdStrike**.")
    w("")
    w(f"<details><summary>Full list of {len(missing)} missing current members</summary>")
    w("")
    for t in missing:
        name, gsec, _ = sect[t]
        w(f"- `{t}` — {name} ({gsec})")
    w("")
    w("</details>")
    w("")

    w("## Recommended fixes")
    w("")
    w("1. **Fuller eras (the big one):** fetch returns for the *full* historical roster, not")
    w("   just current survivors, and source **point-in-time GICS sectors** for the now-delisted")
    w("   names (e.g. Yahoo `quoteSummary` assetProfile, or a historical sector table) so they")
    w("   can be bucketed. This is what moves eras toward ~500.")
    w("2. **Missing current names:** bucket each era from a later/union roster (or current")
    w("   membership for the live era) instead of only the era-start snapshot — captures Tesla,")
    w("   Uber, Palantir, etc. (~100 of these are in the latest membership snapshot).")
    w("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {OUT}: {grand} entries, {len(missing)} current members missing from every era")


if __name__ == "__main__":
    main()
