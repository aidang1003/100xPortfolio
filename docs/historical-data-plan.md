# Historical Data Gathering Plan — pre-1990 eras + delisted names

**Status:** proposal · **Owner:** data pipeline · **Last updated:** 2026-06-11

This plan covers two related expansions of the 100xPortfolio return dataset:

1. **Push the era coverage back to the 1970s** — add `1970-1974` … `1985-1989`
   to the existing `1990-1994` … `2020-2024` set.
2. **Capture stocks that dropped out of the S&P 500** — companies that were in
   the index during an era but were later acquired, delisted, or removed, and so
   are invisible to today's survivor-only build.

Both are aspects of the same underlying problem already documented in
`COVERAGE.md`: the universe is built by intersecting each era's roster with
**today's** sector map, so anything that left the market vanishes. That bias is
worst in the oldest eras (~39% of the 2000 index is still listed), and there is
currently *no* roster or price data before 1990 at all.

---

## 1. Where we are today

Grounding the plan in the current pipeline (`scripts/`):

| Piece | File | What it does | Limitation for this work |
|---|---|---|---|
| Returns cache | `collect.py` → `data/returns_cache.json` | One immutable `(ticker, era)` → multiple, fetched once from Yahoo chart JSON, kept forever | Yahoo silently drops most **delisted** tickers; no key, but no delisted coverage |
| Roster history | `find_candidates.py` (`fja05680/sp500`) | Point-in-time S&P 500 membership, with a ticker **identity check** to catch reuse (PETS, CC, …) | Membership list **begins 1996-01-02** → nothing for the 1970s–80s, and 1990-1994 is already a known gap |
| Universe build | `build_universe.py` → `app/universe.json` | Buckets each era's roster into 8 game categories via **today's** GICS map; overlays curated blurbs + hand-coded 0× "landmine" bankruptcies | Needs a *current* GICS sector, which delisted names don't have |
| Coverage report | `coverage.py` → `COVERAGE.md` | Quantifies survivorship gap per era | Reporting only |
| Eras | `app/catalog.py` `ERAS` | 7 eras, 1990-1994 → 2020-2024 | Hard stop at 1990 |

The key architectural fact: the pipeline is **cache-first and provider-pluggable**
already. Extending it is mostly about (a) sourcing point-in-time membership and
sectors further back, and (b) adding a price provider that retains delisted names —
*not* rewriting the engine.

---

## 2. The two hard problems

### Problem A — point-in-time index membership before 1996
`fja05680/sp500` cannot tell us who was in the S&P 500 in 1972 or 1985. Without a
roster we can't build those eras at all.

### Problem B — price data for names that left the index
Even within covered eras, once a company is acquired/delisted Yahoo's chart API
typically returns nothing for its old ticker (or worse, returns a *different*
company that later reused the ticker). This is the survivorship hole, and it's the
same data we need for the pre-1990 eras, where the *majority* of constituents are
now delisted.

These two problems share one root requirement: **a survivorship-bias-free source of
historical constituents + adjusted prices keyed to the company, not just the ticker
string.**

---

## 3. Data source strategy

We evaluate sources against four needs: (a) point-in-time membership, (b)
point-in-time sector, (c) adjusted prices including delisted, (d) cost/licensing.

### 3.1 Membership (who was in the index, when)

| Source | Coverage | Notes |
|---|---|---|
| `fja05680/sp500` (current) | 1996→now | Keep as the spine for 1996+; free, already wired in |
| Wikipedia "List of S&P 500 changes" | ~1990s→now | Free; additions/removals deltas, can be back-applied; noisy, needs scraping + cleanup |
| **CRSP** (via WRDS) | 1925→now | Gold standard, survivorship-bias-free, includes delisting returns; **academic/paid license** |
| **Norgate Data** | 1970s→now | Purpose-built survivorship-bias-free index constituents + delisted prices; affordable subscription |
| Siblis Research / S&P historical lists | varies | One-off purchasable constituent snapshots for specific historic dates |
| Manual curation | any | For the oldest eras, hand-curate the well-known names per category from public sources (annual reports, news, the existing landmine list pattern) |

**Recommendation:** treat 1996+ as solved by the current roster. For **1970–1995**,
the pragmatic path is a tiered approach:
- *Tier 1 (preferred):* one survivorship-bias-free dataset (Norgate or CRSP) that
  gives both membership and delisted prices in one shot.
- *Tier 2 (fallback, no paid data):* **hand-curate** a roster per (category, era)
  for the four pre-1990 eras — a few dozen marquee names each, mirroring how
  bankruptcies are already manually layered in `build_universe.py`. This keeps the
  game playable back to 1970 without a license, accepting that old eras are
  *curated highlights* rather than the full ~500.

### 3.2 Point-in-time sector (for bucketing into the 8 categories)

GICS only exists from 1999. For older names and delisted names:
- Use the company's **historical SIC / industry** mapped to one of the 8 game
  categories (a small `SIC → category` table).
- For hand-curated rosters, the category is assigned by the curator at entry time
  (same human call `find_candidates.py` already documents for industry bucketing).
- Store the resolved category **with the cached record** so the build no longer
  depends on today's GICS map for these names.

### 3.3 Prices including delisted

| Provider | Delisted retained? | Adjusted? | Key/cost | Fit |
|---|---|---|---|---|
| Yahoo chart JSON (current) | ✗ (mostly drops) | split+div | none | keep for live names |
| Stooq | partial | split | none | free fallback, spotty |
| Tiingo / EOD Historical Data | ✓ | ✓ | free-ish tier + key | good mid-tier |
| Sharadar (Nasdaq Data Link) | ✓ | ✓ | paid | strong |
| **CRSP / Norgate** | ✓ (with delisting return) | ✓ | paid | best, pairs with §3.1 |
| Manual seed multiple | n/a | n/a | none | last resort, already supported in `catalog.py` |

**Recommendation:** add **one** delisted-capable provider behind the existing
provider-fallback chain in `fetch_prices.py` (yfinance → Stooq → seed today). The
chain becomes: live-name provider → delisted-capable provider → curated seed.
Whichever paid/keyed source we pick in §3.1 should also cover prices so we don't
manage two vendors.

---

## 4. Design changes to the pipeline

Keep the cache-first philosophy; extend, don't replace.

1. **Eras** — add to `app/catalog.py`:
   ```
   "1970-1974", "1975-1979", "1980-1984", "1985-1989"
   ```
   The display-label helper (`eraLabel`) already generalizes, so the UI and slot
   reels need only their hardcoded era list widened (`static/game.js` `spinReels`).

2. **Cache record shape** — today a record is just a multiple. Extend each
   `(ticker, era)` entry to carry the fields a delisted/old name needs and which
   can no longer be looked up live:
   ```jsonc
   {
     "multiple": 0.0,            // existing
     "name": "Circuit City",     // company name at the time
     "category": "Consumer Discretionary", // resolved game category
     "delisted": true,           // dropped out / no longer trades
     "source": "norgate|manual", // provenance for auditing
     "asOf": "1985-01-02"        // membership snapshot used
   }
   ```
   This lets `build_universe.py` bucket delisted names **without** today's GICS map.

3. **Identity safety** — the renamed/reused-ticker check in `find_candidates.py`
   becomes mandatory for old eras (ticker reuse is rampant across decades). Records
   that fail the identity check are dropped, never silently mis-scored.

4. **Delisting / merger handling** — a name acquired *inside* an era ends at its
   buyout price (a real, terminal return), not zero. CRSP/Norgate give the delisting
   return directly; for manual entries the curator records the terminal multiple.
   Bankruptcies remain 0× landmines as they are today.

5. **New optional script** — `scripts/fetch_delisted.py` (or a flag on
   `fetch_prices.py`) that pulls the chosen delisted-capable provider and writes
   into the same durable cache, so reruns are network-free.

6. **Coverage report** — extend `coverage.py` to show the four new eras and a
   "delisted captured vs. dropped" column, so progress against survivorship bias is
   measurable.

---

## 5. Phased rollout

**Phase 0 — spike & decision (no data committed)**
- Evaluate one free path (Wikipedia deltas + Stooq/Tiingo) and one paid path
  (Norgate or CRSP) on a single old era. Decide Tier 1 vs Tier 2 per §3.1.
- Deliverable: a short follow-up note in this doc with the chosen provider(s).

**Phase 1 — schema + eras**
- Widen `ERAS` and the JS reel lists; extend the cache record shape (§4.2),
  back-filling existing records with `delisted:false`, `source:"yahoo"`.
- No new data yet; ensure the build + game still pass with empty old eras.

**Phase 2 — delisted within covered eras (1990–2024)**
- Wire the delisted-capable provider into the fallback chain; fetch dropped-out
  names for existing eras. This directly closes the documented survivorship gap and
  is independently shippable.
- Success metric: per-era "kept in game" counts in `COVERAGE.md` rise toward ~500.

**Phase 3 — pre-1990 eras (1970–1989)**
- Tier 1: ingest membership + prices from the paid source.
- Tier 2 (fallback): hand-curate rosters per (category, era) — target a minimum of
  ~8–12 pickable names per category per era so the slot machine always has a viable
  round.
- Success metric: every (category, era) cell ≥ the game's minimum pick count.

**Phase 4 — validation & polish**
- Spot-check a sample of multiples against a second source (±a few %).
- Regenerate `COVERAGE.md`; confirm no era/category cell is below the playable
  minimum; review the oldest eras for ticker-reuse false positives.

---

## 6. Risks & mitigations

- **Ticker reuse across decades** → mandatory identity check (§4.3); prefer
  company-keyed sources (CRSP/Norgate) over ticker-string lookups.
- **Pre-GICS sector gaps** → SIC→category table + curator assignment, stored in the
  cache record so it's stable.
- **Data licensing** → if a paid source is used, keep raw vendor data out of the
  repo; commit only derived multiples (a multiple is a single number, well within
  fair-use of a closed era's public-domain fact). Confirm this per vendor TOS in
  Phase 0.
- **Adjustment methodology drift** → standardize on split+dividend total return to
  match the current Yahoo basis; record `source` so mixed-provider eras are
  auditable.
- **Effort blow-up on old eras** → Tier 2 manual curation is explicitly scoped as
  *highlights, not full index*, capping the work while keeping the game fun.
- **Mergers mid-era** → terminal/buyout multiple, not zero (§4.4).

---

## 7. Open questions for Phase 0

1. Budget for a paid survivorship-bias-free source (Norgate ≈ low-hundreds/yr;
   CRSP via WRDS = institutional)? This is the single biggest fork in the plan.
2. For 1970–1989, is *curated highlights* acceptable, or do we require full-roster
   fidelity (which effectively forces the paid path)?
3. Minimum pickable stocks per (category, era) cell the game requires — needed to
   set the Phase 3 curation target.
