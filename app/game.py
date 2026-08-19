"""Game engine: daily-seeded (era, HQ-location) spins + one-per-industry scoring.

Each round is a combination of an **era** and a **headquarters location** (a US
region for now). You pick one company headquartered there, and across your five
picks you must field five **distinct industries** — a lineup, one per position,
like a starting five. Multi-industry names (Amazon = Tech or Consumer Disc.) are
flexible and can fill either open slot. The stake still rolls from one pick into
the next (parlay); scoring is unchanged.
"""

import hashlib
import random
import secrets
from datetime import date, datetime

from .config import DAY_ONE, GAME_TZ, NUM_ROUNDS, STARTING_STAKE, era_label
from .data import ERAS, INDUSTRIES, STOCKS, cell

# HQ locations a round can land on. Regions keep every (era, location) pool
# populous; finer state-level buckets are a later distribution pass.
LOCATIONS = ["Northeast", "Midwest", "South", "West"]


def _location(hq):
    """A stock's round-location, or None if it can't anchor a round (foreign HQ)."""
    region = (hq or {}).get("region")
    return region if region in LOCATIONS else None


# (era, location) -> [stock dicts], built once from the universe. Each stock keeps
# its full `industries` list so the lineup can honor multi-industry names.
_POOL = {}
for _industry in INDUSTRIES:
    for _era in ERAS:
        for _s in STOCKS[_industry][_era]:
            _loc = _location(_s.get("hq"))
            if _loc:
                _POOL.setdefault((_era, _loc), []).append(_s)


def _seed_for(day):
    """Stable integer seed so everyone in the world gets the same spins on a given day."""
    h = hashlib.sha256(day.encode()).hexdigest()
    return int(h[:16], 16)


def today_str():
    """Today's date in Mountain time — the board rolls at midnight Denver, not UTC."""
    return datetime.now(GAME_TZ).date().isoformat()


def day_number(day):
    """1-based daily number for a day string, counting from DAY_ONE."""
    return (date.fromisoformat(day) - DAY_ONE).days + 1


def practice_seed():
    """A fresh random seed for a practice board. Never collides with a day string."""
    return "p-" + secrets.token_hex(6)


# --- lineup feasibility (a system of distinct industry representatives) --------
def _industries_available(era, loc):
    out = set()
    for s in _POOL.get((era, loc), []):
        out.update(s.get("industries", []))
    return out


def _max_matching(round_industries):
    """Max bipartite matching rounds -> distinct industries (augmenting paths)."""
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
    """Five (era, location) rounds from a seed, guaranteed to admit a legal lineup.

    No seed -> today's shared daily spin; a random seed -> a practice roll. Both
    the rounds and each round's two skip alternates come off this one seeded RNG,
    so the daily board — skips included — is identical for every player. Each
    round bundles its full pool of pickable companies (returns stripped) so the
    client never re-fetches.
    """
    seed = seed or today_str()
    rng = random.Random(_seed_for(seed))

    cells = [c for c, stocks in _POOL.items() if stocks]
    chosen = None
    for _ in range(500):
        cand = rng.sample(cells, NUM_ROUNDS)
        if _max_matching([_industries_available(e, l) for e, l in cand]) == NUM_ROUNDS:
            chosen = cand
            break
    if chosen is None:  # extraordinarily unlikely with region-sized pools
        chosen = rng.sample(cells, NUM_ROUNDS)

    rounds = []
    for i, (era, loc) in enumerate(chosen):
        # The two cells this round's single skip can re-roll into. Their stock
        # lists are fetched on demand (/api/cell) so the daily payload stays
        # one cell per round instead of three.
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
    # A seed equal to today's date is the daily; anything else (including a
    # yesterday resume that crossed midnight) plays on as practice.
    return {"seed": seed, "day": day, "dayNumber": day_number(day),
            "mode": "daily" if seed == day else "practice", "rounds": rounds}


def cell_stocks(era, location):
    """Pick-time payload for one (era, location) cell; what a skip re-rolls into."""
    return [_stock_payload(s) for s in _POOL.get((era, location), [])]


def _legal_cells(rnd):
    """The cells a pick may come from. Each reel has its own skip, so a round can be
    primary, era-skipped, region-skipped, or (if both are spent here) both."""
    return {(era, loc)
            for era in (rnd["era"], rnd["altEra"])
            for loc in (rnd["location"], rnd["altLocation"])}


def _stock_payload(s):
    """Pick-time payload: the outcome multiple is hidden; entry metrics are shown."""
    return {
        "ticker": s["ticker"],
        "name": s["name"],
        "sub": s.get("sub", ""),
        "hq": s.get("hq"),
        "industries": s.get("industries", []),
        "metrics": s.get("metrics", {}),  # entry P/E · price · dividend (known at pick time)
    }


def _pool_lookup(era, loc, ticker):
    for s in _POOL.get((era, loc), []):
        if s["ticker"] == ticker:
            return s
    return None


def _grade(multiple):
    # Tiers by total portfolio multiple. S is the 100x dream; F is the floor.
    if multiple >= 100:
        return ("S", "You 100×'d the pot. Legendary.", "gold")
    if multiple >= 56:
        return ("A", "Elite stock-picking.", "green")
    if multiple >= 36:
        return ("B", "A strong book.", "blue")
    if multiple >= 16:
        return ("C", "A respectable haul.", "yellow")
    if multiple >= 2:
        return ("D", "Barely beat the pack.", "red")
    return ("F", "You barely moved.", "gray")


# Medal for a top-3 finish within an (era, location) pool.
_MEDALS = {1: "gold", 2: "silver", 3: "bronze"}


def _pool_rank(era, loc, ticker):
    """1-based rank of `ticker` within its (era, location) pool by return + pool size."""
    stocks = sorted(_POOL.get((era, loc), []), key=lambda s: s["multiple"], reverse=True)
    n = len(stocks)
    for idx, s in enumerate(stocks):
        if s["ticker"] == ticker:
            return idx + 1, n
    return n, n  # shouldn't happen — the pick was validated against this pool


def _perf_class(rank, n):
    """Tercile of a pick within its pool: top -> up (green), mid -> flat, worst -> down (red)."""
    if not n:
        return "flat"
    frac = (rank - 1) / n
    if frac < 1 / 3:
        return "up"
    if frac < 2 / 3:
        return "flat"
    return "down"


def _best_lineup(cells):
    """(product, [(industry, stock)]) for the best distinct-industry lineup over these
    cells. Reduces each cell to its best stock per industry, then searches assignments."""
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
    """Best legal run on these spins, played under the same rules as the player: one
    stock per round, five distinct industries, one era skip and one region skip. So it
    searches every way of spending those two charges, including both on one round."""
    base = [(r["era"], r["location"]) for r in rounds]
    spends = range(-1, len(rounds))  # -1 = never spend this skip

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
    for (ind, s), (era, _loc) in zip(best_assign, best_cells):
        balance *= s["multiple"]
        legs.append({
            "ticker": s["ticker"], "name": s["name"], "industry": ind,
            "eraLabel": era_label(era), "multiple": round(s["multiple"], 2),
        })
    return {"multiple": round(max(best_prod, 0.0), 2), "finalValue": round(balance, 2), "legs": legs}


def score(picks, seed=None):
    """Score a finished game.

    `picks` is a list of {era, location, ticker, industry}. Validates each pick
    was reachable in its round and that the five industries are distinct (the
    one-per-industry lineup rule), then rolls the stake through them.
    """
    data = daily_rounds(seed)
    rounds = data["rounds"]
    if len(picks) != NUM_ROUNDS:
        raise ValueError(f"Expected {NUM_ROUNDS} picks, got {len(picks)}")

    used_industries = set()
    legs = []
    balance = STARTING_STAKE  # rolls from one pick into the next
    for i, pick in enumerate(picks):
        rnd = rounds[i]
        era, loc = pick.get("era"), pick.get("location")
        if (era, loc) not in _legal_cells(rnd):  # primary or a skipped-into alternate
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
        balance = balance * stock["multiple"]  # whole pot rides on this pick
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
            # Standing within the (era, location) pool the player was dealt.
            "rank": rank,
            "cellSize": pool_size,
            "medal": _MEDALS.get(rank),  # gold/silver/bronze, else None
            "perf": _perf_class(rank, pool_size),  # up/flat/down (green/yellow/red)
        })

    final_value = balance
    multiple = final_value / STARTING_STAKE  # = product of every pick's multiple
    grade, verdict, color = _grade(multiple)

    best = max(legs, key=lambda l: l["multiple"])
    worst = min(legs, key=lambda l: l["multiple"])

    best_possible = _best_possible(rounds)
    captured = round(final_value / best_possible["finalValue"] * 100, 1) if best_possible["finalValue"] else 0.0

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
        "grade": grade,
        "verdict": verdict,
        "gradeColor": color,
        "bestPick": {"ticker": best["ticker"], "name": best["name"], "multiple": best["multiple"]},
        "weakness": {"ticker": worst["ticker"], "name": worst["name"], "multiple": worst["multiple"]},
        "best": best_possible,
        "capturedPct": captured,
    }


def learn_data():
    """Full universe with returns revealed, for the (non-game) learning mode.

    Every (industry, era) cell's stocks with their 5-year return %, sorted best
    to worst — a study view, not a guessing game, so the numbers are shown.
    """
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
