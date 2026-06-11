#!/usr/bin/env python3
"""Cache-first historical-returns collector for 100xPortfolio.

A 5-year era's total return is immutable once the window has closed, so we fetch
each ``(era, ticker)`` multiple exactly once and keep it forever in a tracked
cache (``scripts/data/returns_cache.json``). Only genuine cache misses touch the
network, and the only provider is **Yahoo's public chart JSON** — split +
dividend adjusted, no API key, no extra dependencies.

This replaces the old multi-provider strategy: Stooq 404s from many networks and
yfinance isn't always installed, so both were dropped. Yahoo is the one that
reliably works, and because results are cached durably we essentially never
re-pull a completed era.

    from collect import multiple, collect
    multiple("AAPL", "2010-2014")          # cache hit, or one Yahoo call then cached
    collect([("NVDA", "2020-2024"), ...])  # bulk, resumable, flushes as it goes
"""

import json
import os
import time
import urllib.request
from datetime import datetime, timezone

CACHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "returns_cache.json")
USER_AGENT = "Mozilla/5.0 (100xPortfolio collector)"

# Display ticker -> Yahoo symbol when they differ.
SYMBOL = {"BRK": "BRK-B", "FB": "META"}

_cache = None


def _load():
    global _cache
    if _cache is None:
        try:
            with open(CACHE_PATH, encoding="utf-8") as f:
                _cache = json.load(f)
        except (OSError, json.JSONDecodeError):
            _cache = {}
    return _cache


def save():
    """Persist the cache, sorted, for stable diffs."""
    c = _load()
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(c.items())), f, indent=0)
        f.write("\n")


def yahoo_multiple(ticker, era):
    """One Yahoo chart call -> split/dividend-adjusted 5y multiple, or None."""
    sym = SYMBOL.get(ticker, ticker)
    start, end = era.split("-")
    p1 = int(datetime(int(start), 1, 1, tzinfo=timezone.utc).timestamp())
    p2 = int(datetime(int(end), 12, 31, tzinfo=timezone.utc).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
        f"?period1={p1}&period2={p2}&interval=1mo&events=div%2Csplit"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.load(resp)
        ind = data["chart"]["result"][0]["indicators"]
        series = ind.get("adjclose", [{}])[0].get("adjclose") or ind["quote"][0]["close"]
        closes = [float(x) for x in series if x and float(x) > 0]
    except Exception:  # noqa: BLE001 - network is best-effort
        return None
    if len(closes) < 2:
        return None
    return round(closes[-1] / closes[0], 2)


def multiple(ticker, era, refetch=False):
    """Cache-first 5y multiple for (ticker, era). Network only on a miss.

    Returns the multiple, or None for delisted/no-data names (which is itself
    cached so we don't keep retrying them).
    """
    c = _load()
    key = f"{era}|{ticker}"
    if not refetch and key in c:
        return c[key]
    c[key] = yahoo_multiple(ticker, era)
    return c[key]


def collect(pairs, sleep=0.15, flush_every=40):
    """Bulk-collect (ticker, era) pairs, caching + flushing as we go.

    Resumable: anything already cached is skipped, so a re-run after an
    interruption costs nothing for what's done. Returns (fetched, cache_hits).
    """
    c = _load()
    fetched = hits = 0
    for ticker, era in pairs:
        key = f"{era}|{ticker}"
        if key in c:
            hits += 1
            continue
        c[key] = yahoo_multiple(ticker, era)
        fetched += 1
        if fetched % flush_every == 0:
            save()
        time.sleep(sleep)
    save()
    return fetched, hits


if __name__ == "__main__":
    c = _load()
    have = sum(1 for v in c.values() if v is not None)
    print(f"{CACHE_PATH}: {len(c)} keys cached ({have} with data, {len(c) - have} dead/no-data)")
