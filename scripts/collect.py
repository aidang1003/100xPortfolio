#!/usr/bin/env python3
"""Monthly price-series collector for 100xPortfolio.

We store the full monthly adjusted-close **series** per ticker in
``scripts/data/prices.json`` and compute any window's multiple on the fly
(``multiple(ticker, "2010-2014")`` = close at 2014-12 / close at 2010-01). A
closed era's prices never change, so each ticker is fetched once from Yahoo's
public chart JSON (split+dividend adjusted, no key) and kept forever.

    from collect import multiple, series
    multiple("AAPL", "2010-2014")      # on-the-fly from the stored series
    series("NVDA")                     # {"start": "1999-01", "closes": [...]}
"""

import json
import os
import urllib.request
from datetime import datetime, timezone

from common import SYMBOL, USER_AGENT

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
PRICES_PATH = os.path.join(DATA_DIR, "prices.json")


# --- year-month index helpers --------------------------------------------
def _ym_to_i(ym):
    """'YYYY-MM' -> absolute month index (year*12 + month-1)."""
    y, m = ym.split("-")
    return int(y) * 12 + int(m) - 1


def _i_to_ym(i):
    return f"{i // 12:04d}-{i % 12 + 1:02d}"


def _era_bounds(era):
    """'YYYY-YYYY' -> ('startYYYY-01', 'endYYYY-12')."""
    start, end = era.split("-")
    return f"{start}-01", f"{end}-12"


# --- monthly price-series store -------------------------------------------
_prices = None


def _load_prices():
    global _prices
    if _prices is None:
        try:
            with open(PRICES_PATH, encoding="utf-8") as f:
                _prices = json.load(f)
        except (OSError, json.JSONDecodeError):
            _prices = {}
    return _prices


def save_prices():
    """Persist the price store, sorted by ticker, for stable diffs."""
    p = _load_prices()
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PRICES_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(p.items())), f, separators=(",", ":"))
        f.write("\n")


def fetch_series(ticker):
    """One Yahoo call -> full monthly adj-close series, or None.

    Returns {"start": "YYYY-MM", "closes": [float|None, ...]} where ``closes``
    is dense monthly from ``start`` (None fills any missing month).
    """
    sym = SYMBOL.get(ticker, ticker)
    p1 = int(datetime(1970, 1, 1, tzinfo=timezone.utc).timestamp())
    p2 = int(datetime.now(timezone.utc).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
        f"?period1={p1}&period2={p2}&interval=1mo&events=div%2Csplit"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        result = data["chart"]["result"][0]
        ts = result.get("timestamp") or []
        ind = result["indicators"]
        adj = ind.get("adjclose", [{}])[0].get("adjclose") or ind["quote"][0]["close"]
    except Exception:  # noqa: BLE001 - network is best-effort
        return None

    by_month = {}
    for t, c in zip(ts, adj):
        if c is None or float(c) <= 0:
            continue
        ym = datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m")
        by_month[ym] = round(float(c), 4)
    if len(by_month) < 2:
        return None

    lo, hi = _ym_to_i(min(by_month)), _ym_to_i(max(by_month))
    closes = [by_month.get(_i_to_ym(i)) for i in range(lo, hi + 1)]
    return {"start": _i_to_ym(lo), "closes": closes}


def series(ticker, refetch=False):
    """Cache-first monthly series for a ticker. Network only on a miss.

    A None result (delisted / no data) is cached so we don't keep retrying.
    """
    p = _load_prices()
    if not refetch and ticker in p:
        return p[ticker]
    p[ticker] = fetch_series(ticker)
    return p[ticker]


def price_at(ticker, ym, direction="at"):
    """Adjusted close for `ticker` near month `ym`.

    direction: 'after' = first available at/after ym, 'before' = last available
    at/before ym, 'at' = nearest either way. Returns None if unavailable.
    """
    s = _load_prices().get(ticker)
    if not s:
        return None
    closes = s["closes"]
    n = len(closes)
    idx = _ym_to_i(ym) - _ym_to_i(s["start"])
    if direction == "after":
        rng = range(max(0, idx), n)
    elif direction == "before":
        rng = range(min(n - 1, idx), -1, -1)
    else:
        order = sorted(range(n), key=lambda i: abs(i - idx))
        rng = order
    for i in rng:
        if 0 <= i < n and closes[i] is not None:
            return closes[i]
    return None


def multiple(ticker, era=None, start=None, end=None):
    """Window total-return multiple for a ticker, computed from the series.

    Call as multiple(t, "2010-2014") or multiple(t, start="2010-01", end="2014-12").
    Returns None when the series doesn't cover the window.
    """
    if era is not None:
        start, end = _era_bounds(era)
    if ticker not in _load_prices():
        series(ticker)
    a = price_at(ticker, start, "after")
    b = price_at(ticker, end, "before")
    return round(b / a, 2) if a and b else None


if __name__ == "__main__":
    p = _load_prices()
    have = sum(1 for v in p.values() if v)
    print(f"{PRICES_PATH}: {len(p)} tickers ({have} with series, {len(p) - have} dead/no-data)")
