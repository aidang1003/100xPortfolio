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


def daily_rounds(day=None):
    """Deterministically generate the day's 5 rounds.

    Each round carries a primary (era, industry) plus one alternate era and one
    alternate industry the player can swap to with their single era/industry skip.
    Every relevant cell's stock list is bundled so the client never re-fetches.
    """
    day = day or today_str()
    rng = random.Random(_seed_for(day))

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
    return {"day": day, "rounds": rounds}


def _cell_payload(industry, era):
    return {
        "industry": industry,
        "era": era,
        "eraLabel": era_label(era),
        "stocks": [
            {"ticker": s["ticker"], "name": s["name"], "blurb": s["blurb"]}
            for s in cell(industry, era)
        ],
    }


def _lookup(industry, era, ticker):
    for s in STOCKS.get(industry, {}).get(era, []):
        if s["ticker"] == ticker:
            return s
    return None


def _grade(multiple):
    if multiple >= 100:
        return ("100x", "Mythical — the dream realized", "gold")
    if multiple >= 15:
        return ("S", "Legendary timing", "gold")
    if multiple >= 8:
        return ("A", "Elite stock-picking", "green")
    if multiple >= 4:
        return ("B", "Strong portfolio", "green")
    if multiple >= 2:
        return ("C", "Solid, you beat the market", "blue")
    if multiple >= 1.2:
        return ("D", "Meh — barely moved the needle", "yellow")
    if multiple >= 1.0:
        return ("E", "Treading water", "yellow")
    return ("F", "You lost money. Brutal.", "red")


def score(picks, day=None):
    """Score a finished game.

    `picks` is a list of dicts: {industry, era, ticker}. Returns the simulated
    portfolio result, validating each pick against the day's actual rounds.
    """
    data = daily_rounds(day)
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
        legs.append(
            {
                "ticker": stock["ticker"],
                "name": stock["name"],
                "industry": industry,
                "era": era,
                "eraLabel": era_label(era),
                "blurb": stock["blurb"],
                "multiple": round(stock["multiple"], 2),
                "invested": round(invested, 2),
                "finalValue": round(balance, 2),
                "gainPct": round((stock["multiple"] - 1) * 100, 1),
            }
        )

    final_value = balance
    multiple = final_value / STARTING_STAKE  # = product of every pick's multiple
    grade, verdict, color = _grade(multiple)

    best = max(legs, key=lambda l: l["multiple"])
    worst = min(legs, key=lambda l: l["multiple"])

    return {
        "day": data["day"],
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
    }
