#!/usr/bin/env python3
"""Build app/fundamentals.json: {ticker: {era: {price, divYield?, pe?}}} at era start.

price: nominal Yahoo close. divYield: TTM dividends / price, %. pe: price / latest
as-filed annual EPS from SEC EDGAR (~2009+, so absent before the 2010 era).
Resumable: skips tickers already in the output.
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common  # noqa: E402

APP = os.path.join(os.path.dirname(HERE), "app")
COMPANIES = os.path.join(APP, "companies.json")
OUT_PATH = os.path.join(APP, "fundamentals.json")
ERAS = common.ERAS
SEC_UA = "100xPortfolio research aidang1003@gmail.com"  # SEC requires a contact UA


def _era_start_ts(era):
    y = int(era.split("-")[0])
    return int(datetime(y, 1, 1, tzinfo=timezone.utc).timestamp()), y


def yahoo_price_and_divs(ticker):
    """Monthly closes (split-adjusted to today) + dividend and split events."""
    sym = common.SYMBOL.get(ticker, ticker)
    p1 = int(datetime(1970, 1, 1, tzinfo=timezone.utc).timestamp())
    p2 = int(datetime.now(timezone.utc).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
        f"?period1={p1}&period2={p2}&interval=1mo&events=div%2Csplit"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": common.USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.load(resp)
        res = data["chart"]["result"][0]
        ts = res.get("timestamp") or []
        closes = res["indicators"]["quote"][0]["close"]
        events = res.get("events", {})
        divs = [(int(k), float(v["amount"])) for k, v in events.get("dividends", {}).items()]
        splits = [(int(k), float(v["numerator"]) / float(v["denominator"]))
                  for k, v in events.get("splits", {}).items() if float(v.get("denominator", 0))]
    except Exception:  # noqa: BLE001
        return None
    months = [(t, float(c)) for t, c in zip(ts, closes) if c and float(c) > 0]
    if len(months) < 2:
        return None
    return {"months": months, "divs": sorted(divs), "splits": sorted(splits)}


def _cum_split_after(splits, ts):
    """Split-adjusted price at `ts` x this = nominal price."""
    factor = 1.0
    for st, ratio in splits:
        if st > ts:
            factor *= ratio
    return factor


def edgar_annual_eps(cik):
    """{fiscal-year end: EPS}, earliest 10-K filing per end so EPS stays nominal."""
    for concept in ("EarningsPerShareDiluted", "EarningsPerShareBasic"):
        url = f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik:010d}/us-gaap/{concept}.json"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": SEC_UA})
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.load(resp)
        except Exception:  # noqa: BLE001
            continue
        by_end = {}  # end -> (filed, val)
        for u in data.get("units", {}).get("USD/shares", []):
            if not (u.get("form", "").startswith("10-K") and u.get("val") is not None and u.get("start")):
                continue
            # 10-Ks also tag Q4 EPS as FY.
            span = (datetime.fromisoformat(u["end"]) - datetime.fromisoformat(u["start"])).days
            if span < 300:
                continue
            prev = by_end.get(u["end"])
            if prev is None or u.get("filed", "9999") < prev[0]:
                by_end[u["end"]] = (u.get("filed", "9999"), float(u["val"]))
        if by_end:
            return {end: v for end, (_, v) in by_end.items()}
    return {}


def fundamentals_for(ticker, cik):
    yd = yahoo_price_and_divs(ticker)
    if not yd:
        return {}
    months, divs, splits = yd["months"], yd["divs"], yd["splits"]
    eps = edgar_annual_eps(cik) if cik else {}
    eps_ends = sorted(eps)

    out = {}
    for era in ERAS:
        start_ts, start_y = _era_start_ts(era)
        entry = next(((t, c) for t, c in months if t >= start_ts), None)
        if entry is None:
            continue
        entry_ts, adj_close = entry
        nominal = adj_close * _cum_split_after(splits, entry_ts)
        row = {"price": round(nominal, 2)}
        # Both split-adjusted, so the basis cancels.
        yr = 365 * 24 * 3600
        ttm = sum(a for t, a in divs if start_ts - yr <= t < start_ts)
        if ttm > 0:
            row["divYield"] = round(ttm / adj_close * 100, 2)
        prior = [e for e in eps_ends if e < f"{start_y}-01-01"]
        if prior and eps[prior[-1]] > 0:
            row["pe"] = round(nominal / eps[prior[-1]], 1)
        out[era] = row
    return out


def _load_out():
    try:
        with open(OUT_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def main():
    companies = json.load(open(COMPANIES, encoding="utf-8"))
    out = _load_out()
    done = 0
    for i, (t, co) in enumerate(sorted(companies.items())):
        if t in out:
            continue
        out[t] = fundamentals_for(t, co.get("cik"))
        done += 1
        if done % 20 == 0:
            with open(OUT_PATH, "w", encoding="utf-8") as f:
                json.dump(out, f, separators=(",", ":"))
                f.write("\n")
            print(f"  {i + 1}/{len(companies)} … {t}")
        time.sleep(0.2)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(out.items())), f, separators=(",", ":"))
        f.write("\n")
    pe = sum(1 for c in out.values() for e in c.values() if "pe" in e)
    dy = sum(1 for c in out.values() for e in c.values() if "divYield" in e)
    print(f"Wrote {OUT_PATH}: {len(out)} tickers, {pe} cells with P/E, {dy} with div yield")


if __name__ == "__main__":
    main()
