# Root-five difficulty

## Summary

Today the investor rating comes straight from the final pot multiple, so one huge
pick can carry a weak lineup. With this change each round gets its own score from
1 to 100. A round reaches 100 at **100^(1/5) ≈ 2.512×**, the per-round pace that
compounds to 100× over five picks. Anything above that earns no extra credit.

The five round scores add up to a **game score out of 500**, and that score picks
the investor. The pot ($10,000 compounding) and its multiple stay uncapped and
unchanged.

## Round score (0–100)

The score uses only the stock's multiple `m`, so the same return scores the same
in every era. `C = 100 ** (1 / NUM_ROUNDS) ≈ 2.512`.

```
m = 0          score = 0                              # wipeout
0 < m < 1      score = max(1, 10 · m)                 # loss
m ≥ 1          h(m)  = 1 / (1 + (1.54 / m)^5.28)
               score = min(100, 100 · h(m) / h(C))    # gain
```

Round to the nearest integer. Only a bankruptcy scores 0, so every other pick moves
the bar. A loss scales straight down from 10. For gains, the S-shaped curve is rescaled
so it lands on exactly 100 at `C` and bends toward it on the way up. The constants
1.54 and 5.28 were fitted so 1× scores 10 and 1.5× scores 50.

| Multiple | 0× | 0.1× | 0.5× | 1× | 1.25× | 1.5× | 2× | 2.25× | 2.4× | 2.512×+ |
|---|---|---|---|---|---|---|---|---|---|---|
| Score | 0 | 1 | 5 | 10 | 27 | 50 | 86 | 95 | 98 | 100 |

What the anchors mean:

- **10** is about flat (0% return). **Under 10** is a loss.
- **50** is about a typical stock. Universe medians run 1.2× to 2.3× by era, about 1.6× overall.
- **100** means the pick kept the 100× pace.

## Game score (out of 500)

The sum of the five round scores. It's used only for the investor rating.

## Investor leaderboard

Seven rungs, one per person, in equal bands over 0–500. Rung `i` (0 = top) of `n`
starts at `500 · (n − 1 − i) / n`. The thresholds come from the list length, so
adding or removing an investor resizes the bands automatically. A game lands on the
first rung where `gameScore ≥ threshold`.

| Rung | Investor | Threshold | Lowest score |
|---|---|---|---|
| 1 | Jim Simons | 428.6 | 429 |
| 2 | Warren Buffett (rare Sanders variant stays) | 357.1 | 358 |
| 3 | Jack Bogle | 285.7 | 286 |
| 4 | Nancy Pelosi | 214.3 | 215 |
| 5 | Cathie Wood | 142.9 | 143 |
| 6 | Jim Cramer | 71.4 | 72 |
| 7 | Sam Bankman-Fried | 0 | 0 |

Investors are ranked by lifetime portfolio return, so Pelosi sits above Wood. Each
rung keeps its verdict text and color. Wood and Pelosi share a tier today, so each
needs its own verdict and color.

## Gameplay: reveal after each pick

After each pick, a reveal card replaces the stock list under the reels. The reels
and lineup bar stay in place, with the new pick filled in.

```
┌───────── 2010-2015 · Midwest ─────────┐
│ [Tech ABBV] [Fin   ] [Cons  ] ...      │
├────────────────────────────────────────┤
│  ABBV  AbbVie            Health        │
│                                        │
│        2.31×   +131%                   │
│        ████████████████████░  97 / 100 │
│                                        │
│        3rd of 41 Midwest stocks  🥉    │
│                          [ Next → ]    │
└────────────────────────────────────────┘
```

- **Shows:** ticker, name, industry, multiple, gain %, round score, and the pick's
  rank in that pool (with a medal for the top 3, as on the results screen).
- **Doesn't show:** a running total or the pot so far. Those wait for results.
- **Motion:** the stock list slides down and out, then the card slides up. The score
  counts up from 0 while the bar fills, over about 1.8 s. Moving on slides the card
  down and the next list up. These play even when the system asks for reduced motion.
- **Next** spins the reels for the next round. On the 5th pick, the card shows like
  the others and Next opens the results screen.
- A reload while a card is up shows the same card again.
- Learning mode uses the same card.

The intro copy tells players that each round scores up to 100 at 2.51×.

## Results

- Each leg shows its round score. The total shows out of 500.
- The investor badge works as it does today, without a leaderboard list.
- The best possible portfolio and captured % never use the score. They stay on
  uncapped returns.
- The pot, multiple, annual % and share text also stay uncapped for now.

## Implementation sketch

- `app/game.py`
  - Add `ROUND_CAP = 100 ** (1 / NUM_ROUNDS)` (or put it in `app/config.py`) and `round_score(multiple)`.
  - Replace the multiple thresholds in `_TIERS` with an ordered investor list. Derive the thresholds from its length.
  - `_grade` takes the game score instead of the multiple.
  - `score()` adds `score` to each leg and `gameScore` to the result.
- `app/__init__.py`: new `POST /api/reveal` with `{era, location, ticker}`, checked
  through `_pool_lookup`. It returns the multiple, gainPct, score, rank, cellSize and medal
(reusing `_pool_rank` and `_MEDALS`).
  `_stock_payload` still hides the multiple before a pick.
- `src/main.ts`: `pick()` fetches the reveal and renders the card into `#stock-grid`.
  The pending reveal goes into `saveSession()` so a reload restores it. **Next** goes on
  to `renderRound` or `submit()`. `showResult` shows per-leg scores and the total.
- `templates/index.html`, `static/style.css`: the reveal card and the intro copy.
- `tests/test_game.py`: round score anchor values, band edges, and a check that the pot is unchanged.

## Open questions

- Should the share text move to the score later?
