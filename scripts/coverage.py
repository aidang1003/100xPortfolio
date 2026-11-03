#!/usr/bin/env python3
"""Generate docs/COVERAGE.md."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect  # noqa: E402
import common  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "COVERAGE.md")


def lbl(era):
    s = era.split("-")[0]
    return f"{s}-{int(s) + 5}"


def main():
    uni = json.load(open(os.path.join(ROOT, "app", "universe.json"), encoding="utf-8"))
    cats, eras, S = uni["industries"], uni["eras"], uni["stocks"]
    sect = common.load_sector_map()
    comp = common.load_components()
    collect._load_prices()

    out = []
    w = out.append

    w("# Stock coverage — 100xPortfolio universe")
    w("")
    w(f"Pickable stocks per category × era, from `app/universe.json` (built {uni['generatedAt'][:10]}).")
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

    w("## Survivorship: era-start roster vs. what the game keeps")
    w("")
    w("| Era | In S&P that era | Kept in game | Dropped: no longer in index | Dropped: no return data |")
    w("|---|---|---|---|---|")
    for e in eras:
        roster = common.roster_at(comp, e.split("-")[0] + "-01-01")[0]
        in_sect = [t for t in roster if t in sect]
        has = [t for t in in_sect if collect.multiple(t, e) is not None]
        w(f"| {lbl(e)} | {len(roster)} | {len(has)} | {len(roster) - len(in_sect)} | {len(in_sect) - len(has)} |")
    w("")

    uni_tk = {s["ticker"] for c in cats for e in eras for s in S[c][e]}
    missing = sorted(t for t in sect if t not in uni_tk)
    w(f"## {len(missing)} current S&P 500 members missing from every era")
    w("")
    w("<details><summary>Joined the index after every era start</summary>")
    w("")
    for t in missing:
        name, gsec, _ = sect[t]
        w(f"- `{t}` — {name} ({gsec})")
    w("")
    w("</details>")
    w("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {OUT}: {grand} entries, {len(missing)} current members missing from every era")


if __name__ == "__main__":
    main()
