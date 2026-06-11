// 100xPortfolio — client game loop.

const $ = (id) => document.getElementById(id);
const STORAGE_KEY = "100x_result";

// Display label for an era key: a clean 5-year span (e.g. "2020-2024" -> "2020-2025").
// The key still drives the game logic; this only changes how the span reads.
const eraLabel = (era) => {
  const start = parseInt(era.slice(0, 4), 10);
  return `${start}-${start + 5}`;
};

const state = {
  data: null, // daily payload from /api/daily
  round: 0, // current round index
  picks: [], // [{industry, era, ticker}]
  active: null, // active cell {industry, era, stocks}
  eraSkipUsed: false,
  industrySkipUsed: false,
  learn: null, // cached /api/learn payload (returns, for learning mode)
  learnMode: false, // when true, the run reveals each stock's return as you pick
};

// ---- boot ----------------------------------------------------------------
async function boot() {
  await loadRounds(); // today's shared daily spin
  renderProgress();

  $("start-btn").onclick = () => {
    state.learnMode = false;
    startGame();
  };
  $("skip-era").onclick = () => useSkip("era");
  $("skip-industry").onclick = () => useSkip("industry");
  $("copy-btn").onclick = copyResults;
  $("replay-btn").onclick = replay;

  $("learn-btn").onclick = startLearnGame;
  $("learn-btn-result").onclick = startLearnGame;

  if (loadSaved()) unlockLearn(); // already finished a game in a past session
}

// Learning mode unlocks only after the player completes at least one run.
function unlockLearn() {
  $("learn-btn").classList.remove("hidden");
}

// ---- learning mode -------------------------------------------------------
// The same game as a normal run, but every stock's 5-year return is shown on
// the pick rows so you learn which names mooned. Uses a fresh random spin (so
// you can practice freely) and never overwrites your saved daily result.
async function startLearnGame() {
  if (!state.learn) {
    state.learn = await fetch("/api/learn").then((r) => r.json());
  }
  state.learnMode = true;
  await loadRounds("learn-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8));
  startGame();
}

// ticker -> gainPct for one (industry, era) cell, from the revealed learn data.
function learnReturns(industry, era) {
  const rows = (state.learn.stocks[industry] || {})[era] || [];
  const map = {};
  rows.forEach((r) => {
    map[r.ticker] = r.gainPct;
  });
  return map;
}

// Fetch a round set. No seed -> today's shared daily; a seed -> a specific set.
async function loadRounds(seed) {
  const url = seed ? `/api/daily?seed=${encodeURIComponent(seed)}` : "/api/daily";
  state.data = await fetch(url).then((r) => r.json());
}

function startGame() {
  state.round = 0;
  state.picks = [];
  state.eraSkipUsed = false;
  state.industrySkipUsed = false;
  show("game");
  renderRound();
}

// Replay with a fresh random seed so the spins differ from the daily run.
async function replay() {
  await loadRounds("r-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8));
  startGame();
}

// ---- rendering -----------------------------------------------------------
function renderProgress() {
  const rail = $("progress-rail");
  rail.innerHTML = "";
  for (let i = 0; i < state.data.rounds.length; i++) {
    const pip = document.createElement("div");
    pip.className = "pip";
    if (i < state.round) pip.classList.add("done");
    else if (i === state.round) pip.classList.add("active");
    rail.appendChild(pip);
  }
}

function renderRound() {
  const rnd = state.data.rounds[state.round];
  state.active = rnd.cells.primary;

  renderProgress();
  $("round-counter").textContent = `Round ${state.round + 1} / ${state.data.rounds.length}`;
  $("skip-era").disabled = state.eraSkipUsed;
  $("skip-industry").disabled = state.industrySkipUsed;

  // Hide the company list while the reels are still spinning — it only makes
  // sense once the era + industry have landed.
  $("stock-grid").innerHTML = "";

  spinReels(rnd.era, rnd.industry, () => renderStocks());
}

function spinReels(finalEra, finalIndustry, done) {
  const eraReel = $("reel-era");
  const indReel = $("reel-industry");
  const eras = ["1990-1994", "1995-1999", "2000-2004", "2005-2009", "2010-2014", "2015-2019", "2020-2024"];
  const inds = ["Technology", "Healthcare", "Financials", "Consumer Discretionary", "Consumer Staples", "Industrials", "Utilities", "Materials"];

  eraReel.classList.add("spinning");
  indReel.classList.add("spinning");
  let ticks = 0;
  const spin = setInterval(() => {
    eraReel.textContent = eraLabel(eras[Math.floor(Math.random() * eras.length)]);
    indReel.textContent = inds[Math.floor(Math.random() * inds.length)];
    if (++ticks > 14) {
      clearInterval(spin);
      eraReel.classList.remove("spinning");
      indReel.classList.remove("spinning");
      eraReel.textContent = eraLabel(finalEra);
      indReel.textContent = finalIndustry;
      done();
    }
  }, 70);
}

function renderStocks() {
  const grid = $("stock-grid");
  grid.innerHTML = "";
  // Reflect any active skip in the reels.
  $("reel-era").textContent = eraLabel(state.active.era);
  $("reel-industry").textContent = state.active.industry;

  // In learning mode every return is on the table; otherwise stats stay hidden.
  const returns = state.learnMode ? learnReturns(state.active.industry, state.active.era) : null;

  const count = state.active.stocks.length;
  const header = document.createElement("div");
  header.className = "stock-list-head";
  header.textContent = returns
    ? `${count} stocks — returns shown, pick the one that mooned`
    : `${count} stocks — pick the one you think mooned`;
  grid.appendChild(header);

  const stocks = [...state.active.stocks].sort((a, b) => a.ticker.localeCompare(b.ticker));
  stocks.forEach((s) => {
    const row = document.createElement("div");
    row.className = "stock-row";
    // Curated blurb if we have one, otherwise the GICS sub-industry.
    const meta = s.blurb || s.sub || "";
    let pctCol = "";
    if (returns && returns[s.ticker] !== undefined) {
      const g = returns[s.ticker];
      const sign = g >= 0 ? "+" : "";
      pctCol = `<span class="stock-pct ${g >= 0 ? "up" : "down"}">${sign}${g}%</span>`;
    }
    row.innerHTML = `
      <span class="stock-ticker">${s.ticker}</span>
      <span class="stock-name">${s.name}</span>
      <span class="stock-meta">${meta}</span>${pctCol}`;
    row.onclick = () => pick(s.ticker);
    grid.appendChild(row);
  });
}

// ---- actions -------------------------------------------------------------
function useSkip(kind) {
  const rnd = state.data.rounds[state.round];
  if (kind === "era" && !state.eraSkipUsed) {
    state.eraSkipUsed = true;
    state.active = rnd.cells.altEra;
    $("skip-era").disabled = true;
  } else if (kind === "industry" && !state.industrySkipUsed) {
    state.industrySkipUsed = true;
    state.active = rnd.cells.altIndustry;
    $("skip-industry").disabled = true;
  }
  renderStocks();
}

function pick(ticker) {
  state.picks.push({
    industry: state.active.industry,
    era: state.active.era,
    ticker,
  });

  if (state.round + 1 >= state.data.rounds.length) {
    submit();
  } else {
    state.round += 1;
    renderRound();
  }
}

async function submit() {
  const res = await fetch("/api/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ picks: state.picks, seed: state.data.seed }),
  }).then((r) => r.json());

  if (res.error) {
    alert("Scoring error: " + res.error);
    return;
  }
  // A learning run is practice — don't overwrite the shared daily result/share.
  if (!state.learnMode) save({ day: state.data.day, result: res });
  unlockLearn();
  showResult(res, true);
}

// ---- result --------------------------------------------------------------
function showResult(res, animate) {
  show("result");

  // Sharing posts the saved daily result; a learning run isn't that, so hide it.
  $("copy-btn").classList.toggle("hidden", state.learnMode);
  $("learn-result-tag").classList.toggle("hidden", !state.learnMode);

  const badge = $("grade-badge");
  badge.textContent = res.grade;
  badge.className = "grade-badge " + res.gradeColor;

  $("result-multiple").textContent = res.multiple + "×";
  $("result-verdict").textContent = res.verdict;
  $("res-invested").textContent = usd(res.invested);
  $("res-final").textContent = usd(res.finalValue);

  const legs = $("result-legs");
  legs.innerHTML = "";
  res.legs.forEach((l, i) => {
    const cls = l.multiple >= 2 ? "up" : l.multiple >= 1 ? "flat" : "down";
    const sign = l.gainPct >= 0 ? "+" : "";
    const row = document.createElement("div");
    row.className = "leg";
    row.innerHTML = `
      <div class="leg-tag">#${i + 1} · ${eraLabel(l.era)} · ${l.industry}</div>
      <div class="leg-name">${l.name} <small>${l.ticker}</small></div>
      <div class="leg-mult ${cls}">${l.multiple}× <small>${sign}${l.gainPct}%</small></div>`;
    legs.appendChild(row);
  });

  $("best-pick").textContent = `${res.bestPick.name} (${res.bestPick.ticker}) — ${res.bestPick.multiple}×`;
  $("weak-pick").textContent = `${res.weakness.name} (${res.weakness.ticker}) — ${res.weakness.multiple}×`;

  renderBest(res);
}

// The best run that was achievable on these spins (perfect picks + optimal skips).
function renderBest(res) {
  const b = res.best;
  if (!b) return;
  $("best-final").textContent = usd(b.finalValue);
  $("best-multiple").textContent = b.multiple + "×";

  const pct = res.capturedPct;
  $("captured-pct").textContent = pct + "%";
  $("captured-bar").style.width = Math.max(0, Math.min(100, pct)) + "%";
  $("captured-line").textContent =
    pct >= 100
      ? "🏆 You nailed the perfect run. Diamond hands."
      : `You captured ${pct}% of the best possible run.`;

  const ideal = $("best-legs");
  ideal.innerHTML = "";
  b.legs.forEach((l, i) => {
    const row = document.createElement("div");
    row.className = "ideal-leg";
    row.innerHTML = `
      <span class="ideal-tag">${l.eraLabel} · ${l.industry}</span>
      <span class="ideal-name">${l.name} <small>${l.ticker}</small></span>
      <span class="ideal-mult">${l.multiple}×</span>`;
    ideal.appendChild(row);
  });
}

function copyResults() {
  const saved = loadSaved();
  if (!saved) return;
  const res = saved.result;

  // Three borderless columns per pick: performance emoji · ticker · % return.
  const rows = res.legs.map((l) => {
    const emoji = l.multiple >= 2 ? "🟩" : l.multiple >= 1 ? "🟨" : "🟥";
    const sign = l.gainPct >= 0 ? "+" : "";
    return { emoji, ticker: l.ticker, pct: `${sign}${Math.round(l.gainPct).toLocaleString("en-US")}%` };
  });
  const tickerW = Math.max(...rows.map((r) => r.ticker.length));
  const pctW = Math.max(...rows.map((r) => r.pct.length));
  const grid = rows
    .map((r) => `${r.emoji}  ${r.ticker.padEnd(tickerW)}  ${r.pct.padStart(pctW)}`)
    .join("\n");

  const retired = res.multiple >= 100 ? "did" : "did not";
  const pct = Math.round(res.gainPct).toLocaleString("en-US");
  const text = `I returned ${pct}% and ${retired} retire early. Can you beat me? 100xportfolio.vercel.app\n\n${grid}`;

  navigator.clipboard
    .writeText(text)
    .then(() => {
      const toast = $("share-toast");
      toast.classList.remove("hidden");
      setTimeout(() => toast.classList.add("hidden"), 2000);
    })
    .catch(() => alert(text));
}

// ---- helpers -------------------------------------------------------------
function show(id) {
  ["intro", "game", "result"].forEach((s) => $(s).classList.add("hidden"));
  $(id).classList.remove("hidden");
}

function usd(n) {
  return "$" + Math.round(n).toLocaleString("en-US");
}

function save(obj) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
  } catch (e) {
    /* ignore */
  }
}

function loadSaved() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY));
  } catch (e) {
    return null;
  }
}

boot();
