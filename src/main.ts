// 100xPortfolio — client game loop (TypeScript).
//
// The game: each round deals an ERA × HQ-LOCATION. You pick one company
// headquartered there; across your five picks you must field five DISTINCT
// industries (multi-industry names are flexible). Stake rolls pick to pick.

// ---- API types -----------------------------------------------------------
interface HQ { city: string; state: string; region: string; }
interface Metrics { pe?: number; price?: number; divYield?: number; }

interface Stock {
  ticker: string;
  name: string;
  sub: string;
  hq: HQ | null;
  industries: string[];
  metrics: Metrics;
}
// One (era, region) cell of the board: what the reels show and what you pick from.
interface Cell { era: string; eraLabel: string; location: string; stocks: Stock[]; }
interface Round extends Cell {
  index: number;
  altEra: string;       // the cell an era skip re-rolls into (same region)
  altEraLabel: string;
  altLocation: string;  // the cell a region skip re-rolls into (same era)
}
interface Daily { seed: string; day: string; rounds: Round[]; }

interface Leg {
  ticker: string; name: string; industry: string; era: string; eraLabel: string;
  location: string; hq: HQ | null; metrics: Metrics; multiple: number; gainPct: number;
  rank: number; cellSize: number; medal: string | null; perf: string;
}
interface BestLeg { ticker: string; name: string; industry: string; eraLabel: string; multiple: number; }
interface Result {
  day: string; seed: string; legs: Leg[]; invested: number; finalValue: number;
  multiple: number; gainPct: number; grade: string; verdict: string; gradeColor: string;
  bestPick: { ticker: string; name: string; multiple: number };
  weakness: { ticker: string; name: string; multiple: number };
  best: { multiple: number; finalValue: number; legs: BestLeg[] };
  capturedPct: number;
  error?: string;
}
interface Config {
  startingStake: number; numRounds: number; industryColors: Record<string, string>;
  eras: string[]; eraLabels: Record<string, string>; industries: string[]; locations: string[];
  industryBlurbs: Record<string, string>;
}
interface PickChoice { era: string; location: string; ticker: string; industry: string; }
interface LearnData { stocks: Record<string, Record<string, { ticker: string; gainPct: number }[]>>; }

// ---- helpers -------------------------------------------------------------
const $ = (id: string) => document.getElementById(id) as HTMLElement;
const STORAGE_KEY = "100x_result";
const SESSION_KEY = "100x_session";
const MEDAL_EMOJI: Record<string, string> = { gold: "🥇", silver: "🥈", bronze: "🥉" };

const usd = (n: number) => "$" + Math.round(n).toLocaleString("en-US");
const ordinal = (n: number) => {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

// Format the entry-metric row (price · P/E · yield); omit whatever's missing.
function metricLine(m: Metrics): string {
  const bits: string[] = [];
  if (m.price != null) bits.push(usd(m.price));
  if (m.pe != null) bits.push(`${m.pe}× P/E`);
  if (m.divYield != null) bits.push(`${m.divYield}% yield`);
  return bits.join(" · ");
}

// Solid industry color, or a gradient for a multi-industry stock.
function industryStyle(industries: string[]): string {
  const colors = state.config.industryColors;
  const cs = industries.map((i) => colors[i] || "#888");
  return cs.length > 1 ? `linear-gradient(135deg, ${cs[0]}, ${cs[1]})` : cs[0];
}

// ---- state ---------------------------------------------------------------
const state = {
  config: null as unknown as Config,
  data: null as Daily | null,
  round: 0,
  active: null as Cell | null,    // the cell in play; a skip swaps it for an alternate
  skipUsed: false,                // one re-roll per game, era or region
  picks: [] as PickChoice[],
  used: new Set<string>(),        // industries already filled (one per industry)
  learn: null as LearnData | null,
  learnMode: false,
  screen: null as string | null,
  lastResult: null as Result | null,
};

// ---- session persistence (resume across a refresh) -----------------------
function snapshot() {
  return {
    screen: state.screen, seed: state.data?.seed, learnMode: state.learnMode,
    round: state.round, picks: state.picks, used: [...state.used], result: state.lastResult,
    skipUsed: state.skipUsed,
    active: state.active && { era: state.active.era, location: state.active.location },
  };
}
function saveSession() {
  try { sessionStorage.setItem(SESSION_KEY, JSON.stringify(snapshot())); } catch { /* ignore */ }
}
function loadSession(): any {
  try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || "null"); } catch { return null; }
}
function save(obj: unknown) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(obj)); } catch { /* ignore */ }
}
function loadSaved(): any {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"); } catch { return null; }
}

// ---- boot ----------------------------------------------------------------
async function boot() {
  state.config = await fetch("/api/config").then((r) => r.json());
  applyIndustryColors();
  renderLegend();

  $("start-btn").onclick = () => { state.learnMode = false; startGame(); };
  $("skip-era").onclick = () => useSkip("era");
  $("skip-location").onclick = () => useSkip("location");
  $("copy-btn").onclick = copyResults;
  $("replay-btn").onclick = replay;
  $("learn-btn").onclick = startLearnGame;
  $("learn-btn-result").onclick = startLearnGame;

  if (loadSaved()) $("learn-btn").classList.remove("hidden");

  const sess = loadSession();
  if (sess && (sess.screen === "game" || sess.screen === "result")) {
    try { await restoreSession(sess); return; } catch { /* fall through */ }
  }
  await loadRounds();
  renderProgress();
}

// Expose industry colors as CSS variables (--ind-<slug>) for chips/legends.
function applyIndustryColors() {
  const root = document.documentElement;
  for (const [ind, hex] of Object.entries(state.config.industryColors)) {
    root.style.setProperty(`--ind-${slug(ind)}`, hex);
  }
}
const slug = (s: string) => s.toLowerCase().replace(/[^a-z]+/g, "-");

// Intro screen: the five industries a lineup must cover, with what's in each.
function renderLegend() {
  $("industry-legend").innerHTML = state.config.industries.map((ind) => `
    <li><span class="legend-dot" style="background:${industryStyle([ind])}"></span>
      <span class="legend-name">${ind}</span>
      <span class="legend-blurb">${state.config.industryBlurbs[ind] || ""}</span></li>`).join("");
}

async function restoreSession(s: any) {
  state.learnMode = !!s.learnMode;
  if (state.learnMode && !state.learn) state.learn = await fetch("/api/learn").then((r) => r.json());
  await loadRounds(s.seed);

  if (s.screen === "result" && s.result) { state.lastResult = s.result; showResult(s.result); return; }

  state.round = s.round || 0;
  state.picks = Array.isArray(s.picks) ? s.picks : [];
  state.used = new Set<string>(s.used || []);
  state.skipUsed = !!s.skipUsed;
  const rnd = state.data!.rounds[state.round];
  const a = s.active;  // resume on the skipped-into cell, not the primary
  state.active = a && (a.era !== rnd.era || a.location !== rnd.location)
    ? await loadCell(a.era, a.location) : rnd;
  show("game");
  drawRound(false);
}

// ---- data ----------------------------------------------------------------
const cells = new Map<string, Cell>();
async function loadCell(era: string, location: string): Promise<Cell> {
  const key = `${era}|${location}`;
  if (!cells.has(key)) {
    const q = `era=${encodeURIComponent(era)}&location=${encodeURIComponent(location)}`;
    cells.set(key, await fetch(`/api/cell?${q}`).then((r) => r.json()));
  }
  return cells.get(key)!;
}

async function loadRounds(seed?: string) {
  const url = seed ? `/api/daily?seed=${encodeURIComponent(seed)}` : "/api/daily";
  state.data = await fetch(url).then((r) => r.json());
}

function startGame() {
  state.round = 0;
  state.skipUsed = false;
  state.picks = [];
  state.used = new Set();
  state.lastResult = null;
  show("game");
  renderRound(true);
}

async function replay() {
  state.learnMode = false;
  await loadRounds("r-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8));
  startGame();
}

async function startLearnGame() {
  if (!state.learn) state.learn = await fetch("/api/learn").then((r) => r.json());
  state.learnMode = true;
  await loadRounds("learn-" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8));
  startGame();
}

// ticker -> gainPct across every industry in an era (learning mode reveal).
function learnReturns(era: string): Record<string, number> {
  const out: Record<string, number> = {};
  const byInd = state.learn!.stocks;
  for (const ind of Object.keys(byInd)) {
    for (const r of byInd[ind][era] || []) out[r.ticker] = r.gainPct;
  }
  return out;
}

// ---- rendering -----------------------------------------------------------
function renderProgress() {
  const rail = $("progress-rail");
  rail.innerHTML = "";
  state.data!.rounds.forEach((_, i) => {
    const pip = document.createElement("div");
    pip.className = "pip" + (i < state.round ? " done" : i === state.round ? " active" : "");
    rail.appendChild(pip);
  });
}

// The lineup: one slot per industry, dim until a pick fills it with a ticker.
function renderLineup() {
  const filled: Record<string, string> = {};
  for (const p of state.picks) filled[p.industry] = p.ticker;
  $("lineup-bar").innerHTML = state.config.industries.map((ind) => {
    const color = state.config.industryColors[ind] || "#888";
    const ticker = filled[ind];
    const style = ticker ? `background:${color}` : `border-color:${color}55;color:${color}`;
    return `<div class="slot-chip${ticker ? " filled" : ""}" style="${style}">
      <span class="slot-ind">${ind}</span><span class="slot-pick">${ticker || ""}</span></div>`;
  }).join("");
}

function renderRound(animate: boolean) {
  state.active = state.data!.rounds[state.round];
  drawRound(animate);
}

function drawRound(animate: boolean) {
  const cell = state.active!;
  saveSession();
  renderProgress();
  renderLineup();
  setSkipButtons();
  $("round-counter").textContent = `Pick ${state.round + 1} / ${state.data!.rounds.length}`;
  $("stock-grid").innerHTML = "";
  if (animate) spinReels(cell, () => renderStocks());
  else { setReels(cell); renderStocks(); }
}

const setReels = (cell: Cell) => {
  $("reel-era").textContent = cell.eraLabel;
  $("reel-location").textContent = cell.location;
};

// One re-roll per game, spent on either reel; learning mode re-rolls freely.
function setSkipButtons() {
  const spent = state.skipUsed && !state.learnMode;
  for (const id of ["skip-era", "skip-location"]) ($(id) as HTMLButtonElement).disabled = spent;
}

async function useSkip(kind: "era" | "location") {
  if (state.skipUsed && !state.learnMode) return;
  const rnd = state.data!.rounds[state.round];
  const btn = $(kind === "era" ? "skip-era" : "skip-location");
  if (!state.learnMode) { state.skipUsed = true; setSkipButtons(); }

  $("stock-grid").innerHTML = "";  // hide the list while the reel re-rolls
  state.active = kind === "era"
    ? await loadCell(rnd.altEra, rnd.location)
    : await loadCell(rnd.era, rnd.altLocation);
  saveSession();

  const cell = state.active;
  const reel = kind === "era" ? $("reel-era") : $("reel-location");
  const frames = kind === "era" ? state.config.eras.map((e) => state.config.eraLabels[e]) : state.config.locations;
  spinReel(reel, frames, kind === "era" ? cell.eraLabel : cell.location, () => {
    renderStocks();
    btn.blur();  // drop the lingering activation highlight on the button
  });
}

function spinReel(reel: HTMLElement, frames: string[], finalText: string, done?: () => void) {
  reel.classList.add("spinning");
  let ticks = 0;
  const id = setInterval(() => {
    reel.textContent = frames[Math.floor(Math.random() * frames.length)];
    if (++ticks > 14) {
      clearInterval(id);
      reel.classList.remove("spinning");
      reel.textContent = finalText;
      done?.();
    }
  }, 70);
}

function spinReels(cell: Cell, done: () => void) {
  const eraFrames = state.config.eras.map((e) => state.config.eraLabels[e]);
  spinReel($("reel-era"), eraFrames, cell.eraLabel);
  spinReel($("reel-location"), state.config.locations, cell.location, done);
}

function renderStocks() {
  const grid = $("stock-grid");
  grid.innerHTML = "";
  const cell = state.active!;
  setReels(cell);

  const returns = state.learnMode ? learnReturns(cell.era) : null;
  // Still-pickable companies first, then by dividend yield (learning mode ranks
  // by return instead, since that's the column it reveals). Non-payers sort last.
  const isOpen = (s: Stock) => s.industries.some((i) => !state.used.has(i));
  const rank = (s: Stock) => (returns ? returns[s.ticker] : s.metrics.divYield) ?? -Infinity;
  const stocks = [...cell.stocks].sort((a, b) =>
    Number(isOpen(b)) - Number(isOpen(a)) || rank(b) - rank(a) || a.name.localeCompare(b.name));

  const head = document.createElement("div");
  head.className = "stock-list-head";
  head.textContent = returns
    ? `${stocks.length} companies in ${cell.location} · returns shown`
    : `${stocks.length} companies in ${cell.location} · pick one to fill an industry`;
  grid.appendChild(head);

  for (const s of stocks) {
    const open = isOpen(s);
    const row = document.createElement("div");
    row.className = "stock-row" + (open ? "" : " disabled");

    const chip = `<span class="stock-chip" style="background:${industryStyle(s.industries)}"
      title="${s.industries.join(" / ")}"></span>`;
    const hq = s.hq && s.hq.city ? `${s.hq.city}, ${s.hq.state}` : (s.hq?.region || "");
    const detail = returns
      ? revealCol(returns[s.ticker])
      : `<span class="stock-metrics">${metricLine(s.metrics) || s.sub}</span>`;

    row.innerHTML = `
      ${chip}
      <span class="stock-ticker">${s.ticker}</span>
      <span class="stock-name">${s.name}<small class="stock-hq">${hq}</small></span>
      ${detail}`;
    if (open) row.onclick = () => pick(s);
    else row.title = "You've already used all of this company's industries";
    grid.appendChild(row);
  }
}

const revealCol = (g?: number) =>
  g === undefined ? "" : `<span class="stock-pct ${g >= 0 ? "up" : "down"}">${g >= 0 ? "+" : ""}${g}%</span>`;

// ---- actions -------------------------------------------------------------
function pick(s: Stock) {
  const industry = s.industries.find((i) => !state.used.has(i));
  if (!industry) return; // no open slot (row is disabled anyway)
  const cell = state.active!;
  state.picks.push({ era: cell.era, location: cell.location, ticker: s.ticker, industry });
  state.used.add(industry);

  if (state.round + 1 >= state.data!.rounds.length) submit();
  else { state.round += 1; renderRound(true); }
}

async function submit() {
  const res: Result = await fetch("/api/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ picks: state.picks, seed: state.data!.seed }),
  }).then((r) => r.json());

  if (res.error) { alert("Scoring error: " + res.error); return; }
  if (!state.learnMode) save({ day: state.data!.day, result: res });
  $("learn-btn").classList.remove("hidden");
  showResult(res);
}

// ---- result --------------------------------------------------------------
function showResult(res: Result) {
  state.lastResult = res;
  show("result");
  $("copy-btn").classList.toggle("hidden", state.learnMode);
  $("learn-result-tag").classList.toggle("hidden", !state.learnMode);
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
    const cls = l.perf || (l.multiple >= 2 ? "up" : l.multiple >= 1 ? "flat" : "down");
    const sign = l.gainPct >= 0 ? "+" : "";
    const medal = l.medal
      ? `<span class="leg-medal" title="${ordinal(l.rank)} of ${l.cellSize} in ${l.location}">${MEDAL_EMOJI[l.medal]}</span>`
      : "";
    const chip = `<span class="stock-chip" style="background:${industryStyle([l.industry])}"></span>`;
    const row = document.createElement("div");
    row.className = "leg";
    row.innerHTML = `
      <div class="leg-tag">${chip}#${i + 1} · ${l.eraLabel} · ${l.location} · ${l.industry}</div>
      <div class="leg-name">${medal}${l.name} <small>${l.ticker}</small></div>
      <div class="leg-mult ${cls}">${l.multiple}× <small>${sign}${l.gainPct}%</small></div>`;
    legs.appendChild(row);
  });

  $("best-pick").textContent = `${res.bestPick.name} (${res.bestPick.ticker}) · ${res.bestPick.multiple}×`;
  $("weak-pick").textContent = `${res.weakness.name} (${res.weakness.ticker}) · ${res.weakness.multiple}×`;
  renderBest(res);
}

function renderBest(res: Result) {
  const b = res.best;
  $("best-final").textContent = usd(b.finalValue);
  $("best-multiple").textContent = b.multiple + "×";
  const pct = res.capturedPct;
  $("captured-pct").textContent = pct + "%";
  ($("captured-bar") as HTMLElement).style.width = Math.max(0, Math.min(100, pct)) + "%";
  $("captured-line").textContent = pct >= 100
    ? "🏆 You nailed the perfect lineup. Diamond hands."
    : `You captured ${pct}% of the best possible lineup.`;

  const ideal = $("best-legs");
  ideal.innerHTML = "";
  b.legs.forEach((l) => {
    const row = document.createElement("div");
    row.className = "ideal-leg";
    row.innerHTML = `
      <span class="ideal-tag">${l.eraLabel} · ${l.industry}</span>
      <span class="ideal-name">${l.name} <small>${l.ticker}</small></span>
      <span class="ideal-mult">${l.multiple}×</span>`;
    ideal.appendChild(row);
  });
}

// ---- share ---------------------------------------------------------------
function shareText(res: Result): string {
  const rows = res.legs.map((l) => ({
    emoji: l.multiple >= 2 ? "🟩" : l.multiple >= 1 ? "🟨" : "🟥",
    ticker: l.ticker,
    pct: `${l.gainPct >= 0 ? "+" : ""}${Math.round(l.gainPct).toLocaleString("en-US")}%`,
  }));
  const tW = Math.max(...rows.map((r) => r.ticker.length));
  const pW = Math.max(...rows.map((r) => r.pct.length));
  const grid = rows.map((r) => `${r.emoji}  ${r.ticker.padEnd(tW)}  ${r.pct.padStart(pW)}`).join("\n");
  const pct = Math.round(res.gainPct).toLocaleString("en-US");
  const headline = res.multiple >= 100
    ? `I retired with ${pct}% gains, can you beat me? play100x.com`
    : `I returned ${pct}%, can you beat me? play100x.com`;
  return `${headline}\n\n${grid}`;
}

function flashToast() {
  const t = $("share-toast");
  t.classList.remove("hidden");
  setTimeout(() => t.classList.add("hidden"), 2000);
}

function legacyCopy(text: string): boolean {
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
  } catch { return false; }
}

async function copyResults() {
  const res = state.lastResult || (loadSaved() && loadSaved().result);
  if (!res) return;
  const text = shareText(res);
  if (navigator.share) {
    try { await navigator.share({ text }); return; }
    catch (e: any) { if (e && e.name === "AbortError") return; }
  }
  try {
    if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(text); flashToast(); return; }
  } catch { /* fall through */ }
  if (legacyCopy(text)) { flashToast(); return; }
  window.prompt("Copy your result:", text);
}

// ---- screens -------------------------------------------------------------
function show(id: string) {
  ["intro", "game", "result"].forEach((s) => $(s).classList.add("hidden"));
  $(id).classList.remove("hidden");
  state.screen = id;
  saveSession();
}

boot();
