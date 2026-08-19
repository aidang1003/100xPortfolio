# Portfolio Redesign — from sequential parlay to a one-decade allocated basket

**Status:** proposal · **Owner:** game design / engine · **Last updated:** 2026-06-12

The goal: make 100× **hard** — so that even great picks usually fall short and people
replay — without losing the "$10k → $1M" hook. The current engine multiplies 5 picks
together, which explodes on the upside (two big legs = guaranteed win, no ceiling). We
replace that with a **single-decade portfolio you allocate across**, which builds in a
natural asymptote and, as a bonus, finally lets the game *teach* that consistent
compounding beats chasing winners.

---

# Part 1 — Human Spec

## The problem in one picture

```
NOW  (sequential parlay — pot re-bet each round across 5 different eras)
  $10k ─×m1─▶ ─×m2─▶ ─×m3─▶ ─×m4─▶ ─×m5─▶  final = 10k · (m1·m2·m3·m4·m5)
  └─ product. Two 20× legs = 400×. You've already won at round 2.
     Legs 3–5 are decoration. No ceiling. One 0× landmine = total wipeout.

NEW  (one decade, 5-stock basket, you split your $10k, held 10 years)
  $10k ─┬─ w1 → stock1 ·m1 ─┐
        ├─ w2 → stock2 ·m2 ─┤
        ├─ w3 → stock3 ·m3 ─┼─▶ final = 10k · Σ(wi·mi)   (Σwi = 1)
        ├─ w4 → stock4 ·m4 ─┤
        └─ w5 → stock5 ·m5 ─┘
  └─ weighted average. Bounded by your biggest bet. To 100× you must be
     right AND brave. One 0× landmine at 20% weight = a −20% scratch, not death.
```

## Why averaging fixes the difficulty (real data)

Best **diversified** basket (single best name in each of 5 sectors, equal-weighted),
by decade — i.e. the ceiling a perfect, careful player hits:

| Decade | Perfect diversified basket | Best single stock in the decade |
|---|---:|---:|
| 1990–1999 | **165×** | 698× |
| 2015–2024 | **67×** | 290× (NVDA) |
| 2010–2019 | 13× | 17× |
| 1995–2004 | 13× | 21× |
| 2005–2014 | 12× | 23× |
| 2000–2009 | 7× | — |

Read that table as the whole design:

- **Diversify and you hit a wall** — even perfect picks cap at ~13× in a normal
  decade. That is the asymptote. "You nailed the 5 best stocks of the 2010s and still
  only 13×'d" is a brutal, true, replay-driving result.
- **100× survives only for the brave** — to clear it you have to *concentrate* into a
  monster (single decade names hit 290×, 698×). The hook stays alive but becomes the
  legendary corner of the space, not a floor you trip over.

## The one new mechanic: you allocate

After picking 5 stocks, you split your $10k across them. **Stats are still hidden** when
you allocate — so it's a real bet on your own conviction, not a solved math problem.

- **All-in on one conviction pick** → you get that stock's full multiple. 100× reachable.
- **Equal-weight** → safe, capped at the ~13× diversified ceiling.
- The gap between those two outcomes, felt every single game, **is** the
  concentration-vs-diversification lesson.

Presets keep it one-tap; a slider is the power-user path:

```
   Allocate your $10,000            [ Equal ] [ Barbell ] [ All-in ] [ Custom ]
   ┌────────────────────────────────────────────────────────────────┐
   │ TECH   ███████████████████████████████████   60%      $6,000    │
   │ HEALTH ████████                               15%      $1,500    │
   │ FIN    ████                                   10%      $1,000    │
   │ INDU   ████                                   10%      $1,000    │
   │ STPL   ██                                      5%        $500    │
   └────────────────────────────────────────────────────────────────┘
                                            Σ = 100%   ·   Lock it in ▶
```

## Reconciling compounding (the lesson, finally)

There are two different things called "compounding," and today's game teaches the wrong one:

- **Parlay compounding (across picks)** — `m1·m2·…` — is the *gambler's* structure:
  re-bet the whole pot, win big, but one 0× zeroes you. The current game. It rewards
  chasing winners. This is the anti-lesson.
- **Time compounding (across years at a rate)** — `(1+r)^t` — is the real
  wealth-building mechanism, and the index-fund lesson.

The redesign demotes the first and promotes the second: your 5 picks combine into a
**portfolio rate**, and that rate compounds over the **10-year hold**, drawn as a curve
against the S&P line — which we show on every result. People learn "slow and consistent
wins" by watching the boring index line quietly stack up next to their volatile one.

## What the player sees

```
  Intro
    │
    ▼
  Spin ── lands ONE decade ("You're investing across 2010–2019")
    │
    ▼
  Round 1..5 ── same decade, a different sector each round; pick 1 stock
    │            (one era-skip… now a sector-swap; stats hidden as today)
    ▼
  Allocate ── split $10k across your 5 picks (stats still hidden)
    │
    ▼
  Reveal / Result
```

Result screen — the chart does the teaching:

```
  ┌─ GRADE  C ─────────────────────────  18× · +1,700% ──────────────┐
  │                                                                  │
  │   $1M ┆                                              ⋅⋅⋅YOU 18×  │
  │       ┆                                      ⋅⋅⋅⋅⋅⋅⋅             │
  │ $180k ┤                              ⋅⋅⋅⋅⋅⋅⋅⋅                    │
  │       ┆                       ⋅⋅⋅⋅⋅⋅⋅          ____________ S&P  │
  │       ┆            ⋅⋅⋅⋅⋅____________------------     3.5×        │
  │  $10k ┿━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
  │       └──2010────2013────2016────2019──────────────────────────  │
  │                                                                  │
  │  Your picks            weight   return   added                   │
  │  NVDA  Technology         60%     14×    +$50,400                 │
  │  LLY   Healthcare         15%      4×     +$4,500                 │
  │  JPM   Financials         10%      2×     +$1,000                 │
  │  CAT   Industrials        10%      3×     +$2,000                 │
  │  KO    Consumer Staples    5%      1×        +$0                  │
  │                                                                  │
  │  Best you could've done: all-in NVDA → 14×.                      │
  │  If you'd just bought the index: 3.5×, zero research, no nerve.  │
  └──────────────────────────────────────────────────────────────────┘
```

## Key design decisions

- **Lock one decade per game** (not 5 different eras). A real portfolio is held over one
  period; this is what makes the index baseline and the time-compounding curve meaningful.
- **5-year era → 10-year hold.** Your "retire in 10, not 25" framing. Decade multiples are
  juicier, which keeps the 100× dream vivid at the stock level.
- **Picks span 5 distinct sectors.** Keeps the existing round-by-round UX and scaffolds
  diversification; the skip becomes a sector-swap.
- **Score = weighted average `Σ wi·mi`, not a product.** Bounded by your biggest bet →
  the asymptote is automatic.
- **Allocate with stats hidden.** Keeps it a genuine bet; otherwise "all-in on the known
  best" is a dominant strategy and the choice evaporates.
- **100× stays the S grade.** Only the *path* changes (concentration, not parlay). Lower
  tiers get recalibrated to the new, compressed distribution.
- **Index line on every result.** The educational payload, shown not told.
- **Optional per-stock cap (the "you'd have sold at 4×" knob).** A tunable ceiling on any
  single multiple, to stop an all-in 290× from trivializing the richest decades. Off by
  default; turn on if 100× proves too easy for concentrators.

## Open decisions (need a call before building)

1. **Allocation UI:** presets-only (one-tap, ship fast) vs presets + slider (more depth)?
2. **Decade set:** overlapping 10-yr windows (`1990–99, 1995–04, …`, 6 options, more
   variety) vs clean non-overlapping decades (3–4 options, simpler story)?
3. **Decade multiples:** chain two 5-yr eras from existing cache (free, but drops any name
   not present in both halves — worsens survivorship) vs refetch true 10-yr returns (clean,
   costs a data pass)?
4. **Per-stock cap:** ship with it on (and at what ×) or keep it off until tuning says so?
5. **Learning mode:** keep as-is (reveals %), or also reveal the *index line* so the study
   view drives the lesson home?

---

# Part 2 — AI Spec Sheet

## Renames / reframes

| Old | New | Note |
|---|---|---|
| round = (era, industry) spin | round = (sector) pick within the game's locked decade | era is fixed game-wide |
| `NUM_ROUNDS` | `NUM_PICKS` | still 5 |
| era-skip / industry-skip | sector-swap (one) + ?second swap | era-skip is meaningless once decade is locked |
| `score(picks, seed)` product | `score(picks, weights, seed)` weighted avg | weights new |
| `multiple = Π mi` | `multiple = Σ wi·mi` | bounded |
| "best possible run" (parlay path) | "best single bet" = max reachable single multiple | all-in dominates weighted avg in hindsight |

## Constants (`app/game.py`)

```
NUM_PICKS        = 5
STARTING_STAKE   = 10_000
HOLD_YEARS       = 10
PER_STOCK_CAP    = None        # e.g. 50.0 to enable Lever A; None = off
DECADES          = [...]       # see open decision #2
GRADE_TIERS      = [...]       # recalibrated — see below
```

## Grade recalibration (`_grade`, absolute multiple)

Distribution is now compressed (weighted avg, ~13× diversified ceiling, 100× only for
concentrators). Starting point, tune against seed sims:

```
S  >= 100   Legendary — you 100×'d the pot      gold
A  >=  40   Elite — huge conviction paid off     green
B  >=  20   Strong portfolio                     blue
C  >=  10   Solid — beat the index handily       yellow
D  >=   3   Modest — roughly matched the index   red
F  <    3   Brutal — the index beat you          gray   (anchor F to the decade's S&P mult)
```

## Data (`app/data.py`, `app/universe.json`, build scripts)

- **Decade multiples.** Either (a) `build_universe` emits `(industry, decade) → [{ticker,
  name, multiple10y, …}]` by chaining consecutive era multiples for tickers present in
  both halves; or (b) a new `collect` pass fetches true 10-yr `(ticker, decade)` returns.
- **Index baseline.** New `INDEX_MULT: {decade -> spy_multiple}` (and ideally a per-year
  series for the chart, or derive from CAGR). Source: SPY / S&P 500 total return per
  decade. ~6 numbers. No equivalent exists today — must be added.
- `cell(industry, era)` → `cell(industry, decade)`; era enums become decade enums.

## `app/game.py` call graph

```
daily_rounds(seed)
  └─ pick ONE decade (seeded) → spin 5 distinct sectors → bundle cells (+ swap alts)

score(picks, weights, seed)
  ├─ validate len(picks)==NUM_PICKS, len(weights)==NUM_PICKS, Σweights≈1, each cell legal
  ├─ per leg: m = cap(stock.multiple, PER_STOCK_CAP); contribution = weight * m
  ├─ portfolio_mult = Σ contribution ; final = STARTING_STAKE * portfolio_mult
  ├─ index_mult = INDEX_MULT[decade]
  ├─ best_single = max reachable single multiple over the 5 rounds (all-in ceiling)
  ├─ growth_series = per-year $ curve for basket and for index (CAGR interp over HOLD_YEARS)
  └─ grade = _grade(portfolio_mult)

best_possible(rounds)  →  now trivial: all-in on max reachable stock (no skip brute force)
```

## API / payload changes

- `POST /api/score` body: add `weights: number[5]` alongside `picks`. Server is
  authoritative — re-validate Σ=1 and non-negative.
- `/api/score` response: add `weights`, `indexMultiple`, `bestSingle`, `growthSeries`
  (`{year, basket, index}[]`), per-leg `weight` + `contribution`. Drop parlay-only
  `capturedPct` vs the old best-run; replace with `vsIndex` and `vsBestSingle`.
- `/api/daily`: one `decade` + `decadeLabel` at top level; rounds carry `sector` + one
  swap-cell instead of altEra/altIndustry.

## Frontend (`src/main.ts`, `templates/index.html`, `static/style.css`)

- New **allocation screen** between last pick and submit: presets (Equal / Barbell /
  All-in / Custom) → weight rows with $ + % → "Lock it in" calls `submit(weights)`.
- `state` additions: `weights[]`, `decade`, `allocPreset`; `screen` gains `"allocate"`.
  Extend `snapshot()`/`restoreSession()` for refresh-resume.
- Result screen: render the **dual-line growth chart** (basket vs index, `growthSeries`),
  per-leg weight/contribution columns, "best single bet" hindsight line, "vs index" line.
- Reels: spin **one decade** (+ the per-round sector), not era+industry each round.
- Share text: lead with multiple + a "beat/lost to the index" tag instead of the legs grid
  alone (reinforces the lesson in the viral surface).

## Invariants

- `Σ weights == 1` (server-clamped), each `weight ∈ [0,1]`.
- `portfolio_mult ≤ max(mi)` always (sanity: weighted avg can't exceed its largest term) —
  this is the ceiling guarantee; assert in tests.
- A single 0× landmine caps damage at its `weight` (no total wipeout unless weight=1).
- Allocation is collected with returns hidden; reveal happens only on the result screen.

## Required tests

- `score` weighted-avg math: known picks+weights → exact `Σ wi·mi`.
- Ceiling: random picks/weights ⇒ `portfolio_mult ≤ max picked multiple` (fuzz).
- Weight validation: rejects Σ≠1, negatives, wrong length.
- Landmine: 0× at weight w drags portfolio by exactly w·(its share).
- `best_single` == max reachable multiple across the 5 rounds.
- Grade boundaries at 3/10/20/40/100.
- Seed determinism: same seed ⇒ same decade + sectors worldwide.

## Files touched

```
app/game.py            scoring → weighted avg; daily spin → one decade; best_single
app/data.py            era→decade access; INDEX_MULT loader
app/universe.json      decade-bucketed multiples (regenerate)
app/__init__.py        /api/score accepts weights; payload fields
scripts/build_universe.py   emit decade cells + index baseline
src/main.ts            allocation screen, weights state, dual-line chart, one-decade reels
templates/index.html   allocation markup + chart container
static/style.css       allocation rows, slider, chart styles
README.md              rules + the compounding/diversification framing
```
