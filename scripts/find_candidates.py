#!/usr/bin/env python3
"""Find candidate S&P 500 stocks per era that aren't already in the catalog.

Pulls the survivorship-bias-free S&P 500 historical membership list from
fja05680/sp500, takes the index roster as of each era's *start*, drops the names
already in `app/catalog.py` for that era, then (optionally) fetches each
candidate's 5-year return from Yahoo with an **identity check** — so a reused or
renamed ticker (PETS = PetMed today, not Pets.com; CC = Chemours, not Circuit
City) isn't silently scored as the wrong company.

The output is a ranked menu per era to drive manual curation into `catalog.py`.
Bucketing candidates into the game's six industries stays a human call: the
membership list carries no sector, and the game's industries are a custom subset
of GICS.

    python scripts/find_candidates.py                  # all covered eras, with fetch
    python scripts/find_candidates.py --era 2010-2014  # just one era
    python scripts/find_candidates.py --no-fetch       # only the roster diff (fast)
    python scripts/find_candidates.py --limit 60       # probe at most N candidates/era

Coverage note: the membership list begins 1996-01-02, so 1990-1994 has no data
and 1995-1999 is approximated from the earliest snapshot (flagged 'proxy').
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from urllib.parse import quote

# Reuse catalog + Yahoo plumbing from the sibling fetcher (both are standalone).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_prices as fp  # noqa: E402

catalog = fp.catalog
ERAS = catalog.ERAS

_CONST_NAME = "S&P 500 Historical Components & Changes (Updated).csv"
CONSTITUENTS_URL = "https://raw.githubusercontent.com/fja05680/sp500/master/" + quote(_CONST_NAME)
CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache", "sp500_components.csv")

FIRST_SNAPSHOT = "1996-01-02"  # earliest date the membership list covers
MIN_MONTHS = 50  # of ~60 monthly closes in a 5y window -> "full" coverage
IDENT_MONTHS = 15  # first close must land within this many months of era start


# ---- membership list -----------------------------------------------------
def load_components(refresh=False):
    """Return [(date_str, [tickers])] sorted ascending, caching the CSV locally."""
    if refresh or not os.path.exists(CACHE_PATH):
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        req = urllib.request.Request(CONSTITUENTS_URL, headers={"User-Agent": fp.USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            text = resp.read().decode("utf-8", "replace")
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            f.write(text)
    else:
        with open(CACHE_PATH, encoding="utf-8") as f:
            text = f.read()

    rows = []
    import csv

    reader = csv.reader(text.splitlines())
    next(reader, None)  # header: date,tickers
    for row in reader:
        if len(row) < 2:
            continue
        date_str, tickers = row[0], row[1]
        rows.append((date_str, [t.strip() for t in tickers.split(",") if t.strip()]))
    rows.sort(key=lambda r: r[0])
    return rows


def roster_at(components, date_str):
    """Index membership as of date_str: the latest snapshot on or before it.

    Returns (tickers, proxied) where proxied=True means date_str predates the
    list and we fell back to the earliest available snapshot.
    """
    pick = None
    for d, tickers in components:
        if d <= date_str:
            pick = tickers
        else:
            break
    if pick is None:
        return components[0][1], True
    return pick, False


# ---- per-candidate identity-checked probe --------------------------------
def _months_between(start_iso, other_iso):
    a = datetime.fromisoformat(start_iso)
    b = datetime.fromisoformat(other_iso)
    return (b.year - a.year) * 12 + (b.month - a.month)


def probe(ticker, era):
    """Fetch a candidate's 5y return + the metadata needed to vet its identity."""
    sym = fp.SYMBOL.get(ticker, ticker)
    start, end = era.split("-")
    p1 = int(datetime(int(start), 1, 1, tzinfo=timezone.utc).timestamp())
    p2 = int(datetime(int(end), 12, 31, tzinfo=timezone.utc).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
        f"?period1={p1}&period2={p2}&interval=1mo&events=div%2Csplit"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": fp.USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
        result = data["chart"]["result"][0]
        ts = result.get("timestamp") or []
        ind = result["indicators"]
        series = ind.get("adjclose", [{}])[0].get("adjclose") or ind["quote"][0]["close"]
        pairs = [(t, float(c)) for t, c in zip(ts, series) if c and float(c) > 0]
    except Exception:  # noqa: BLE001 - network is best-effort
        return None
    if len(pairs) < 2:
        return None
    first_date = datetime.fromtimestamp(pairs[0][0], tz=timezone.utc).date().isoformat()
    return {
        "multiple": round(pairs[-1][1] / pairs[0][1], 2),
        "n": len(pairs),
        "first_date": first_date,
    }


def classify(era, info):
    """Tag a probe result so curation can trust (or distrust) the number."""
    if info is None:
        return "dead/no-data"
    era_start = f"{era.split('-')[0]}-01-01"
    if _months_between(era_start, info["first_date"]) > IDENT_MONTHS:
        return "LATE (ipo/reused?)"  # ticker didn't trade at era start under this symbol
    return "full" if info["n"] >= MIN_MONTHS else "partial"


# ---- driver --------------------------------------------------------------
def catalog_tickers(era):
    """Every ticker already in the catalog for this era, across all industries."""
    out = set()
    for eras in catalog.CATALOG.values():
        for s in eras.get(era, []):
            out.add(s["ticker"])
    return out


def run_era(components, era, fetch, limit, top):
    era_start = f"{era.split('-')[0]}-01-01"
    roster, proxied = roster_at(components, era_start)
    have = catalog_tickers(era)
    candidates = sorted(t for t in roster if t not in have)

    proxy_note = "  [proxy: list starts 1996, approximating]" if proxied else ""
    pre_note = "  [NO DATA: era predates the 1996 membership list]" if era_start < FIRST_SNAPSHOT and not roster else ""
    print(f"\n=== {era}  (window {era_start} → {era.split('-')[1]}-12-31){proxy_note}{pre_note}")
    print(f"    roster {len(roster)}  ·  already in catalog {len(have)}  ·  new candidates {len(candidates)}")

    if not fetch:
        print("    " + ", ".join(candidates[:top]) + (" …" if len(candidates) > top else ""))
        return

    probe_list = candidates[:limit] if limit else candidates
    if limit and len(candidates) > limit:
        print(f"    probing first {limit} of {len(candidates)} (use --limit 0 for all)…")

    results = []
    for t in probe_list:
        info = probe(t, era)
        results.append((t, info, classify(era, info)))
        time.sleep(0.2)

    # Rank: trustworthy + high multiple first; dead/late sink to the bottom.
    def sort_key(r):
        _, info, flag = r
        trusted = flag in ("full", "partial")
        return (trusted, info["multiple"] if info else -1)

    results.sort(key=sort_key, reverse=True)
    print(f"    {'TICKER':8}{'MULT':>8}  {'N':>3}  {'FIRST':12} FLAG")
    for t, info, flag in results[:top]:
        if info:
            print(f"    {t:8}{info['multiple']:>7}x  {info['n']:>3}  {info['first_date']:12} {flag}")
        else:
            print(f"    {t:8}{'—':>8}  {'—':>3}  {'—':12} {flag}")
    dead = sum(1 for _, info, _ in results if info is None)
    print(f"    ({len(results)} probed · {dead} dead/no-data — likely delisted, a curation seed)")


def main():
    ap = argparse.ArgumentParser(description="Find candidate S&P 500 stocks per era for the catalog.")
    ap.add_argument("--era", help="only this era key, e.g. 2010-2014")
    ap.add_argument("--no-fetch", action="store_true", help="just the roster diff, no network probes")
    ap.add_argument("--limit", type=int, default=60, help="max candidates to probe per era (0 = all)")
    ap.add_argument("--top", type=int, default=40, help="rows to print per era")
    ap.add_argument("--refresh", action="store_true", help="re-download the membership list")
    args = ap.parse_args()

    components = load_components(refresh=args.refresh)
    print(f"Loaded {len(components)} membership snapshots ({components[0][0]} → {components[-1][0]})")

    eras = [args.era] if args.era else ERAS
    for era in eras:
        run_era(components, era, fetch=not args.no_fetch, limit=args.limit, top=args.top)


if __name__ == "__main__":
    main()
