"""Single source of truth for game constants + presentation config.

Flask-free so it can be imported anywhere. Served to the front end via
/api/config so the client stops hard-coding stakes, round counts, and colors.
"""

STARTING_STAKE = 10_000  # dollars you start with; 100x = $1M
NUM_ROUNDS = 5

# Industry -> accent color. The front end builds CSS variables from this and
# blends the two colors into a gradient for multi-industry stocks (e.g. Amazon).
INDUSTRY_COLORS = {
    "Technology": "#3b82f6",          # blue
    "Financials": "#22c55e",          # green
    "Consumer": "#f59e0b",            # amber
    "Health & Utilities": "#ef4444",  # red
    "Industry & Energy": "#8b5cf6",   # violet
}

# One line per industry, shown on the intro screen so players know the board
# before they enter. Keyed to INDUSTRY_COLORS.
INDUSTRY_BLURBS = {
    "Technology": "Software, chips, telecom, media",
    "Financials": "Banks, insurers, payments, real estate",
    "Consumer": "Retail, food, cars, restaurants, brands",
    "Health & Utilities": "Drugs, hospitals, power, water",
    "Industry & Energy": "Machines, defense, chemicals, oil, transport",
}


def era_label(era):
    """Display label for an era: a clean 5-year span ('2020-2024' -> '2020-2025')."""
    start = era.split("-")[0]
    return f"{start}-{int(start) + 5}"
