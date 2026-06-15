// 100xPortfolio — client game loop.

const $ = (id) => document.getElementById(id);
const STORAGE_KEY = "100x_result";
const MEDAL_EMOJI = { gold: "🥇", silver: "🥈", bronze: "🥉" };

// 1 -> "1st", 2 -> "2nd", 3 -> "3rd", 4 -> "4th" ...
const ordinal = (n) => {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

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
  activeKind: "primary", // which cell is active this round: primary | altEra | altIndustry
  eraSkipUsed: false,
  industrySkipUsed: false,
  learn: null, // cached /api/learn payload (returns, for learning mode)
  learnMode: false, // when true, the run reveals each stock's return as you pick
  screen: null, // current visible screen, for refresh restore
  lastResult: null, // last scored result, for refresh restore
};

// A snapshot of where the player is, kept in sessionStorage so a page refresh
// (especially mobile pull-to-refresh) resumes instead of bouncing to the intro.
const SESSION_KEY = "100x_session";

function snapshot() {
  return {
    screen: state.screen,
    seed: state.data && state.data.seed,
    learnMode: state.learnMode,
    round: state.round,
    picks: state.picks,
    activeKind: state.activeKind,
    eraSkipUsed: state.eraSkipUsed,
    industrySkipUsed: state.industrySkipUsed,
    result: state.lastResult,
  };
}

function saveSession() {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(snapshot()));
  } catch (e) {
    /* ignore */
  }
}

function loadSession() {
  try {
    return JSON.parse(sessionStorage.getItem(SESSION_KEY));
  } catch (e) {
    return null;
  }
}

// ---- boot ----------------------------------------------------------------
async function boot() {
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

  // Resume an in-progress game or result across a refresh; else fresh daily.
  const sess = loadSession();
  if (sess && (sess.screen === "game" || sess.screen === "result")) {
    try {
      await restoreSession(sess);
      return;
    } catch (e) {
      /* fall through to a clean daily boot */
    }
  }

  await loadRounds(); // today's shared daily spin
  renderProgress();
}

// Rebuild the saved screen after a refresh. Seeds are deterministic, so
// re-fetching the same seed reproduces the exact rounds the player was on.
async function restoreSession(s) {
  state.learnMode = !!s.learnMode;
  if (state.learnMode && !state.learn) {
    state.learn = await fetch("/api/learn").then((r) => r.json());
  }
  await loadRounds(s.seed || undefined);

  if (s.screen === "result" && s.result) {
    state.lastResult = s.result;
    showResult(s.result, false);
    return;
  }

  state.round = s.round || 0;
  state.picks = Array.isArray(s.picks) ? s.picks : [];
  state.activeKind = s.activeKind || "primary";
  state.eraSkipUsed = !!s.eraSkipUsed;
  state.industrySkipUsed = !!s.industrySkipUsed;
  show("game");
  resumeRound();
}

// Render the current round without the slot animation (we're resuming, not spinning).
function resumeRound() {
  const rnd = state.data.rounds[state.round];
  state.active = rnd.cells[state.activeKind] || rnd.cells.primary;
  renderProgress();
  $("round-counter").textContent = `Round ${state.round + 1} / ${state.data.rounds.length}`;
  $("skip-era").disabled = state.eraSkipUsed;
  $("skip-industry").disabled = state.industrySkipUsed;
  renderStocks(); // sets the reels + pick list from state.active
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
  state.lastResult = null;
  show("game");
  renderRound();
}

// Replay with a fresh random seed so the spins differ from the daily run.
// This is always a regular run ("Play again" in regular, "Play regular" in learning).
async function replay() {
  state.learnMode = false;
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
  state.activeKind = "primary";
  saveSession(); // persist the round advance for refresh-resume

  renderProgress();
  $("round-counter").textContent = `Round ${state.round + 1} / ${state.data.rounds.length}`;
  $("skip-era").disabled = state.eraSkipUsed;
  $("skip-industry").disabled = state.industrySkipUsed;

  // Hide the company list while the reels are still spinning — it only makes
  // sense once the era + industry have landed.
  $("stock-grid").innerHTML = "";

  spinReels(rnd.era, rnd.industry, () => renderStocks());
}

// Values the reels flash through while spinning.
const SPIN_ERAS = ["1990-1994", "1995-1999", "2000-2004", "2005-2009", "2010-2014", "2015-2019", "2020-2024"];
const SPIN_INDUSTRIES = ["Technology", "Healthcare", "Financials", "Consumer Discretionary", "Consumer Staples", "Industrials", "Utilities", "Materials"];

// Flash one reel through random frames, then settle on finalText.
function spinReel(reel, frames, finalText, done) {
  reel.classList.add("spinning");
  let ticks = 0;
  const id = setInterval(() => {
    reel.textContent = frames[Math.floor(Math.random() * frames.length)];
    if (++ticks > 14) {
      clearInterval(id);
      reel.classList.remove("spinning");
      reel.textContent = finalText;
      if (done) done();
    }
  }, 70);
}

function spinReels(finalEra, finalIndustry, done) {
  // Both reels spin the same number of frames, so they land together; the
  // industry reel fires the shared `done` callback.
  spinReel($("reel-era"), SPIN_ERAS.map(eraLabel), eraLabel(finalEra), null);
  spinReel($("reel-industry"), SPIN_INDUSTRIES, finalIndustry, done);
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

  // Learning mode: rank best-to-worst by return, and keep rows compact (just
  // ticker, name, %) so they fit on a phone. The game keeps its A–Z list +
  // descriptions with stats hidden.
  const stocks = [...state.active.stocks];
  if (returns) {
    stocks.sort((a, b) => (returns[b.ticker] ?? -Infinity) - (returns[a.ticker] ?? -Infinity));
  } else {
    stocks.sort((a, b) => a.ticker.localeCompare(b.ticker));
  }

  stocks.forEach((s) => {
    const row = document.createElement("div");
    row.className = "stock-row";
    if (returns) {
      const g = returns[s.ticker];
      let pctCol = "";
      if (g !== undefined) {
        const sign = g >= 0 ? "+" : "";
        pctCol = `<span class="stock-pct ${g >= 0 ? "up" : "down"}">${sign}${g}%</span>`;
      }
      row.innerHTML = `
        <span class="stock-ticker">${s.ticker}</span>
        <span class="stock-name">${s.name}</span>${pctCol}`;
    } else {
      // Curated blurb if we have one, otherwise the GICS sub-industry.
      const meta = s.blurb || s.sub || "";
      row.innerHTML = `
        <span class="stock-ticker">${s.ticker}</span>
        <span class="stock-name">${s.name}</span>
        <span class="stock-meta">${meta}</span>`;
    }
    row.onclick = () => pick(s.ticker);
    grid.appendChild(row);
  });
}

// ---- actions -------------------------------------------------------------
// A skip re-rolls the era (or industry) and lands on the alternate cell. The
// server picks that alternate at random excluding the original, so a skip can
// never land on the era/industry the player already had. We spin only the
// re-rolled reel and rebuild the list once it settles.
//
// Learning mode gets unlimited skips: the buttons are never consumed/disabled,
// so you can keep re-rolling to study other eras and industries.
function useSkip(kind) {
  const rnd = state.data.rounds[state.round];
  const unlimited = state.learnMode;
  let reel, frames, finalText;
  if (kind === "era" && (unlimited || !state.eraSkipUsed)) {
    if (!unlimited) {
      state.eraSkipUsed = true;
      $("skip-era").disabled = true;
    }
    state.active = rnd.cells.altEra;
    state.activeKind = "altEra";
    reel = $("reel-era");
    frames = SPIN_ERAS.map(eraLabel);
    finalText = eraLabel(state.active.era);
  } else if (kind === "industry" && (unlimited || !state.industrySkipUsed)) {
    if (!unlimited) {
      state.industrySkipUsed = true;
      $("skip-industry").disabled = true;
    }
    state.active = rnd.cells.altIndustry;
    state.activeKind = "altIndustry";
    reel = $("reel-industry");
    frames = SPIN_INDUSTRIES;
    finalText = state.active.industry;
  } else {
    return; // skip already spent (regular mode)
  }
  saveSession();
  $("stock-grid").innerHTML = ""; // hide picks while the reel re-rolls
  spinReel(reel, frames, finalText, () => renderStocks());
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
  state.lastResult = res; // captured before show() so the session snapshot has it
  show("result");

  // Sharing posts the saved daily result; a learning run isn't that, so hide it.
  $("copy-btn").classList.toggle("hidden", state.learnMode);
  $("learn-result-tag").classList.toggle("hidden", !state.learnMode);

  // Same two play buttons in the same slots; only the labels flip by mode.
  // replay-btn always starts a regular run; learn-btn-result always learning.
  $("replay-btn").textContent = state.learnMode ? "Play regular" : "Play again";
  $("learn-btn-result").textContent = state.learnMode ? "Play again" : "Learning mode →";

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
    // Color reflects standing in the era/industry dealt (top/mid/worst third);
    // a medal marks a top-3 finish in that cell.
    const cls = l.perf || (l.multiple >= 2 ? "up" : l.multiple >= 1 ? "flat" : "down");
    const sign = l.gainPct >= 0 ? "+" : "";
    const medal = l.medal
      ? `<span class="leg-medal" title="${ordinal(l.rank)} of ${l.cellSize} in this era/industry">${MEDAL_EMOJI[l.medal]}</span>`
      : "";
    const row = document.createElement("div");
    row.className = "leg";
    row.innerHTML = `
      <div class="leg-tag">#${i + 1} · ${eraLabel(l.era)} · ${l.industry}</div>
      <div class="leg-name">${medal}${l.name} <small>${l.ticker}</small></div>
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

function shareText(res) {
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

  const pct = Math.round(res.gainPct).toLocaleString("en-US");
  const headline =
    res.multiple >= 100
      ? `I Retired with ${pct}% gains, can you beat me? play100x.com`
      : `I returned ${pct}%, can you beat me? play100x.com`;
  return `${headline}\n\n${grid}`;
}

function flashToast() {
  const toast = $("share-toast");
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2000);
}

// Legacy clipboard path for browsers without the Async Clipboard API
// (e.g. Brave on iOS with shields blocking it). Returns true on success.
function legacyCopy(text) {
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "-1000px";
    document.body.appendChild(ta);
    ta.select();
    ta.setSelectionRange(0, text.length);
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch (e) {
    return false;
  }
}

// Share the result. Prefer the native share sheet (best on mobile, and what a
// "Share" button implies), then fall back to clipboard, then to manual copy —
// each guarded so a blocked/absent API never silently no-ops the button.
async function copyResults() {
  // Use the result on screen, not localStorage — survives blocked storage and
  // a refresh-restored result.
  const res = state.lastResult || (loadSaved() && loadSaved().result);
  if (!res) return;
  const text = shareText(res);

  if (navigator.share) {
    try {
      await navigator.share({ text });
      return; // shared via the OS sheet
    } catch (e) {
      if (e && e.name === "AbortError") return; // user dismissed — not an error
      // otherwise fall through to copying
    }
  }

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      flashToast();
      return;
    }
  } catch (e) {
    /* fall through to legacy copy */
  }

  if (legacyCopy(text)) {
    flashToast();
    return;
  }

  // Last resort: surface the text so it can be copied by hand.
  window.prompt("Copy your result:", text);
}

// ---- helpers -------------------------------------------------------------
function show(id) {
  ["intro", "game", "result"].forEach((s) => $(s).classList.add("hidden"));
  $(id).classList.remove("hidden");
  state.screen = id;
  saveSession();
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
