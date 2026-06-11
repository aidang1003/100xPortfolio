# 100xPortfolio

A daily stock-picking game inspired by [82-0.com](https://www.82-0.com), but for investing.

The slot machine deals you a random **5-year era** and a random **industry**. You
pick the one stock you think crushed it — five times. You start with **$10,000**
and it **compounds**: the whole pot rides on pick #1, then those earnings ride on
pick #2, and so on. Then the engine grades the run. Can you go **100×** and turn it
into a million?

- **5 rounds.** Start with $10,000 — gains roll from each pick into the next.
- Stats are **hidden** — it's a test of market history.
- **One era skip + one industry skip** for the whole game.
- The day's spins are **the same for everyone** (seeded by date).

Eras are shown as clean 5-year spans (e.g. **2020–2025**); the underlying return
window is unchanged (`2020-2024` = Jan 2020 → Dec 2024).

## Stack

- **Flask** (Python) backend — daily spins + server-authoritative scoring.
- Vanilla HTML/CSS/JS frontend (no build step).
- Static return data in `app/universe.json` (no database).

## Data pipeline

The app reads **`app/universe.json`** at runtime: the full S&P 500 universe bucketed
into **8 categories × 7 eras** (30–80+ names per cell), shown as a pickable list. It's
produced in two cache-first steps:

```bash
python scripts/build_universe.py   # cache + GICS sectors -> app/universe.json
```

1. **`scripts/collect.py`** — cache-first returns collector. A 5-year era's total
   return is immutable once the window closes, so each `(era, ticker)` multiple is
   fetched **once** from Yahoo's public chart JSON (split+dividend adjusted, no deps)
   and kept forever in the tracked cache `scripts/data/returns_cache.json`. Only true
   misses hit the network. (Stooq 404s from many networks and yfinance isn't always
   installed, so both were dropped — Yahoo is the sole provider.)
2. **`scripts/build_universe.py`** — buckets each era's S&P 500 roster
   ([fja05680](https://github.com/fja05680/sp500) membership + `sp500.csv` GICS
   sectors) into the 8 game categories (the 11 GICS sectors with Real Estate, Energy
   and Communication Services folded in). Curated blurbs are overlaid where present
   and famous bankruptcies are layered in as `0×` landmines (the data is survivor-only).

The legacy `scripts/fetch_prices.py` + hand-curated `app/catalog.py` (6 categories,
seed multiples) remain as the fallback if `universe.json` is missing.

> Note: some stock-data hosts are blocked on locked-down/CI networks. The fetcher
> loads `app/catalog.py` directly (no Flask needed), so you can run it from any
> machine with open internet, then commit the JSON.

### Finding new names: `scripts/find_candidates.py`

To grow the catalog without survivorship bias, this tool pulls the historical
S&P 500 membership list from [fja05680/sp500](https://github.com/fja05680/sp500),
takes the index roster as of each era's **start**, drops names already in the
catalog (deduped by `(ticker, era)` — a ticker can be a new candidate in an era
it's not yet listed in), then fetches each candidate's 5-year return from Yahoo
with an **identity check**: the first close must land near the era start, so a
reused or renamed symbol (`CC` = Chemours today, not Circuit City) is flagged
rather than silently scored as the wrong company.

```bash
python scripts/find_candidates.py --era 2010-2014   # ranked menu for one era
python scripts/find_candidates.py --no-fetch        # just the roster diff (fast)
```

Output is a ranked, identity-flagged menu (`full` / `partial` / `LATE` / `dead`)
to drive manual curation — bucketing into the game's six industries stays a human
call. The list starts in 1996, so the 1990s eras are approximated/manual.

### Bankruptcy landmines

Famous flameouts are intentionally seeded into the era they collapsed as `0.0`
"gotcha" picks — WorldCom, Lehman, Bear Stearns, Washington Mutual, Blockbuster,
Circuit City, Sears, Bed Bath & Beyond, JCPenney, Kodak, Enron, GM, SVB… Their
tickers are pinned in `FORCE_SEED` (in `scripts/fetch_prices.py`) because many
have since been reused by other companies, so they must never be fetched.

## Run locally

```bash
cd 100xportfolio
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python api/index.py            # http://localhost:5000
```

## Deploy to Vercel

This folder is a self-contained Vercel project. From the Vercel dashboard, set the
**Root Directory** to `100xportfolio` and deploy — `vercel.json` wires the Flask
app (`api/index.py`) as a Python serverless function with all routes pointed at it.

```bash
# or from the CLI, inside this folder:
vercel --prod
```

## Layout

```
.
├── api/index.py        # Vercel entrypoint (exposes Flask `app`)
├── app/
│   ├── __init__.py     # Flask app factory + routes
│   ├── data.py         # runtime loader: reads universe.json (falls back to catalog)
│   ├── game.py         # seeded spins, skips, compounding score, best-possible run
│   ├── universe.json   # generated dataset: 8 categories × 7 eras (real returns)
│   └── catalog.py      # legacy 6-category catalog: blurb/landmine source + fallback
├── scripts/
│   ├── collect.py          # cache-first Yahoo-only returns collector
│   ├── build_universe.py   # roster × GICS sectors → app/universe.json
│   ├── find_candidates.py  # S&P 500 membership → identity-checked candidate menu
│   ├── fetch_prices.py     # legacy scraper → app/stocks.json
│   └── data/returns_cache.json  # tracked, durable (era,ticker) → multiple cache
├── templates/index.html
├── static/{style.css,game.js}
├── requirements.txt
└── vercel.json
```

> Educational game. Returns are hand-curated historical approximations — **not investment advice.**
