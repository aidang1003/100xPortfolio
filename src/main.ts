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
interface Cell { era: string; eraLabel: string; location: string; stocks: Stock[]; }
interface Round extends Cell {
  index: number;
  altEra: string;       // era skip target
  altEraLabel: string;
  altLocation: string;  // region skip target
}
// mode: "daily" (once per browser per day) | "practice"
interface Daily { seed: string; day: string; dayNumber: number; mode: string; rounds: Round[]; }

interface Leg {
  ticker: string; name: string; industry: string; era: string; eraLabel: string;
  location: string; hq: HQ | null; metrics: Metrics; multiple: number; gainPct: number;
  rank: number; cellSize: number; medal: string | null; perf: string; score?: number;
}
// One pick's outcome, from /api/reveal.
interface Reveal {
  ticker: string; multiple: number; gainPct: number; score: number;
  rank: number; cellSize: number; medal: string | null; perf: string;
}
interface Revealed extends Reveal { name: string; industry: string; location: string; }
interface BestLeg {
  ticker: string; name: string; industry: string; eraLabel: string; location: string;
  multiple: number; skips: string[];
}
interface Result {
  day: string; dayNumber: number; mode: string; seed: string; legs: Leg[]; invested: number; finalValue: number;
  multiple: number; gainPct: number; annualPct: number; gameScore?: number; investor: { name: string; photo: string; credit: string; wiki: string }; verdict: string; gradeColor: string; revealed?: boolean;
  bestPick: { ticker: string; name: string; multiple: number };
  weakness: { ticker: string; name: string; multiple: number };
  best: { annualPct: number; legs: BestLeg[] };
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

const $ = (id: string) => document.getElementById(id) as HTMLElement;
const STORAGE_KEY = "100x_result";
const SESSION_KEY = "100x_session";
const REGION_ADJ: Record<string, string> = {
  Northeast: "Northeastern", Midwest: "Midwestern", South: "Southern", West: "Western",
};
const MEDAL_EMOJI: Record<string, string> = { gold: "🥇", silver: "🥈", bronze: "🥉" };

const usd = (n: number) => "$" + Math.round(n).toLocaleString("en-US");
const ordinal = (n: number) => {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};

function metricLine(m: Metrics): string {
  const bits: string[] = [];
  if (m.price != null) bits.push(usd(m.price));
  if (m.pe != null) bits.push(`${m.pe}× P/E`);
  if (m.divYield != null) bits.push(`${m.divYield}% dividend`);
  return bits.join(" · ");
}

const dayTag = (mode: string, dayNumber: number) =>
  mode === "daily" ? `Daily Puzzle #${dayNumber}` : "Practice Mode";

function renderDayTag(el: HTMLElement, mode: string, dayNumber: number) {
  el.textContent = dayTag(mode, dayNumber);
  // Address bar follows the board in play: /d/N for the daily, / for practice.
  const path = mode === "daily" ? `/d/${dayNumber}` : "/";
  if (location.pathname !== path) history.replaceState(null, "", path);
  el.classList.toggle("daily", mode === "daily");
}

function industryStyle(industries: string[]): string {
  const colors = state.config.industryColors;
  const cs = industries.map((i) => colors[i] || "#888");
  return cs.length > 1 ? `linear-gradient(135deg, ${cs[0]}, ${cs[1]})` : cs[0];
}

const state = {
  config: null as unknown as Config,
  data: null as Daily | null,
  round: 0,
  active: null as Cell | null,
  skips: { era: false, location: false },  // spent this game
  swapped: { era: false, location: false }, // re-rolled this round
  picks: [] as PickChoice[],
  used: new Set<string>(),        // industries filled
  learn: null as LearnData | null,
  learnMode: false,
  screen: null as string | null,
  lastResult: null as Result | null,
  reveal: null as Revealed | null,  // card showing for the pick just made
  focus: null as string | null,     // open industry sorted to the top of the list
};

function snapshot() {
  return {
    screen: state.screen, seed: state.data?.seed, learnMode: state.learnMode,
    round: state.round, picks: state.picks, used: [...state.used], result: state.lastResult,
    skips: state.skips, reveal: state.reveal,
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

async function boot() {
  state.config = await fetch("/api/config").then((r) => r.json());
  applyIndustryColors();
  renderLegend();

  $("start-btn").onclick = () => { state.learnMode = false; startGame(); };
  $("skip-era").onclick = () => useSkip("era");
  $("skip-location").onclick = () => useSkip("location");
  $("lineup-bar").onclick = focusIndustry;
  $("lineup-bar").onkeydown = focusIndustry;
  $("copy-btn").onclick = copyResults;
  $("replay-btn").onclick = replay;
  $("brand").onclick = (e) => {
    e.preventDefault();
    const midGame = state.screen === "game" && state.picks.length > 0;
    if (!midGame || confirm("Start over? You'll lose your picks from this game.")) replay();
  };
  $("learn-btn").onclick = startLearnGame;
  $("learn-btn-result").onclick = startLearnGame;

  if (loadSaved()) $("learn-btn").classList.remove("hidden");

  const sess = loadSession();
  if (sess && (sess.screen === "game" || sess.screen === "result")) {
    try { await restoreSession(sess); return; } catch { /* fall through */ }
  }
  await loadRounds();
  // Daily already scored here: show it; Play again rolls practice.
  const saved = loadSaved();
  if (state.data!.mode === "practice" && saved?.day === state.data!.day) {
    showResult(saved.result);
    return;
  }
  renderProgress();
}

function applyIndustryColors() {
  const root = document.documentElement;
  for (const [ind, hex] of Object.entries(state.config.industryColors)) {
    root.style.setProperty(`--ind-${slug(ind)}`, hex);
  }
}
const slug = (s: string) => s.toLowerCase().replace(/[^a-z]+/g, "-");

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
  state.skips = { era: !!s.skips?.era, location: !!s.skips?.location };
  state.reveal = s.reveal || null;
  const rnd = state.data!.rounds[state.round];
  const a = s.active;  // may be a skipped-into cell
  state.active = a && (a.era !== rnd.era || a.location !== rnd.location)
    ? await loadCell(a.era, a.location) : rnd;
  state.swapped = { era: state.active.era !== rnd.era, location: state.active.location !== rnd.location };
  show("game");
  drawRound(false);
}

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
  state.skips = { era: false, location: false };
  state.picks = [];
  state.used = new Set();
  state.lastResult = null;
  state.reveal = null;
  disarmContinue();
  show("game");
  renderRound(true);
}

// Server deals the daily until it's scored here, then practice.
async function replay() {
  state.learnMode = false;
  await loadRounds();
  startGame();
}

async function startLearnGame() {
  if (!state.learn) state.learn = await fetch("/api/learn").then((r) => r.json());
  state.learnMode = true;
  await loadRounds();
  startGame();
}

// ticker -> gainPct (learning mode)
function learnReturns(era: string): Record<string, number> {
  const out: Record<string, number> = {};
  const byInd = state.learn!.stocks;
  for (const ind of Object.keys(byInd)) {
    for (const r of byInd[ind][era] || []) out[r.ticker] = r.gainPct;
  }
  return out;
}

function renderProgress() {
  const rail = $("progress-rail");
  rail.innerHTML = "";
  state.data!.rounds.forEach((_, i) => {
    const pip = document.createElement("div");
    pip.className = "pip" + (i < state.round ? " done" : i === state.round ? " active" : "");
    rail.appendChild(pip);
  });
}

function renderLineup() {
  const filled: Record<string, string> = {};
  for (const p of state.picks) filled[p.industry] = p.ticker;
  if (state.focus && state.used.has(state.focus)) state.focus = null;
  $("lineup-bar").innerHTML = state.config.industries.map((ind) => {
    const color = state.config.industryColors[ind] || "#888";
    const ticker = filled[ind];
    const focused = ind === state.focus;
    const style = ticker ? `background:${color}`
      : focused ? `border-color:${color};color:${color};background:${color}26`
      : `border-color:${color}55;color:${color}`;
    const open = ticker ? "" : ` open" role="button" tabindex="0" aria-pressed="${focused}`;
    return `<div class="slot-chip${ticker ? " filled" : ""}${open}" data-ind="${ind}" style="${style}">
      <span class="slot-ind">${ind}</span><span class="slot-pick">${ticker || ""}</span></div>`;
  }).join("");
}

// Clicking an open industry brings its stocks to the top; clicking it again clears that.
function focusIndustry(e: Event) {
  const chip = (e.target as HTMLElement).closest<HTMLElement>(".slot-chip.open");
  if (!chip || state.reveal || $("stock-grid").inert) return;
  if (e instanceof KeyboardEvent) {
    if (e.key !== "Enter" && e.key !== " ") return;
    e.preventDefault();
  }
  state.focus = state.focus === chip.dataset.ind ? null : chip.dataset.ind!;
  renderLineup();
  renderStocks();
}

function renderRound(animate: boolean) {
  state.active = state.data!.rounds[state.round];
  state.swapped = { era: false, location: false };
  state.focus = null;
  drawRound(animate);
}

function drawRound(animate: boolean) {
  const cell = state.active!;
  saveSession();
  renderDayTag($("day-tag"), state.data!.mode, state.data!.dayNumber);
  renderProgress();
  renderLineup();
  setSkipButtons();
  $("round-counter").textContent = `Pick ${state.round + 1} / ${state.data!.rounds.length}`;
  $("stock-grid").innerHTML = "";
  if (state.reveal) { setReels(cell); renderReveal(false); }
  else if (animate) spinReels(cell, () => renderStocks());
  else { setReels(cell); renderStocks(); }
}

const setReels = (cell: Cell) => {
  $("reel-era").textContent = cell.eraLabel;
  $("reel-location").textContent = cell.location;
};

// Learning mode skips are unlimited.
function setSkipButtons() {
  for (const kind of ["era", "location"] as const) {
    ($(`skip-${kind}`) as HTMLButtonElement).disabled = (state.skips[kind] && !state.learnMode) || !!state.reveal;
  }
}

async function useSkip(kind: "era" | "location") {
  if (state.skips[kind] && !state.learnMode) return;
  const rnd = state.data!.rounds[state.round];
  const btn = $(`skip-${kind}`);
  if (!state.learnMode) { state.skips[kind] = true; setSkipButtons(); }

  $("stock-grid").innerHTML = "";
  state.swapped[kind] = !state.swapped[kind];
  state.active = await loadCell(
    state.swapped.era ? rnd.altEra : rnd.era,
    state.swapped.location ? rnd.altLocation : rnd.location);
  saveSession();

  const cell = state.active;
  const reel = kind === "era" ? $("reel-era") : $("reel-location");
  const frames = kind === "era" ? state.config.eras.map((e) => state.config.eraLabels[e]) : state.config.locations;
  spinReel(reel, frames, kind === "era" ? cell.eraLabel : cell.location, () => {
    renderStocks();
    btn.blur();  // clear lingering focus highlight
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
  slide(grid, "in");
  const cell = state.active!;
  setReels(cell);

  const returns = state.learnMode ? learnReturns(cell.era) : null;
  // Pickable first, then the focused industry, then by dividend yield (learning mode:
  // by return); missing last.
  const isOpen = (s: Stock) => s.industries.some((i) => !state.used.has(i));
  const inFocus = (s: Stock) => !!state.focus && s.industries.includes(state.focus);
  const rank = (s: Stock) => (returns ? returns[s.ticker] : s.metrics.divYield) ?? -Infinity;
  const stocks = [...cell.stocks].sort((a, b) =>
    Number(isOpen(b)) - Number(isOpen(a)) || Number(inFocus(b)) - Number(inFocus(a)) ||
    rank(b) - rank(a) || a.name.localeCompare(b.name));

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
    if (open) row.onclick = () => pick(s, row);
    else row.title = "You've already used all of this company's industries";
    grid.appendChild(row);
  }
}

const revealCol = (g?: number) =>
  g === undefined ? "" : `<span class="stock-pct ${g >= 0 ? "up" : "down"}">${g >= 0 ? "+" : ""}${g}%</span>`;

async function pick(s: Stock, row: HTMLElement) {
  const industry = s.industries.find((i) => !state.used.has(i));
  if (!industry) return;
  const cell = state.active!;
  const grid = $("stock-grid");
  grid.inert = true;  // no second pick while the list slides away
  row.classList.add("picked");
  // Glide back up to the lineup while the list fades, both on one clock, so the short
  // card never lands while the page is still scrolled down a long list.
  const top = $("lineup-bar").getBoundingClientRect().top + scrollY - 12;
  const ms = Math.round(Math.min(700, Math.max(SLIDE.out.ms, Math.abs(scrollY - top) * 0.6)));
  const [out]: [Reveal & { error?: string }, void, void] = await Promise.all([
    fetch("/api/reveal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ era: cell.era, location: cell.location, ticker: s.ticker }),
    }).then((r) => r.json()),
    slide(grid, "out", ms),
    scrollY > top ? glideTo(top, ms) : Promise.resolve(),
  ]);
  if (out.error) { alert("Reveal error: " + out.error); renderStocks(); return; }

  state.picks.push({ era: cell.era, location: cell.location, ticker: s.ticker, industry });
  state.used.add(industry);
  state.reveal = { ...out, name: s.name, industry, location: cell.location };
  saveSession();
  renderLineup();
  setSkipButtons();
  renderReveal(true);
}

const REVEAL_MS = 1800;
const easeOut = (k: number) => 1 - (1 - k) ** 3;

// Out: a short drop and fade, then stay hidden. In: a slower, gentle rise into place.
// Small distance, soft easing: the content drifts in rather than landing hard.
const SLIDE = {
  out: { ms: 220, easing: "cubic-bezier(0.4, 0, 1, 1)" },
  in: { ms: 520, easing: "cubic-bezier(0.25, 0.8, 0.35, 1)" },
};
function slide(el: HTMLElement, dir: "in" | "out", ms = SLIDE[dir].ms): Promise<void> {
  const old = el.getAnimations();
  const low = { transform: "translateY(16px)", opacity: 0 };
  const home = { transform: "translateY(0)", opacity: 1 };
  const anim = el.animate(dir === "in" ? [low, home] : [home, low], {
    duration: ms,
    easing: SLIDE[dir].easing,
    fill: dir === "in" ? "backwards" : "forwards",
  });
  old.forEach((a) => a.cancel());  // after the new one starts, so nothing flashes
  return anim.finished.then(() => { if (dir === "in") el.inert = false; });
}

// Scroll on our own clock (native smooth scroll has no set duration).
function glideTo(top: number, ms: number): Promise<void> {
  const from = scrollY, dist = top - from;
  const easeInOut = (k: number) => (k < 0.5 ? 4 * k ** 3 : 1 - (-2 * k + 2) ** 3 / 2);
  return new Promise((done) => {
    const t0 = performance.now();
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / ms);
      scrollTo(0, from + dist * easeInOut(k));
      if (k < 1) requestAnimationFrame(step); else done();
    };
    requestAnimationFrame(step);
  });
}

async function renderReveal(animate: boolean) {
  const r = state.reveal!;
  const last = state.round + 1 >= state.data!.rounds.length;
  const sign = r.gainPct >= 0 ? "+" : "";
  const medal = r.medal ? ` ${MEDAL_EMOJI[r.medal]}` : "";
  $("stock-grid").innerHTML = `
    <div class="reveal card">
      <div class="reveal-rank">${ordinal(r.rank)} of ${r.cellSize} ${REGION_ADJ[r.location] || r.location} stocks${medal}</div>
      <div class="reveal-stock">
        <span class="stock-chip" style="background:${industryStyle([r.industry])}"></span>
        <span class="stock-ticker">${r.ticker}</span>
        <span class="reveal-name">${r.name}</span>
      </div>
      <div class="reveal-return ${r.multiple >= 2 ? "up" : r.multiple >= 1.5 ? "flat" : "down"}">${sign}${r.gainPct}%</div>
      <div class="reveal-score">
        <div class="captured-track"><div class="captured-fill" id="reveal-fill"></div></div>
        <div class="reveal-points"><b id="reveal-points">0</b> / 100</div>
      </div>
      <div class="reveal-continue">Click anywhere to ${last ? "see results" : "continue"}</div>
    </div>`;
  armContinue();

  const fill = $("reveal-fill"), points = $("reveal-points");
  fill.style.transition = "none";  // the frame loop below drives it
  const paint = (k: number) => {
    fill.style.width = r.score * k + "%";
    points.textContent = String(Math.round(r.score * k));
  };
  if (!animate) { slide($("stock-grid"), "in"); paint(1); return; }

  paint(0);
  await slide($("stock-grid"), "in");
  if (state.reveal !== r) return;  // already moved on
  const t0 = performance.now();
  const tick = (t: number) => {
    const k = Math.min(1, (t - t0) / REVEAL_MS);
    paint(easeOut(k));
    if (k < 1 && state.reveal === r) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

// While the card is up, any click (or Enter/Space) moves on. Links and buttons keep their own job.
let onContinue: ((e: Event) => void) | null = null;
function armContinue() {
  disarmContinue();
  onContinue = (e: Event) => {
    if (e instanceof KeyboardEvent) {
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
    } else if ((e.target as HTMLElement).closest("a, button")) return;
    disarmContinue();
    nextRound();
  };
  document.addEventListener("click", onContinue);
  document.addEventListener("keydown", onContinue);
}
function disarmContinue() {
  if (!onContinue) return;
  document.removeEventListener("click", onContinue);
  document.removeEventListener("keydown", onContinue);
  onContinue = null;
}

function nextRound() {
  if (state.round + 1 >= state.data!.rounds.length) { submit(); return; }  // card stays until scored
  state.reveal = null;
  state.round += 1;
  const grid = $("stock-grid");
  grid.inert = true;
  slide(grid, "out").then(() => renderRound(true));
}

async function submit() {
  const res: Result = await fetch("/api/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ picks: state.picks, seed: state.data!.seed }),
  }).then((r) => r.json());

  if (res.error) {
    alert("Scoring error: " + res.error);
    if (state.reveal) armContinue();
    return;
  }
  state.reveal = null;
  // Only the daily is saved.
  if (res.mode === "daily" && !state.learnMode) save({ day: res.day, result: res });
  $("learn-btn").classList.remove("hidden");
  showResult(res);
}

const annual = (pct: number) => (pct >= 0 ? "+" : "") + pct + "%/yr";

// The investor stays hidden until clicked; the reveal is saved with the result.
function renderInvestor(res: Result) {
  const badge = $("grade-badge") as HTMLImageElement;
  const label = $("result-investor");
  const shown = !!res.revealed;
  badge.src = shown ? res.investor.photo : "/static/investors/hidden.svg";
  badge.alt = badge.title = shown ? res.investor.credit : "Click to reveal";
  badge.className = "grade-badge " + (shown ? res.gradeColor : "unrevealed");
  label.textContent = shown ? "You invested like " : "Which legendary investor did you emulate?";
  if (shown) {
    const link = Object.assign(document.createElement("a"), {
      href: res.investor.wiki, target: "_blank", rel: "noopener", textContent: res.investor.name,
    });
    label.append(link);
  }
  label.classList.toggle("unrevealed", !shown);
  $("investor-badge").classList.toggle("unrevealed", !shown);
  badge.onclick = label.onclick = shown ? null : () => {
    res.revealed = true;
    saveSession();
    const saved = loadSaved();
    if (saved?.result?.seed === res.seed && !state.learnMode) save({ ...saved, result: res });
    renderInvestor(res);
  };
}

function showResult(res: Result) {
  state.lastResult = res;
  show("result");
  renderDayTag($("day-tag-result"), res.mode, res.dayNumber);
  $("copy-btn").classList.toggle("hidden", state.learnMode);
  $("learn-result-tag").classList.toggle("hidden", !state.learnMode);
  $("replay-btn").textContent = state.learnMode ? "Play regular" : "Play again";
  $("learn-btn-result").textContent = state.learnMode ? "Play again" : "Learning mode →";

  renderInvestor(res);
  $("result-multiple").textContent = res.multiple + "×";
  $("result-verdict").textContent = res.verdict;
  $("res-invested").textContent = usd(res.invested);
  $("res-final").textContent = usd(res.finalValue);
  $("res-annual").textContent = annual(res.annualPct);
  // Results saved before round scores existed have no score.
  const scored = res.gameScore != null;
  $("res-score-row").classList.toggle("hidden", !scored);
  if (scored) $("res-score").textContent = `${res.gameScore} / ${state.config.numRounds * 100}`;

  const legs = $("result-legs");
  legs.innerHTML = "";
  res.legs.forEach((l) => {
    const cls = l.perf || (l.multiple >= 2 ? "up" : l.multiple >= 1 ? "flat" : "down");
    const sign = l.gainPct >= 0 ? "+" : "";
    const medal = l.medal
      ? `<span class="leg-medal" title="${ordinal(l.rank)} of ${l.cellSize} in ${l.location}">${MEDAL_EMOJI[l.medal]}</span>`
      : "";
    const chip = `<span class="stock-chip" style="background:${industryStyle([l.industry])}"></span>`;
    const tag = `${l.industry} · ${l.eraLabel} · ${l.location}`;
    const row = document.createElement("div");
    row.className = "leg";
    row.innerHTML = `
      <div class="leg-tag" title="${tag}">${chip}${tag}</div>
      <div class="leg-name">${l.name}${medal}<small>${l.ticker}</small></div>
      <div class="leg-mult ${cls}">${l.multiple}× <small>${sign}${l.gainPct}%</small></div>`;
    legs.appendChild(row);
  });

  $("best-pick").textContent = `${res.bestPick.name} (${res.bestPick.ticker}) · ${res.bestPick.multiple}×`;
  $("weak-pick").textContent = `${res.weakness.name} (${res.weakness.ticker}) · ${res.weakness.multiple}×`;
  renderBest(res);
}

function renderBest(res: Result) {
  $("best-annual").textContent = annual(res.best.annualPct);
  const pct = res.capturedPct;
  $("captured-pct").textContent = pct + "%";
  ($("captured-bar") as HTMLElement).style.width = Math.max(0, Math.min(100, pct)) + "%";
  $("captured-line").textContent = pct >= 100
    ? "🏆 You nailed the perfect lineup. Diamond hands."
    : `You captured ${pct}% of the best possible portfolio.`;

  const ideal = $("best-legs");
  ideal.innerHTML = "";
  res.best.legs.forEach((l) => {
    const row = document.createElement("div");
    row.className = "ideal-leg";
    row.innerHTML = `
      <span class="ideal-tag">${l.industry} · ${l.eraLabel} · ${l.location}${
        l.skips.map((k) => ` <span class="skip-chip">↻ ${k} skip</span>`).join("")}</span>
      <span class="ideal-name">${l.name}<small>${l.ticker}</small></span>
      <span class="ideal-mult">${l.multiple}×</span>`;
    ideal.appendChild(row);
  });
}

function shareText(res: Result): string {
  const rows = res.legs.map((l) => ({
    emoji: l.multiple >= 2 ? "🟩" : l.multiple >= 1 ? "🟨" : "🟥",
    cell: `${l.eraLabel} ${l.location}`,
    pct: `${l.gainPct >= 0 ? "+" : ""}${Math.round(l.gainPct).toLocaleString("en-US")}%`,
  }));
  const cW = Math.max(...rows.map((r) => r.cell.length));
  const pW = Math.max(...rows.map((r) => r.pct.length));
  const grid = rows.map((r) => `${r.emoji}  ${r.cell.padEnd(cW)}  ${r.pct.padStart(pW)}`).join("\n");
  const link = res.mode === "daily" ? `https://play100x.com/d/${res.dayNumber}` : "https://play100x.com";
  const headline = `${res.multiple >= 100 ? "I retired with" : "I made"} ${res.multiple}x, can you beat me? ${link}`;
  return `Play 100x: ${dayTag(res.mode, res.dayNumber)}\n${headline}\n\n${grid}`;
}

let toastTimer = 0;
function flashCopied() {
  const toast = $("copy-toast");
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("show"), 2000);
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
  try {
    if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(text); flashCopied(); return; }
  } catch { /* fall through */ }
  if (legacyCopy(text)) { flashCopied(); return; }
  window.prompt("Copy your result:", text);
}

function show(id: string) {
  ["intro", "game", "result"].forEach((s) => $(s).classList.add("hidden"));
  $(id).classList.remove("hidden");
  state.screen = id;
  saveSession();
}

boot();
