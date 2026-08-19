# 100xPortfolio

A daily stock-picking game inspired by [82-0.com](https://www.82-0.com), but for investing.

Each round deals a **5-year era** and a **US region**. You pick a company
**headquartered there** that you think crushed it — and you draft five, **one per
industry**, like a starting lineup. You start with **$10,000** and it **compounds**:
the whole pot rides on pick #1, then those earnings ride on pick #2, and so on. Then
the engine grades the run. Can you go **100×** and turn it into a million?

- **5 picks, one per industry.** Multi-industry names (Amazon = Tech *or* Consumer) are flexible.
- Each round is an **(era × HQ region)** spin — pick a company based there.
- Returns are **hidden**; the **entry price, P/E and dividend yield** are shown.
- The day's board is **the same for everyone** (seeded by date).

Eras are shown as clean 5-year spans (e.g. **2020–2025**); the underlying return
window is unchanged (`2020-2024` = Jan 2020 → Dec 2024).

## Stack

- **Flask** (Python) backend — daily spins + server-authoritative scoring.
- **TypeScript** frontend bundled with **esbuild** to `static/app.js` (no framework).
- Normalized static JSON data (no database).

## Data model

The app reads a few normalized files under `app/`, joined into the runtime
`universe.json` at build time:

| File | What it holds |
|---|---|
| `scripts/data/prices.json` | Monthly adjusted-close **series** per ticker. Any window's multiple is computed on the fly (`close[end] / close[start]`). |
| `app/companies.json` | Per-company: name, **industries** (multi-tag), **HQ** (city/state/region), GICS sub-industry, CIK. |
| `app/membership.json` | Point-in-time S&P 500 **rosters** per year (who was in the index when). |
| `app/fundamentals.json` | **Entry metrics** per (ticker, era): price, P/E, dividend yield. |
| `app/universe.json` | The built runtime dataset: 5 categories × 7 eras, with HQ + metrics on each entry. |
| `app/data/{landmines,gics_fold}.json` | Bankruptcy gotchas and the GICS→category fold. |

## Data pipeline

Cache-first and immutable: a closed era's numbers never change, so each series is
fetched **once** and committed. Rebuild everything with one command:

```bash
python scripts/refresh.py            # incremental — picks up new index members
python scripts/refresh.py --refresh  # also re-download the source CSVs
```

That runs, in order:

1. **`build_membership.py`** — per-year index rosters from
   [fja05680/sp500](https://github.com/fja05680/sp500) → `membership.json`.
2. **`build_companies.py`** — names, GICS industries + **HQ** from the same repo's
   `sp500.csv` (Wikipedia-derived), plus a curated multi-industry overlay → `companies.json`.
3. **`build_fundamentals.py`** — entry price/yield from Yahoo + P/E from
   **SEC EDGAR** EPS (split-reconciled; P/E only where EDGAR reaches, ~2010+) → `fundamentals.json`.
4. **`build_universe.py`** — joins the above with on-the-fly multiples from
   **`collect.py`** (Yahoo monthly series), folds GICS → 5 categories, layers in the
   bankruptcy landmines → `universe.json`.
5. **`coverage.py`** — regenerates `docs/COVERAGE.md`.

`scripts/find_candidates.py` is a curation aid (identity-checked S&P membership diff,
for extending the delisted/historical universe). Sources: Yahoo public chart JSON
(prices, no key), fja05680 (membership + GICS + HQ), SEC EDGAR (fundamentals).

> A future/shelved redesign (weighted one-decade basket) lives in
> `docs/portfolio-redesign.md`; the current game keeps sequential-parlay scoring.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm install            # esbuild + typescript (dev only)
npm run build          # src/*.ts -> static/app.js  (commit the bundle)
python api/index.py    # http://localhost:5000
```

The compiled `static/app.js` is committed, so **run `npm run build` after editing
`src/`**. `npm run watch` rebuilds on save; `npm run typecheck` runs `tsc`.

## Deploy to Vercel

`vercel.json` wires the Flask app (`api/index.py`) as a Python serverless function
with all routes pointed at it; `templates/`, `static/`, and `app/` are bundled.
Vercel Web Analytics (page views) loads from `/_vercel/insights/script.js`.

```bash
vercel --prod
```

## Layout

```
.
├── api/index.py            # Vercel entrypoint (exposes Flask `app`)
├── app/
│   ├── __init__.py         # Flask factory + routes (/api/daily, /score, /learn, /config)
│   ├── config.py           # single source: stake, rounds, industry colors, era labels
│   ├── data.py             # runtime loader for universe.json
│   ├── game.py             # (era, HQ-location) spins + one-per-industry scoring
│   ├── universe.json       # built dataset (companies × eras, with HQ + metrics)
│   ├── companies.json · membership.json · fundamentals.json
│   └── data/{landmines,gics_fold}.json
├── scripts/
│   ├── refresh.py          # one-command rebuild orchestrator
│   ├── collect.py          # monthly price-series store + on-the-fly multiples
│   ├── build_{membership,companies,fundamentals,universe}.py
│   ├── find_candidates.py  # membership diff / curation aid + shared roster lib
│   ├── coverage.py         # → docs/COVERAGE.md
│   └── common.py           # shared constants + source-CSV loader (remaps, UA, eras, categories, GICS fold)
├── src/main.ts             # TypeScript frontend (built → static/app.js)
├── templates/index.html · static/{style.css,app.js}
├── tests/                  # pytest/unittest: prices, fundamentals, game rules
├── package.json · tsconfig.json · requirements.txt · vercel.json
```

> Educational game. Returns are historical approximations — **not investment advice.**
```
