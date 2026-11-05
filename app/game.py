"""Game engine: seeded (era, HQ region) rounds, five distinct industries, stake parlays through picks."""

import hashlib
import random
import secrets
from datetime import date, datetime

from .config import DAY_ONE, ERA_YEARS, GAME_TZ, NUM_ROUNDS, STARTING_STAKE, era_label
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


def _annual_pct(multiple):
    """Compound yearly return over the full run (every round is one era)."""
    return round((max(multiple, 0) ** (1 / (NUM_ROUNDS * ERA_YEARS)) - 1) * 100, 1)


# A round scores 100 at the 5th root of 100, the per-pick pace for a 100x pot.
ROUND_CAP = 100 ** (1 / NUM_ROUNDS)
MAX_GAME_SCORE = 100 * NUM_ROUNDS


def _curve(multiple):
    """S-curve fitted so 1x scores 10 and 1.5x scores 50 once rescaled."""
    return 1 / (1 + (1.54 / multiple) ** 5.28) if multiple > 0 else 0.0


def round_score(multiple):
    """0-100. Only a wipeout scores 0; a loss scales down from 10 at flat; 100 at ROUND_CAP and above."""
    if multiple <= 0:
        return 0
    if multiple < 1:
        return max(1, round(10 * multiple))
    return round(min(100, 100 * _curve(multiple) / _curve(ROUND_CAP)))


def _inv(name, photo, credit, weight=1):
    return {"name": name, "photo": "/static/investors/" + photo, "credit": "Photo: " + credit,
            "wiki": "https://en.wikipedia.org/wiki/" + name.replace(" ", "_"), "weight": weight}


# Best first, ranked by lifetime return; one investor is drawn by weight.
# Each rung gets an equal band of the game score, so the list length sets the bands.
_TIERS = [
    ("Legendary stock-picking.", "gold", [_inv("Jim Simons", "simons.jpg", "Gleuschk, CC BY-SA 3.0")]),
    ("Elite stock-picking.", "green", [
        _inv("Warren Buffett", "buffett.jpg", "U.S. International Trade Administration, public domain", 19),
        _inv("Warren Buffett", "sanders.jpg", "Anderseidesvik, CC BY-SA 4.0"),
    ]),
    ("A strong book.", "blue", [_inv("Jack Bogle", "bogle.jpg", "Bill Cramer, CC BY-SA 4.0")]),
    ("Well-timed trades.", "yellow", [_inv("Nancy Pelosi", "pelosi.jpg", "John Harrington, public domain")]),
    ("A respectable haul.", "orange", [_inv("Cathie Wood", "wood.jpg", "3948wmc, CC BY-SA 4.0")]),
    ("Barely beat the pack.", "red", [_inv("Jim Cramer", "cramer.jpg", "Bear Bull Traders, CC BY 2.0")]),
    ("You barely moved.", "gray", [_inv("Sam Bankman-Fried", "sbf.png", "Cointelegraph, CC BY 3.0")]),
]


def _tier_floor(i):
    """Lowest game score for rung i (0 = top)."""
    n = len(_TIERS)
    return MAX_GAME_SCORE * (n - 1 - i) / n


def _grade(game_score, rng):
    verdict, color, investors = next(t for i, t in enumerate(_TIERS) if game_score >= _tier_floor(i))
    inv = rng.choices(investors, weights=[i["weight"] for i in investors])[0]
    return {k: inv[k] for k in ("name", "photo", "credit", "wiki")}, verdict, color


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


def _outcome(era, loc, stock):
    """What a pick earned: return, round score, and rank in its pool."""
    rank, pool_size = _pool_rank(era, loc, stock["ticker"])
    return {
        "ticker": stock["ticker"],
        "multiple": round(stock["multiple"], 2),
        "gainPct": round((stock["multiple"] - 1) * 100, 1),
        "score": round_score(stock["multiple"]),
        "rank": rank,
        "cellSize": pool_size,
        "medal": _MEDALS.get(rank),
        "perf": _perf_class(rank, pool_size),
    }


def reveal(era, loc, ticker):
    """One pick's outcome, shown on the card right after it's made."""
    stock = _pool_lookup(era, loc, ticker)
    if not stock:
        raise ValueError(f"Unknown stock {ticker} in {era} / {loc}")
    return _outcome(era, loc, stock)


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

    legs = []
    for (ind, s), (era, loc), r in zip(best_assign, best_cells, rounds):
        legs.append({
            "ticker": s["ticker"], "name": s["name"], "industry": ind,
            "eraLabel": era_label(era), "location": loc, "multiple": round(s["multiple"], 2),
            "skips": [k for k, used in (("era", era != r["era"]), ("region", loc != r["location"])) if used],
        })
    return {"annualPct": _annual_pct(best_prod), "legs": legs}


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
        legs.append({
            "name": stock["name"],
            "industry": industry,
            "era": era,
            "eraLabel": era_label(era),
            "location": loc,
            "hq": stock.get("hq"),
            "metrics": stock.get("metrics", {}),
            "invested": round(invested, 2),
            "finalValue": round(balance, 2),
            **_outcome(era, loc, stock),
        })

    final_value = balance
    multiple = final_value / STARTING_STAKE
    # Seeded by game and picks, so a result always shows the same investor.
    tickers = ",".join(l["ticker"] for l in legs)
    game_score = sum(l["score"] for l in legs)
    investor, verdict, color = _grade(game_score, random.Random(_seed_for(f"{data['seed']}|{tickers}")))

    best = max(legs, key=lambda l: l["multiple"])
    worst = min(legs, key=lambda l: l["multiple"])

    best_possible = _best_possible(rounds)
    # Ratio of the annual rates shown on screen; losing runs floor at 0.
    annual, best_annual = _annual_pct(multiple), best_possible["annualPct"]
    captured = round(max(annual, 0) / best_annual * 100, 1) if best_annual > 0 else 0.0

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
        "annualPct": annual,
        "gameScore": game_score,
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
