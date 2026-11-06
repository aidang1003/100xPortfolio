"""Game constants, served to the client via /api/config."""

from datetime import date
from zoneinfo import ZoneInfo

# DAY_ONE is daily #1.
GAME_TZ = ZoneInfo("America/Denver")
DAY_ONE = date(2026, 11, 3)

SITE_URL = "https://play100x.com"

STARTING_STAKE = 10_000
NUM_ROUNDS = 5
ERA_YEARS = 5

INDUSTRY_COLORS = {
    "Technology": "#3b82f6",
    "Financials": "#22c55e",
    "Consumer": "#f59e0b",
    "Health & Utilities": "#ef4444",
    "Industry & Energy": "#8b5cf6",
}

def era_label(era):
    """'2020-2024' -> '2020-2025'"""
    start = era.split("-")[0]
    return f"{start}-{int(start) + ERA_YEARS}"
