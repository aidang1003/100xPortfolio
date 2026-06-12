"""Game engine: daily-seeded spins, skip rolls, and portfolio scoring."""

import hashlib
import random
from datetime import date

from .data import ERAS, INDUSTRIES, STOCKS, cell

NUM_ROUNDS = 5
STARTING_STAKE = 10_000  # dollars you start with; rolls from one pick into the next (100x = $1M)


def era_label(era):
    """Display label for an era: a clean 5-year span (e.g. '2020-2024' -> '2020-2025').

    The underlying key still drives the data window; this only changes how the
    span reads to the player.
    """
    start = era.split("-")[0]
    return f"{start}-{int(start) + 5}"


def _seed_for(day):
    """Stable integer seed so everyone in the world gets the same spins on a given day."""
    h = hashlib.sha256(day.encode()).hexdigest()
    return int(h[:16], 16)


def today_str():
    return date.today().isoformat()


def daily_rounds(seed=None):
    """Generate a set of 5 rounds from a seed.

    With no seed it uses today's date, so everyone in the world gets the same
    daily spin. A replay passes a random seed to get a fresh, different set.

    Each round carries a primary (era, industry) plus one alternate era and one
    alternate industry the player can swap to with their single era/industry skip.
    Every relevant cell's stock list is bundled so the client never re-fetches.
    """
    seed = seed or today_str()
    rng = random.Random(_seed_for(seed))

    rounds = []
    used = set()
    while len(rounds) < NUM_ROUNDS:
        era = rng.choice(ERAS)
        industry = rng.choice(INDUSTRIES)
        if (era, industry) in used:
            continue
        used.add((era, industry))

        alt_era = rng.choice([e for e in ERAS if e != era])
        alt_industry = rng.choice([i for i in INDUSTRIES if i != industry])

        rounds.append(
            {
                "index": len(rounds),
                "era": era,
                "eraLabel": era_label(era),
                "industry": industry,
                "altEra": alt_era,
                "altEraLabel": era_label(alt_era),
                "altIndustry": alt_industry,
                "cells": {
                    "primary": _cell_payload(industry, era),
                    "altEra": _cell_payload(industry, alt_era),
                    "altIndustry": _cell_payload(alt_industry, era),
                },
            }
        )
    return {"seed": seed, "day": today_str(), "rounds": rounds}


def _cell_payload(industry, era):
    return {
        "industry": industry,
        "era": era,
        "eraLabel": era_label(era),
        "stocks": [
            {
                "ticker": s["ticker"],
                "name": s["name"],
                "sub": s.get("sub", ""),
                "blurb": s.get("blurb", ""),
            }
            for s in cell(industry, era)
        ],
    }


def _lookup(industry, era, ticker):
    for s in STOCKS.get(industry, {}).get(era, []):
        if s["ticker"] == ticker:
            return s
    return None


def _grade(multiple):
    # Tiers by total portfolio multiple. S is the 100x dream; F is the floor.
    if multiple >= 100:
        return ("S", "Legendary — you 100×'d the pot", "gold")
    if multiple >= 56:
        return ("A", "Elite stock-picking", "green")
    if multiple >= 36:
        return ("B", "Strong portfolio", "blue")
    if multiple >= 16:
        return ("C", "Solid — a respectable haul", "yellow")
    if multiple >= 2:
        return ("D", "Modest — barely beat the pack", "red")
    return ("F", "Brutal — you barely moved", "red")


# Medal for a top-3 finish within an (industry, era) cell.
_MEDALS = {1: "gold", 2: "silver", 3: "bronze"}


def _cell_rank(industry, era, ticker):
    """1-based rank of `ticker` within its cell by return (best = 1) + cell size."""
    stocks = sorted(cell(industry, era), key=lambda s: s["multiple"], reverse=True)
    n = len(stocks)
    for idx, s in enumerate(stocks):
        if s["ticker"] == ticker:
            return idx + 1, n
    return n, n  # shouldn't happen — the pick was validated against this cell


def _perf_class(rank, n):
    """Tercile of a pick within its cell, as a leg-mult color class:
    top third -> green (up), middle -> yellow (flat), worst -> red (down)."""
    if not n:
        return "flat"
    frac = (rank - 1) / n
    if frac < 1 / 3:
        return "up"
    if frac < 2 / 3:
        return "flat"
    return "down"


def _cell_best(industry, era):
    """Highest-multiple stock in a cell (a 0x landmine never wins a max)."""
    stocks = STOCKS.get(industry, {}).get(era, [])
    return max(stocks, key=lambda s: s["multiple"]) if stocks else None


def _best_possible(rounds):
    """The best achievable run on these spins, using the two skips optimally.

    Each round you can pick from the primary cell, or swap to the alt-era or
    alt-industry cell — but the era skip and industry skip are each usable once
    for the whole game, and a round can use at most one (you pick one cell). We
    brute-force the (era-skip round, industry-skip round) assignment and keep the
    product-maximising path.
    """
    n = len(rounds)
    P = [_cell_best(r["industry"], r["era"]) for r in rounds]
    AE = [_cell_best(r["industry"], r["altEra"]) for r in rounds]
    AI = [_cell_best(r["altIndustry"], r["era"]) for r in rounds]

    best_prod, best_path = -1.0, None
    choices = [None] + list(range(n))
    for er in choices:
        for ir in choices:
            if er is not None and er == ir:
                continue  # one round can't spend both skips
            prod, path = 1.0, []
            for i, r in enumerate(rounds):
                if er == i:
                    pick, ind, era = AE[i], r["industry"], r["altEra"]
                elif ir == i:
                    pick, ind, era = AI[i], r["altIndustry"], r["era"]
                else:
                    pick, ind, era = P[i], r["industry"], r["era"]
                prod *= pick["multiple"]
                path.append((ind, era, pick))
            if prod > best_prod:
                best_prod, best_path = prod, path

    balance, legs = STARTING_STAKE, []
    for ind, era, pick in best_path:
        balance *= pick["multiple"]
        legs.append(
            {
                "ticker": pick["ticker"],
                "name": pick["name"],
                "industry": ind,
                "eraLabel": era_label(era),
                "multiple": round(pick["multiple"], 2),
            }
        )
    return {"multiple": round(best_prod, 2), "finalValue": round(balance, 2), "legs": legs}


def score(picks, seed=None):
    """Score a finished game.

    `picks` is a list of dicts: {industry, era, ticker}. Returns the simulated
    portfolio result, validating each pick against the seed's actual rounds.
    """
    data = daily_rounds(seed)
    rounds = data["rounds"]
    if len(picks) != NUM_ROUNDS:
        raise ValueError(f"Expected {NUM_ROUNDS} picks, got {len(picks)}")

    legs = []
    balance = STARTING_STAKE  # rolls from one pick into the next
    for i, pick in enumerate(picks):
        rnd = rounds[i]
        industry = pick["industry"]
        era = pick["era"]

        # Validate the (industry, era) was actually reachable this round.
        valid_cells = {
            (rnd["industry"], rnd["era"]),
            (rnd["industry"], rnd["altEra"]),
            (rnd["altIndustry"], rnd["era"]),
        }
        if (industry, era) not in valid_cells:
            raise ValueError(f"Round {i}: illegal cell {industry} / {era}")

        stock = _lookup(industry, era, pick["ticker"])
        if not stock:
            raise ValueError(f"Round {i}: unknown stock {pick['ticker']}")

        invested = balance
        balance = balance * stock["multiple"]  # whole pot rides on this pick
        rank, cell_size = _cell_rank(industry, era, stock["ticker"])
        legs.append(
            {
                "ticker": stock["ticker"],
                "name": stock["name"],
                "industry": industry,
                "era": era,
                "eraLabel": era_label(era),
                "blurb": stock.get("blurb", ""),
                "multiple": round(stock["multiple"], 2),
                "invested": round(invested, 2),
                "finalValue": round(balance, 2),
                "gainPct": round((stock["multiple"] - 1) * 100, 1),
                # Standing within the era/industry the player was dealt.
                "rank": rank,
                "cellSize": cell_size,
                "medal": _MEDALS.get(rank),  # gold/silver/bronze, else None
                "perf": _perf_class(rank, cell_size),  # up/flat/down (green/yellow/red)
            }
        )

    final_value = balance
    multiple = final_value / STARTING_STAKE  # = product of every pick's multiple
    grade, verdict, color = _grade(multiple)

    best = max(legs, key=lambda l: l["multiple"])
    worst = min(legs, key=lambda l: l["multiple"])

    best_possible = _best_possible(rounds)
    captured = round(final_value / best_possible["finalValue"] * 100, 1) if best_possible["finalValue"] else 0.0

    return {
        "day": data["day"],
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
                    "multiple": round(s["multiple"], 2),
                    "gainPct": round((s["multiple"] - 1) * 100, 1),
                }
                for s in cell(industry, era)
            ]
            rows.sort(key=lambda r: r["multiple"], reverse=True)
            out[industry][era] = rows
    return {"eras": ERAS, "industries": INDUSTRIES, "stocks": out}
