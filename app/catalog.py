"""Editorial catalog + seed multiples for 100xPortfolio.

This is the source of truth for *which* stocks appear in each (industry, era)
cell, plus their display name and blurb. Each stock also carries a seed
`multiple` (total return over the 5-year window: 1.0 = flat, 2.0 = doubled,
0.0 = wiped out) used as a fallback when real data isn't available.

`scripts/fetch_prices.py` reads this catalog, fetches real returns (Yahoo ->
yfinance -> Stooq), and writes `app/stocks.json`, which the app loads at
runtime. The seed values here cover delisted / bankrupt names a scraper can't
fetch (Enron, Lehman, Pets.com, SVB, GM's 2009 bankruptcy, …).

Note: era keys are the 5-year data window (e.g. "2020-2024" = 2020-01-01 →
2024-12-31). They're displayed to players as clean 5-year spans ("2020-2025")
by game.era_label(); the window used for returns is unchanged.
"""

# Five-year eras the slot machine can land on.
ERAS = [
    "1990-1994",
    "1995-1999",
    "2000-2004",
    "2005-2009",
    "2010-2014",
    "2015-2019",
    "2020-2024",
]

# Industries the slot machine can land on.
INDUSTRIES = [
    "Technology",
    "Healthcare",
    "Energy",
    "Financials",
    "Consumer & Retail",
    "Auto & Transport",
]


def _s(ticker, name, multiple, blurb):
    return {"ticker": ticker, "name": name, "multiple": multiple, "blurb": blurb}


# CATALOG[industry][era] -> list of pickable stocks for that cell.
CATALOG = {
    "Technology": {
        "1990-1994": [
            _s("MSFT", "Microsoft", 4.2, "Windows 3.1 → 95 hype machine spins up."),
            _s("ORCL", "Oracle", 5.1, "Database king rides the enterprise boom."),
            _s("INTC", "Intel", 3.0, "Pentium launches; 'Intel Inside' everywhere."),
            _s("AAPL", "Apple", 0.9, "Pre-Jobs wilderness years. Newton flops."),
            _s("TXN", "Texas Instruments", 2.2, "Calculators-to-chips, steady climb."),
            _s("HPQ", "Hewlett-Packard", 3.0, "Printers and PCs mint cash."),
        ],
        "1995-1999": [
            _s("CSCO", "Cisco", 11.0, "Plumbing of the internet. Nearly most valuable co on Earth."),
            _s("QCOM", "Qualcomm", 18.0, "CDMA mania; 1999 alone was absurd."),
            _s("DELL", "Dell", 14.0, "Build-to-order PCs mint a generation of millionaires."),
            _s("AAPL", "Apple", 2.8, "Jobs returns, iMac lands. Comeback begins."),
            _s("MSFT", "Microsoft", 9.0, "Windows 95/98 monopoly mints money."),
            _s("EMC", "EMC", 20.0, "Storage king — one of the decade's best stocks."),
        ],
        "2000-2004": [
            _s("AAPL", "Apple", 1.9, "iPod (2001) plants the seed amid the wreckage."),
            _s("AMZN", "Amazon", 0.35, "Dot-com crash craters the stock ~90% off peak."),
            _s("MSFT", "Microsoft", 0.55, "Antitrust + burst bubble = dead money."),
            _s("PETS", "Pets.com", 0.0, "The sock puppet goes to zero. Bankrupt."),
            _s("EBAY", "eBay", 2.4, "Auctions survive the bust and grow."),
            _s("QCOM", "Qualcomm", 0.5, "Round-trips after the 1999 moonshot."),
        ],
        "2005-2009": [
            _s("AAPL", "Apple", 5.0, "iPhone (2007) changes everything."),
            _s("GOOG", "Google", 2.9, "Fresh IPO compounds through the crisis."),
            _s("AMZN", "Amazon", 2.7, "Prime + AWS quietly take shape."),
            _s("SUNW", "Sun Micro", 0.2, "Dot-com darling fades, sold to Oracle."),
            _s("CRM", "Salesforce", 4.0, "SaaS pioneer scales after its 2004 IPO."),
            _s("BKNG", "Booking (Priceline)", 6.0, "Negotiator-era turnaround into a travel giant."),
        ],
        "2010-2014": [
            _s("NFLX", "Netflix", 7.5, "Streaming pivot; survives Qwikster near-death."),
            _s("AAPL", "Apple", 2.9, "iPad era, becomes most valuable company."),
            _s("FB", "Meta (Facebook)", 2.1, "Botched IPO, then nails mobile ads."),
            _s("AMZN", "Amazon", 2.6, "AWS becomes a profit engine."),
            _s("GOOGL", "Google", 2.5, "Search + Android print money."),
            _s("CRM", "Salesforce", 3.0, "Cloud-software land grab continues."),
        ],
        "2015-2019": [
            _s("NVDA", "Nvidia", 11.0, "Gaming + crypto + early AI = GPU gold rush."),
            _s("AMD", "AMD", 10.0, "From ~$2 penny stock to comeback story."),
            _s("SHOP", "Shopify", 9.0, "Fresh IPO arms the e-commerce long tail."),
            _s("AAPL", "Apple", 2.0, "Services narrative kicks in."),
            _s("MSFT", "Microsoft", 3.0, "Nadella's cloud pivot reignites the giant."),
            _s("ADBE", "Adobe", 4.0, "Creative Cloud subscription flywheel."),
        ],
        "2020-2024": [
            _s("NVDA", "Nvidia", 13.0, "The AI supercycle. Trillion-dollar club."),
            _s("TSLA", "Tesla", 8.0, "S&P inclusion, retail mania, EV dominance."),
            _s("AMD", "AMD", 2.8, "Data-center share gains."),
            _s("ZM", "Zoom", 1.2, "Pandemic moonshot, then a long hangover."),
            _s("META", "Meta", 2.2, "Ad slump then a 2023 'Year of Efficiency' rip."),
            _s("AVGO", "Broadcom", 5.0, "Chips + VMware; rides the AI wave."),
        ],
    },
    "Healthcare": {
        "1990-1994": [
            _s("AMGN", "Amgen", 3.1, "Biotech pioneer; EPO and Neupogen scale."),
            _s("PFE", "Pfizer", 2.0, "Steady big-pharma compounding."),
            _s("JNJ", "Johnson & Johnson", 1.9, "Band-Aids to blockbusters."),
            _s("MRK", "Merck", 1.5, "Patent cliffs loom."),
            _s("LLY", "Eli Lilly", 1.8, "Prozac era cash machine."),
            _s("ABT", "Abbott", 2.0, "Diversified healthcare compounder."),
        ],
        "1995-1999": [
            _s("PFE", "Pfizer", 5.0, "Viagra (1998) is a phenomenon."),
            _s("MDT", "Medtronic", 4.2, "Pacemakers and stents boom."),
            _s("AMGN", "Amgen", 3.0, "Biotech keeps compounding."),
            _s("JNJ", "Johnson & Johnson", 3.1, "Healthcare bull market."),
            _s("LLY", "Eli Lilly", 3.5, "Zyprexa blockbuster drives the run."),
            _s("BMY", "Bristol-Myers Squibb", 3.0, "Big-pharma bull market darling."),
        ],
        "2000-2004": [
            _s("GILD", "Gilead Sciences", 3.2, "HIV franchise takes off."),
            _s("DNA", "Genentech", 2.1, "Avastin/Herceptin pipeline."),
            _s("PFE", "Pfizer", 0.7, "Post-bubble big pharma sags."),
            _s("AMGN", "Amgen", 1.4, "Maturing biotech."),
            _s("UNH", "UnitedHealth", 5.0, "Managed-care monster of the early 2000s."),
            _s("MDT", "Medtronic", 1.1, "Device leader treads water."),
        ],
        "2005-2009": [
            _s("ISRG", "Intuitive Surgical", 9.0, "da Vinci robots go mainstream."),
            _s("CELG", "Celgene", 5.0, "Revlimid drives the run."),
            _s("GILD", "Gilead Sciences", 3.0, "Antivirals keep compounding."),
            _s("JNJ", "Johnson & Johnson", 1.1, "Defensive through the crisis."),
            _s("ABT", "Abbott", 1.3, "Humira ramps; defensive through the crash."),
            _s("BMY", "Bristol-Myers Squibb", 1.0, "Patent cliffs, dividend safety."),
        ],
        "2010-2014": [
            _s("REGN", "Regeneron", 10.0, "Eylea launch is explosive."),
            _s("BIIB", "Biogen", 6.0, "MS franchise + Alzheimer's hope."),
            _s("GILD", "Gilead Sciences", 4.0, "Hep-C cure Sovaldi prints money."),
            _s("CELG", "Celgene", 4.0, "Blockbuster pipeline."),
            _s("BMY", "Bristol-Myers Squibb", 2.5, "Opdivo immuno-oncology bet pays."),
            _s("ABT", "Abbott", 1.8, "Spins off AbbVie, refocuses."),
        ],
        "2015-2019": [
            _s("UNH", "UnitedHealth", 3.0, "Managed care quietly compounds."),
            _s("VRTX", "Vertex", 3.0, "Cystic fibrosis monopoly."),
            _s("LLY", "Eli Lilly", 2.0, "Diabetes franchise builds."),
            _s("GILD", "Gilead Sciences", 0.7, "Hep-C revenue cliff."),
            _s("ABBV", "AbbVie", 1.6, "Humira cash funds the pipeline."),
            _s("DHR", "Danaher", 2.4, "Serial-acquirer compounding machine."),
        ],
        "2020-2024": [
            _s("LLY", "Eli Lilly", 5.5, "GLP-1 (Mounjaro/Zepbound) mania."),
            _s("NVO", "Novo Nordisk", 3.2, "Ozempic/Wegovy global craze."),
            _s("MRNA", "Moderna", 2.5, "COVID vaccine spike, then the hangover."),
            _s("PFE", "Pfizer", 0.9, "Vaccine boom unwinds."),
            _s("UNH", "UnitedHealth", 2.0, "Managed-care juggernaut keeps grinding."),
            _s("VRTX", "Vertex", 2.4, "CF monopoly + new pain/gene bets."),
        ],
    },
    "Energy": {
        "1990-1994": [
            _s("XOM", "Exxon", 1.5, "Big oil, steady as she goes."),
            _s("SLB", "Schlumberger", 1.8, "Oilfield services lead."),
            _s("CVX", "Chevron", 1.4, "Integrated major plods upward."),
            _s("HAL", "Halliburton", 1.6, "Services major grinds higher."),
        ],
        "1995-1999": [
            _s("ENE", "Enron", 3.0, "'Innovation' darling — for now."),
            _s("XOM", "Exxon", 1.9, "Mega-merger with Mobil."),
            _s("SLB", "Schlumberger", 1.6, "Services through a low-oil decade."),
            _s("HAL", "Halliburton", 1.3, "Cheney-era services, low-oil drag."),
            _s("CVX", "Chevron", 1.4, "Major holds steady pre-merger wave."),
        ],
        "2000-2004": [
            _s("VLO", "Valero", 3.2, "Refining margins explode."),
            _s("DVN", "Devon Energy", 3.0, "Rising oil lifts E&P."),
            _s("XOM", "Exxon", 1.4, "Crude grinds higher."),
            _s("ENE", "Enron", 0.0, "Accounting fraud collapse. Bankrupt."),
            _s("OXY", "Occidental", 2.6, "Rising crude lifts the E&P."),
        ],
        "2005-2009": [
            _s("CHK", "Chesapeake", 1.5, "Shale gas land grab, volatile."),
            _s("XOM", "Exxon", 1.3, "Oil to $147, then the crash."),
            _s("FSLR", "First Solar", 2.0, "Fresh IPO rides the clean-tech hype."),
            _s("SLB", "Schlumberger", 1.2, "Services whipsaw."),
            _s("OXY", "Occidental", 1.7, "Oil spike then crisis round-trip."),
            _s("COP", "ConocoPhillips", 1.1, "Integrated major rides the oil cycle."),
        ],
        "2010-2014": [
            _s("LNG", "Cheniere Energy", 5.0, "LNG export bet pays off."),
            _s("PXD", "Pioneer Natural", 3.0, "Permian shale boom."),
            _s("XOM", "Exxon", 1.4, "Steady through the shale era."),
            _s("FSLR", "First Solar", 0.4, "Solar glut crushes margins."),
            _s("EOG", "EOG Resources", 3.0, "Shale leader, best-in-class wells."),
            _s("VLO", "Valero", 4.0, "Refiner feasts on cheap shale crude."),
        ],
        "2015-2019": [
            _s("NEE", "NextEra Energy", 2.5, "Renewables utility outperforms."),
            _s("ENPH", "Enphase", 4.0, "Microinverters; late-decade breakout."),
            _s("XOM", "Exxon", 0.9, "Oil bust of 2015-16 lingers."),
            _s("CVX", "Chevron", 1.1, "Majors tread water."),
            _s("COP", "ConocoPhillips", 1.0, "Cuts dividend, survives the bust."),
            _s("VLO", "Valero", 1.2, "Refining margins ride out the slump."),
        ],
        "2020-2024": [
            _s("OXY", "Occidental", 2.2, "2022 oil spike + Buffett buying."),
            _s("XOM", "Exxon", 2.0, "Energy crisis windfall."),
            _s("ENPH", "Enphase", 1.6, "Solar boom then a brutal 2023-24."),
            _s("SEDG", "SolarEdge", 0.3, "Solar darling craters on rates."),
            _s("COP", "ConocoPhillips", 2.4, "Shale discipline + the energy windfall."),
            _s("DVN", "Devon Energy", 3.0, "Fixed-plus-variable dividend frenzy."),
        ],
    },
    "Financials": {
        "1990-1994": [
            _s("WFC", "Wells Fargo", 2.1, "Survives early-90s real-estate scare."),
            _s("BRK", "Berkshire Hathaway", 2.0, "Buffett compounding machine."),
            _s("JPM", "J.P. Morgan", 1.8, "Pre-mega-merger blue chip."),
            _s("AXP", "American Express", 1.6, "Charge-card franchise recovers."),
            _s("USB", "U.S. Bancorp", 2.0, "Steady regional-bank compounding."),
        ],
        "1995-1999": [
            _s("SCHW", "Charles Schwab", 16.0, "Online trading mania."),
            _s("C", "Citigroup", 5.0, "Travelers merger builds the supermarket."),
            _s("AIG", "AIG", 4.0, "Insurance juggernaut."),
            _s("BRK", "Berkshire Hathaway", 2.8, "Bull-market compounding."),
            _s("AXP", "American Express", 4.0, "Card spending booms with the bull."),
            _s("WFC", "Wells Fargo", 3.0, "Acquisitive bank rides the boom."),
        ],
        "2000-2004": [
            _s("GS", "Goldman Sachs", 1.3, "Newly public, steady."),
            _s("LEH", "Lehman Brothers", 2.0, "Riding the housing wave up."),
            _s("BRK", "Berkshire Hathaway", 1.3, "Defensive through the bust."),
            _s("AXP", "American Express", 1.1, "Recovers from the post-bubble swoon."),
            _s("WFC", "Wells Fargo", 1.3, "Mortgage boom tailwind."),
        ],
        "2005-2009": [
            _s("GS", "Goldman Sachs", 1.0, "Bailed, survives, round-trips."),
            _s("JPM", "J.P. Morgan", 1.0, "Buys Bear & WaMu, comes out ahead."),
            _s("LEH", "Lehman Brothers", 0.0, "September 2008. Bankrupt."),
            _s("AIG", "AIG", 0.05, "$182B bailout; near-total wipeout."),
            _s("WFC", "Wells Fargo", 0.9, "Buys Wachovia, scrapes through."),
            _s("AXP", "American Express", 0.7, "Card losses bite, then recovers."),
        ],
        "2010-2014": [
            _s("MA", "Mastercard", 4.5, "The toll-booth on global spending."),
            _s("V", "Visa", 3.2, "Payments compounding begins."),
            _s("BAC", "Bank of America", 1.3, "Slow crisis recovery."),
            _s("JPM", "J.P. Morgan", 2.0, "Fortress balance sheet."),
            _s("AXP", "American Express", 2.2, "Premium-card spend rebounds."),
            _s("GS", "Goldman Sachs", 1.3, "Trading recovers off the lows."),
        ],
        "2015-2019": [
            _s("SQ", "Block (Square)", 5.0, "Fresh IPO, fintech darling."),
            _s("MA", "Mastercard", 3.2, "Cashless tailwind continues."),
            _s("V", "Visa", 2.6, "Steady payments compounding."),
            _s("GS", "Goldman Sachs", 1.3, "Trading desk in a quiet decade."),
            _s("JPM", "J.P. Morgan", 2.0, "Best-in-class bank compounds."),
            _s("BLK", "BlackRock", 1.8, "ETF flywheel keeps gathering assets."),
        ],
        "2020-2024": [
            _s("JPM", "J.P. Morgan", 1.6, "Higher rates juice net interest income."),
            _s("V", "Visa", 1.5, "Spending rebounds post-COVID."),
            _s("HOOD", "Robinhood", 0.6, "Meme-stock IPO, then reality."),
            _s("SIVB", "SVB Financial", 0.0, "March 2023 bank run. Bankrupt."),
            _s("GS", "Goldman Sachs", 1.7, "Trading boom, then a consumer retreat."),
            _s("MS", "Morgan Stanley", 1.8, "Wealth-management pivot pays off."),
        ],
    },
    "Consumer & Retail": {
        "1990-1994": [
            _s("KO", "Coca-Cola", 3.0, "Buffett's favorite goes global."),
            _s("WMT", "Walmart", 2.2, "Supercenters carpet America."),
            _s("MCD", "McDonald's", 2.0, "Golden arches keep compounding."),
            _s("GPS", "Gap", 3.0, "Khakis-and-tees retail darling."),
            _s("HD", "Home Depot", 6.0, "Big-box DIY juggernaut of the era."),
            _s("DIS", "Disney", 2.5, "Animation renaissance + theme parks."),
        ],
        "1995-1999": [
            _s("SBUX", "Starbucks", 6.0, "A café on every corner."),
            _s("WMT", "Walmart", 4.0, "Retail behemoth scales."),
            _s("KO", "Coca-Cola", 2.8, "Nifty-Fifty redux."),
            _s("GPS", "Gap", 4.5, "Peak mall-era cool."),
            _s("HD", "Home Depot", 7.0, "Best-performing big-cap of the decade."),
            _s("DIS", "Disney", 1.6, "Steady but lagging the bull."),
        ],
        "2000-2004": [
            _s("SBUX", "Starbucks", 3.0, "Still in hyper-growth."),
            _s("KKD", "Krispy Kreme", 0.4, "Hot-doughnut bubble pops."),
            _s("WMT", "Walmart", 1.0, "Too big to sprint, dead money."),
            _s("KO", "Coca-Cola", 0.8, "Valuation hangover."),
            _s("COST", "Costco", 1.0, "Warehouse model digests the bubble."),
            _s("TGT", "Target", 1.6, "Cheap-chic 'Tarzhay' era begins."),
        ],
        "2005-2009": [
            _s("GMCR", "Green Mountain Coffee", 9.0, "Keurig pods go viral."),
            _s("MCD", "McDonald's", 2.2, "Defensive winner in the crisis."),
            _s("CMG", "Chipotle", 2.0, "Fresh IPO, burrito empire begins."),
            _s("CROX", "Crocs", 0.2, "Fad IPO craters in '08."),
            _s("NKE", "Nike", 1.4, "Swoosh holds up through the crash."),
            _s("DPZ", "Domino's", 0.7, "Pre-turnaround pizza, still a laggard."),
        ],
        "2010-2014": [
            _s("MNST", "Monster Beverage", 8.0, "Best-performing stock of the decade-ish."),
            _s("CMG", "Chipotle", 5.0, "Burrito mania peaks."),
            _s("UA", "Under Armour", 5.0, "Challenger-brand breakout."),
            _s("SBUX", "Starbucks", 4.0, "Reignites global growth."),
            _s("NKE", "Nike", 2.6, "Global swoosh keeps compounding."),
            _s("COST", "Costco", 2.3, "Membership flywheel hums."),
        ],
        "2015-2019": [
            _s("LULU", "Lululemon", 3.0, "Athleisure goes mainstream."),
            _s("DPZ", "Domino's", 3.0, "A tech company that sells pizza."),
            _s("COST", "Costco", 2.0, "Membership flywheel."),
            _s("CMG", "Chipotle", 1.3, "E. coli scare, then recovery."),
            _s("NKE", "Nike", 1.9, "Direct-to-consumer push pays off."),
            _s("MCD", "McDonald's", 1.9, "All-day breakfast reignites traffic."),
        ],
        "2020-2024": [
            _s("CROX", "Crocs", 5.0, "Comfort-fad redemption arc."),
            _s("COST", "Costco", 2.5, "Defensive compounder."),
            _s("WMT", "Walmart", 1.9, "Omnichannel finally clicks."),
            _s("PTON", "Peloton", 0.1, "Lockdown darling implodes."),
            _s("LULU", "Lululemon", 2.0, "Athleisure stays sticky post-pandemic."),
            _s("SBUX", "Starbucks", 1.3, "Reopening boom, then a China wobble."),
        ],
    },
    "Auto & Transport": {
        "1990-1994": [
            _s("HOG", "Harley-Davidson", 3.0, "Born-to-be-wild brand revival."),
            _s("F", "Ford", 2.0, "Trucks and Tauruses sell."),
            _s("GM", "General Motors", 1.5, "Detroit grinds back."),
            _s("CAT", "Caterpillar", 2.4, "Construction cycle lifts the machines."),
            _s("UNP", "Union Pacific", 2.0, "Rails roll through the recovery."),
        ],
        "1995-1999": [
            _s("TM", "Toyota", 1.6, "Quality reputation compounds."),
            _s("F", "Ford", 1.9, "SUV boom (Explorer)."),
            _s("HOG", "Harley-Davidson", 2.5, "Boomers buy bikes."),
            _s("CAT", "Caterpillar", 1.4, "Heavy machinery in a strong economy."),
            _s("UNP", "Union Pacific", 1.3, "Southern Pacific merger digestion."),
        ],
        "2000-2004": [
            _s("HOG", "Harley-Davidson", 2.0, "Brand still roaring."),
            _s("TM", "Toyota", 1.3, "Prius pioneers hybrids."),
            _s("GM", "General Motors", 0.9, "Legacy costs bite."),
            _s("F", "Ford", 0.7, "Market-share slide."),
            _s("UNP", "Union Pacific", 1.5, "Freight rebounds with the economy."),
            _s("CAT", "Caterpillar", 2.2, "China-led commodity boom lifts demand."),
        ],
        "2005-2009": [
            _s("F", "Ford", 0.6, "Skips bankruptcy, epic late rally off lows."),
            _s("TM", "Toyota", 0.8, "Recall era + crisis."),
            _s("GM", "General Motors", 0.0, "2009 bankruptcy. Wiped out."),
            _s("UNP", "Union Pacific", 1.4, "Rails grind through the crisis."),
            _s("CAT", "Caterpillar", 1.1, "Commodity-supercycle boom and bust."),
        ],
        "2010-2014": [
            _s("TSLA", "Tesla", 15.0, "2010 IPO to Model S mania."),
            _s("TM", "Toyota", 1.8, "Post-crisis recovery."),
            _s("F", "Ford", 1.3, "'One Ford' turnaround."),
            _s("GM", "General Motors", 1.2, "Re-IPO, steadies."),
            _s("UNP", "Union Pacific", 3.0, "Shale-and-trade freight boom."),
            _s("DAL", "Delta Air Lines", 4.0, "Out of bankruptcy, airlines re-rate."),
        ],
        "2015-2019": [
            _s("RACE", "Ferrari", 2.5, "Spun off; luxury multiple expands."),
            _s("TSLA", "Tesla", 1.5, "Model 3 'production hell', choppy."),
            _s("GM", "General Motors", 1.0, "Range-bound Detroit."),
            _s("F", "Ford", 0.7, "Sedan retreat weighs."),
            _s("UNP", "Union Pacific", 1.6, "Precision railroading lifts margins."),
            _s("CAT", "Caterpillar", 1.8, "Late-cycle industrial rebound."),
        ],
        "2020-2024": [
            _s("TSLA", "Tesla", 9.0, "S&P entry, split, retail frenzy."),
            _s("F", "Ford", 1.8, "EV pivot + meme bid."),
            _s("GM", "General Motors", 1.4, "Cruise + EV story."),
            _s("RIVN", "Rivian", 0.2, "2021 IPO hype meets cash burn."),
            _s("LCID", "Lucid", 0.25, "SPAC darling deflates."),
            _s("UBER", "Uber", 2.0, "From cash-burn to its first profits."),
            _s("CAT", "Caterpillar", 2.6, "Infrastructure + pricing power."),
        ],
    },
}


def cell(industry, era):
    """Return the list of catalog stocks for an (industry, era) cell."""
    return CATALOG[industry][era]
