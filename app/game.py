"""Game engine: seeded (era, HQ region) rounds, five distinct industries, stake parlays through picks."""

import hashlib
import math
import random
import secrets
from datetime import date, datetime

from .config import DAY_ONE, GAME_TZ, NUM_ROUNDS, STARTING_STAKE, era_label
from .data import ERAS, INDUSTRIES, STOCKS, cell

LOCATIONS = ["Northeast", "Midwest", "South", "West"]


def _location(hq):
    """None for a foreign HQ."""
    region = (hq or {}).get("region")
    return region if region in LOCATIONS else None


# (era, location) -> stocks
_POOL = {}
for _industry in INDUSTRIES:
    for _era in ERAS:
        for _s in STOCKS[_industry][_era]:
            _loc = _location(_s.get("hq"))
            if _loc:
                _POOL.setdefault((_era, _loc), []).append(_s)


def _seed_for(day):
    h = hashlib.sha256(day.encode()).hexdigest()
    return int(h[:16], 16)


def today_str():
    return datetime.now(GAME_TZ).date().isoformat()


def day_number(day):
    return (date.fromisoformat(day) - DAY_ONE).days + 1


def practice_seed():
    """Never collides with a day string."""
    return "p-" + secrets.token_hex(6)


def _industries_available(era, loc):
    out = set()
    for s in _POOL.get((era, loc), []):
        out.update(s.get("industries", []))
    return out


def _max_matching(round_industries):
    """Max bipartite matching: rounds -> distinct industries."""
    match = {}  # industry -> round index

    def augment(r, seen):
        for ind in round_industries[r]:
            if ind in seen:
                continue
            seen.add(ind)
            if ind not in match or augment(match[ind], seen):
                match[ind] = r
                return True
        return False

    total = 0
    for r in range(len(round_industries)):
        if augment(r, set()):
            total += 1
    return total


def daily_rounds(seed=None):
    """Five rounds that admit a legal lineup. Rounds and skip alternates share one
    seeded RNG, so the daily is identical for every player."""
    seed = seed or today_str()
    rng = random.Random(_seed_for(seed))

    cells = [c for c, stocks in _POOL.items() if stocks]
    chosen = None
    for _ in range(500):
        cand = rng.sample(cells, NUM_ROUNDS)
        if _max_matching([_industries_available(e, l) for e, l in cand]) == NUM_ROUNDS:
            chosen = cand
            break
    if chosen is None:
        chosen = rng.sample(cells, NUM_ROUNDS)

    rounds = []
    for i, (era, loc) in enumerate(chosen):
        # Skip targets; their stocks load on demand via /api/cell.
        alt_era = rng.choice([e for e in ERAS if e != era])
        alt_loc = rng.choice([l for l in LOCATIONS if l != loc])
        rounds.append({
            "index": i,
            "era": era,
            "eraLabel": era_label(era),
            "location": loc,
            "altEra": alt_era,
            "altEraLabel": era_label(alt_era),
            "altLocation": alt_loc,
            "stocks": cell_stocks(era, loc),
        })
    day = today_str()
    # A resume that crossed midnight plays on as practice.
    return {"seed": seed, "day": day, "dayNumber": day_number(day),
            "mode": "daily" if seed == day else "practice", "rounds": rounds}


def cell_stocks(era, location):
    return [_stock_payload(s) for s in _POOL.get((era, location), [])]


def _legal_cells(rnd):
    """Primary, either reel's alternate, or both."""
    return {(era, loc)
            for era in (rnd["era"], rnd["altEra"])
            for loc in (rnd["location"], rnd["altLocation"])}


def _stock_payload(s):
    """Multiple hidden at pick time."""
    return {
        "ticker": s["ticker"],
        "name": s["name"],
        "sub": s.get("sub", ""),
        "hq": s.get("hq"),
        "industries": s.get("industries", []),
        "metrics": s.get("metrics", {}),
    }


def _pool_lookup(era, loc, ticker):
    for s in _POOL.get((era, loc), []):
        if s["ticker"] == ticker:
            return s
    return None


def _inv(name, photo, credit, weight=1):
    return {"name": name, "photo": "/static/investors/" + photo, "credit": "Photo: " + credit, "weight": weight}


# (min multiple, verdict, color, investors); one investor is drawn by weight.
_TIERS = [
    (100, "You 100×'d the pot. Legendary.", "gold", [_inv("Jim Simons", "simons.jpg", "Gleuschk, CC BY-SA 3.0")]),
    (56, "Elite stock-picking.", "green", [
        _inv("Warren Buffett", "buffett.jpg", "U.S. International Trade Administration, public domain", 19),
        _inv("Warren Buffett", "sanders.jpg", "Anderseidesvik, CC BY-SA 4.0"),
    ]),
    (36, "A strong book.", "blue", [_inv("Jack Bogle", "bogle.jpg", "Bill Cramer, CC BY-SA 4.0")]),
    (16, "A respectable haul.", "yellow", [
        _inv("Cathie Wood", "wood.jpg", "3948wmc, CC BY-SA 4.0"),
        _inv("Nancy Pelosi", "pelosi.jpg", "John Harrington, public domain"),
    ]),
    (2, "Barely beat the pack.", "red", [_inv("Jim Cramer", "cramer.jpg", "Bear Bull Traders, CC BY 2.0")]),
    (0, "You barely moved.", "gray", [_inv("Sam Bankman-Fried", "sbf.png", "Cointelegraph, CC BY 3.0")]),
]


def _grade(multiple, rng):
    _, verdict, color, investors = next(t for t in _TIERS if multiple >= t[0])
    inv = rng.choices(investors, weights=[i["weight"] for i in investors])[0]
    return {k: inv[k] for k in ("name", "photo", "credit")}, verdict, color


_MEDALS = {1: "gold", 2: "silver", 3: "bronze"}


def _pool_rank(era, loc, ticker):
    """(1-based rank by multiple, pool size)"""
    stocks = sorted(_POOL.get((era, loc), []), key=lambda s: s["multiple"], reverse=True)
    n = len(stocks)
    for idx, s in enumerate(stocks):
        if s["ticker"] == ticker:
            return idx + 1, n
    return n, n


def _perf_class(rank, n):
    """Pool tercile."""
    if not n:
        return "flat"
    frac = (rank - 1) / n
    if frac < 1 / 3:
        return "up"
    if frac < 2 / 3:
        return "flat"
    return "down"


def _best_lineup(cells):
    """Best distinct-industry lineup: (product, [(industry, stock)])."""
    opts = []
    for era, loc in cells:
        best = {}
        for s in _POOL.get((era, loc), []):
            for ind in s.get("industries", []):
                if ind not in best or s["multiple"] > best[ind][0]:
                    best[ind] = (s["multiple"], s)
        opts.append(best)

    best_prod, best_assign = -1.0, None

    def dfs(i, used, prod, path):
        nonlocal best_prod, best_assign
        if i == len(cells):
            if prod > best_prod:
                best_prod, best_assign = prod, list(path)
            return
        for ind, (mult, s) in opts[i].items():
            if ind in used:
                continue
            path.append((ind, s))
            dfs(i + 1, used | {ind}, prod * mult, path)
            path.pop()

    dfs(0, frozenset(), 1.0, [])
    return best_prod, best_assign or []


def _best_possible(rounds):
    """Best legal run, trying every way to spend the era and region skip."""
    base = [(r["era"], r["location"]) for r in rounds]
    spends = range(-1, len(rounds))  # -1 = unspent

    best_prod, best_assign, best_cells = -1.0, [], base
    for era_at in spends:
        for loc_at in spends:
            cells = list(base)
            if era_at >= 0:
                cells[era_at] = (rounds[era_at]["altEra"], cells[era_at][1])
            if loc_at >= 0:
                cells[loc_at] = (cells[loc_at][0], rounds[loc_at]["altLocation"])
            prod, assign = _best_lineup(cells)
            if prod > best_prod:
                best_prod, best_assign, best_cells = prod, assign, cells

    balance, legs = STARTING_STAKE, []
    for (ind, s), (era, loc), r in zip(best_assign, best_cells, rounds):
        balance *= s["multiple"]
        legs.append({
            "ticker": s["ticker"], "name": s["name"], "industry": ind,
            "eraLabel": era_label(era), "location": loc, "multiple": round(s["multiple"], 2),
            "skips": [k for k, used in (("era", era != r["era"]), ("region", loc != r["location"])) if used],
        })
    return {"multiple": round(max(best_prod, 0.0), 2), "finalValue": round(balance, 2), "legs": legs}


def score(picks, seed=None):
    """picks: [{era, location, ticker, industry}]"""
    data = daily_rounds(seed)
    rounds = data["rounds"]
    if len(picks) != NUM_ROUNDS:
        raise ValueError(f"Expected {NUM_ROUNDS} picks, got {len(picks)}")

    used_industries = set()
    legs = []
    balance = STARTING_STAKE
    for i, pick in enumerate(picks):
        rnd = rounds[i]
        era, loc = pick.get("era"), pick.get("location")
        if (era, loc) not in _legal_cells(rnd):
            raise ValueError(f"Round {i}: illegal cell {era} / {loc}")

        stock = _pool_lookup(era, loc, pick.get("ticker"))
        if not stock:
            raise ValueError(f"Round {i}: unknown stock {pick.get('ticker')}")

        industry = pick.get("industry")
        if industry not in stock.get("industries", []):
            raise ValueError(f"Round {i}: {stock['ticker']} is not in industry {industry}")
        if industry in used_industries:
            raise ValueError(f"Round {i}: industry {industry} already used (one per industry)")
        used_industries.add(industry)

        invested = balance
        balance = balance * stock["multiple"]
        rank, pool_size = _pool_rank(era, loc, stock["ticker"])
        legs.append({
            "ticker": stock["ticker"],
            "name": stock["name"],
            "industry": industry,
            "era": era,
            "eraLabel": era_label(era),
            "location": loc,
            "hq": stock.get("hq"),
            "metrics": stock.get("metrics", {}),
            "multiple": round(stock["multiple"], 2),
            "invested": round(invested, 2),
            "finalValue": round(balance, 2),
            "gainPct": round((stock["multiple"] - 1) * 100, 1),
            "rank": rank,
            "cellSize": pool_size,
            "medal": _MEDALS.get(rank),
            "perf": _perf_class(rank, pool_size),
        })

    final_value = balance
    multiple = final_value / STARTING_STAKE
    # Seeded by game and picks, so a result always shows the same investor.
    tickers = ",".join(l["ticker"] for l in legs)
    investor, verdict, color = _grade(multiple, random.Random(_seed_for(f"{data['seed']}|{tickers}")))

    best = max(legs, key=lambda l: l["multiple"])
    worst = min(legs, key=lambda l: l["multiple"])

    best_possible = _best_possible(rounds)
    # Log scale; losing runs floor at 0.
    best_mult = best_possible["multiple"]
    captured = round(math.log(multiple) / math.log(best_mult) * 100, 1) if multiple > 1 and best_mult > 1 else 0.0

    return {
        "day": data["day"],
        "dayNumber": data["dayNumber"],
        "mode": data["mode"],
        "seed": data["seed"],
        "legs": legs,
        "invested": STARTING_STAKE,
        "finalValue": round(final_value, 2),
        "multiple": round(multiple, 2),
        "gainPct": round((multiple - 1) * 100, 1),
        "investor": investor,
        "verdict": verdict,
        "gradeColor": color,
        "bestPick": {"ticker": best["ticker"], "name": best["name"], "multiple": best["multiple"]},
        "weakness": {"ticker": worst["ticker"], "name": worst["name"], "multiple": worst["multiple"]},
        "best": best_possible,
        "capturedPct": captured,
    }


def learn_data():
    """Learning mode: every cell with returns revealed, best first."""
    out = {}
    for industry in INDUSTRIES:
        out[industry] = {}
        for era in ERAS:
            rows = [
                {
                    "ticker": s["ticker"],
                    "name": s["name"],
                    "sub": s.get("sub", ""),
                    "hq": s.get("hq"),
                    "metrics": s.get("metrics", {}),
                    "multiple": round(s["multiple"], 2),
                    "gainPct": round((s["multiple"] - 1) * 100, 1),
                }
                for s in cell(industry, era)
            ]
            rows.sort(key=lambda r: r["multiple"], reverse=True)
            out[industry][era] = rows
    return {"eras": ERAS, "industries": INDUSTRIES, "stocks": out}
