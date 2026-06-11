# Stock coverage — 100xPortfolio universe

Generated from `app/universe.json` (built 2026-06-11). Each cell is the
number of pickable stocks for that category × era.

| Category | 1990-1995 | 1995-2000 | 2000-2005 | 2005-2010 | 2010-2015 | 2015-2020 | 2020-2025 | **Total** |
|---|---|---|---|---|---|---|---|---|
| Technology | 18 | 18 | 28 | 32 | 41 | 46 | 63 | **246** |
| Healthcare | 13 | 15 | 19 | 27 | 29 | 35 | 45 | **183** |
| Financials | 13 | 18 | 31 | 43 | 59 | 62 | 84 | **310** |
| Consumer Discretionary | 9 | 10 | 16 | 20 | 28 | 35 | 41 | **159** |
| Consumer Staples | 18 | 18 | 18 | 19 | 27 | 30 | 31 | **161** |
| Industrials | 29 | 29 | 32 | 35 | 40 | 45 | 62 | **272** |
| Utilities | 15 | 15 | 21 | 22 | 24 | 25 | 28 | **150** |
| Materials | 18 | 19 | 22 | 23 | 25 | 32 | 39 | **178** |
| **Total** | **133** | **142** | **187** | **221** | **273** | **310** | **393** | **1659** |

## Why the per-era totals are ~130–390, not ~500

The S&P 500 held ~500 names in every era, but each era cell is built by intersecting
that era's index roster with **today's** sector map (`sp500.csv`, 503 names). Any
company that was in the index then but has since been acquired, delisted, or dropped
has no current sector and is excluded — **survivorship bias**, worst in the old eras
(only ~39% of the 2000 index is still listed today).

| Era | In S&P that era | Kept in game | Dropped: no longer in index | Dropped: no return data |
|---|---|---|---|---|
| 1990-1995 | 487 | 133 | 335 | 19 |
| 1995-2000 | 487 | 142 | 335 | 10 |
| 2000-2005 | 492 | 183 | 300 | 9 |
| 2005-2010 | 495 | 215 | 269 | 11 |
| 2010-2015 | 499 | 271 | 222 | 6 |
| 2015-2020 | 499 | 307 | 188 | 4 |
| 2020-2025 | 505 | 390 | 113 | 2 |

"Kept in game" is survivors-with-data (the era totals above, minus a few curated
landmines). The dominant loss is **"no longer in index"** — historical members we have
no current GICS sector for, so they can't be bucketed.

## 102 current S&P 500 members missing from every era

A separate gap: the universe uses each era's **start-date** roster, so companies added
to the index later never appear. Marquee omissions: **Tesla** (added Dec 2020),
**Meta**, **Berkshire Hathaway**, **Uber**, **Palantir**, **Coinbase**, **Airbnb**,
**KKR**, **Blackstone**, **CrowdStrike**.

<details><summary>Full list of 102 missing current members</summary>

- `ABNB` — Airbnb (Consumer Discretionary)
- `ACGL` — Arch Capital Group (Financials)
- `APO` — Apollo Global Management (Financials)
- `APP` — AppLovin (Information Technology)
- `ARES` — Ares Management (Financials)
- `AXON` — Axon Enterprise (Industrials)
- `BALL` — Ball Corporation (Materials)
- `BF-B` — Brown–Forman (Consumer Staples)
- `BG` — Bunge Global (Consumer Staples)
- `BLDR` — Builders FirstSource (Industrials)
- `BNY` — BNY Mellon (Financials)
- `BRK-B` — Berkshire Hathaway (Financials)
- `BRO` — Brown & Brown (Financials)
- `BX` — Blackstone Inc. (Financials)
- `CARR` — Carrier Global (Industrials)
- `CASY` — Casey's (Consumer Staples)
- `CEG` — Constellation Energy (Utilities)
- `COHR` — Coherent Corp. (Information Technology)
- `COIN` — Coinbase (Financials)
- `COR` — Cencora (Health Care)
- `CPAY` — Corpay (Financials)
- `CPT` — Camden Property Trust (Real Estate)
- `CRH` — CRH plc (Materials)
- `CRL` — Charles River Laboratories (Health Care)
- `CRWD` — CrowdStrike (Information Technology)
- `CSGP` — CoStar Group (Real Estate)
- `CVNA` — Carvana (Consumer Discretionary)
- `DASH` — DoorDash (Consumer Discretionary)
- `DDOG` — Datadog (Information Technology)
- `DECK` — Deckers Brands (Consumer Discretionary)
- `DELL` — Dell Technologies (Information Technology)
- `DOC` — Healthpeak Properties (Real Estate)
- `DPZ` — Domino's (Consumer Discretionary)
- `DXCM` — Dexcom (Health Care)
- `EG` — Everest Group (Financials)
- `ELV` — Elevance Health (Health Care)
- `EME` — Emcor (Industrials)
- `ERIE` — Erie Indemnity (Financials)
- `EXE` — Expand Energy (Energy)
- `FDS` — FactSet (Financials)
- `FDXF` — FedEx Freight (Industrials)
- `FICO` — Fair Isaac (Information Technology)
- `FIX` — Comfort Systems USA (Industrials)
- `GDDY` — GoDaddy (Information Technology)
- `GEHC` — GE HealthCare (Health Care)
- `GEN` — Gen Digital (Information Technology)
- `GEV` — GE Vernova (Industrials)
- `GNRC` — Generac (Industrials)
- `HOOD` — Robinhood Markets (Financials)
- `HUBB` — Hubbell Incorporated (Industrials)
- `HWM` — Howmet Aerospace (Industrials)
- `IBKR` — Interactive Brokers (Financials)
- `INVH` — Invitation Homes (Real Estate)
- `KKR` — KKR & Co. (Financials)
- `KVUE` — Kenvue (Consumer Staples)
- `LII` — Lennox International (Industrials)
- `LITE` — Lumentum (Information Technology)
- `LULU` — Lululemon Athletica (Consumer Discretionary)
- `META` — Meta Platforms (Communication Services)
- `MPWR` — Monolithic Power Systems (Information Technology)
- `MRNA` — Moderna (Health Care)
- `MRSH` — Marsh McLennan (Financials)
- `NDSN` — Nordson Corporation (Industrials)
- `NXPI` — NXP Semiconductors (Information Technology)
- `ON` — ON Semiconductor (Information Technology)
- `OTIS` — Otis Worldwide (Industrials)
- `PANW` — Palo Alto Networks (Information Technology)
- `PLTR` — Palantir Technologies (Information Technology)
- `PODD` — Insulet Corporation (Health Care)
- `POOL` — Pool Corporation (Consumer Discretionary)
- `PSKY` — Paramount Skydance Corporation (Communication Services)
- `Q` — Qnity Electronics (Information Technology)
- `RTX` — RTX Corporation (Industrials)
- `RVTY` — Revvity (Health Care)
- `SATS` — EchoStar (Communication Services)
- `SMCI` — Supermicro (Information Technology)
- `SNDK` — Sandisk (Information Technology)
- `SOLV` — Solventum (Health Care)
- `STLD` — Steel Dynamics (Materials)
- `SW` — Smurfit Westrock (Materials)
- `TDY` — Teledyne Technologies (Information Technology)
- `TECH` — Bio-Techne (Health Care)
- `TKO` — TKO Group Holdings (Communication Services)
- `TPL` — Texas Pacific Land Corporation (Energy)
- `TRGP` — Targa Resources (Energy)
- `TRMB` — Trimble Inc. (Information Technology)
- `TSLA` — Tesla, Inc. (Consumer Discretionary)
- `TTD` — Trade Desk (The) (Communication Services)
- `TYL` — Tyler Technologies (Information Technology)
- `UBER` — Uber (Industrials)
- `VEEV` — Veeva Systems (Health Care)
- `VICI` — Vici Properties (Real Estate)
- `VLTO` — Veralto (Industrials)
- `VRT` — Vertiv (Industrials)
- `VST` — Vistra Corp. (Utilities)
- `VTRS` — Viatris (Health Care)
- `WBD` — Warner Bros. Discovery (Communication Services)
- `WDAY` — Workday, Inc. (Information Technology)
- `WSM` — Williams-Sonoma, Inc. (Consumer Discretionary)
- `WST` — West Pharmaceutical Services (Health Care)
- `WTW` — Willis Towers Watson (Financials)
- `XYZ` — Block, Inc. (Financials)

</details>

## Recommended fixes

1. **Fuller eras (the big one):** fetch returns for the *full* historical roster, not
   just current survivors, and source **point-in-time GICS sectors** for the now-delisted
   names (e.g. Yahoo `quoteSummary` assetProfile, or a historical sector table) so they
   can be bucketed. This is what moves eras toward ~500.
2. **Missing current names:** bucket each era from a later/union roster (or current
   membership for the live era) instead of only the era-start snapshot — captures Tesla,
   Uber, Palantir, etc. (~100 of these are in the latest membership snapshot).

