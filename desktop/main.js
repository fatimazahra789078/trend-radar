// Trend Radar desktop app (Windows + macOS).
// - shows the online dashboard in its own window
// - lives in the tray / menu bar and starts with the computer
// - listens to your ntfy topic and shows native notifications, filtered by YOUR choices:
//   importance, countries, topics and types (also the ones missed while the computer slept)
// The radar itself runs in the cloud (GitHub Actions), so this app needs nothing else installed.
const { app, BrowserWindow, Tray, Menu, Notification, shell, ipcMain, nativeImage, powerMonitor, screen } = require("electron");
const path = require("path");
const fs = require("fs");
const https = require("https");
const crypto = require("crypto");

const DEFAULT_URL = "https://fatimazahra789078.github.io/trend-radar/";
const DEFAULT_SERVER = "https://ntfy.sh";
const FLAGS = { us: "🇺🇸", de: "🇩🇪", gb: "🇬🇧", fr: "🇫🇷", it: "🇮🇹", es: "🇪🇸", eu: "🇪🇺" };
const COUNTRIES = [["us", "🇺🇸 USA"], ["de", "🇩🇪 Germany / Austria / Switzerland"], ["gb", "🇬🇧 UK"], ["fr", "🇫🇷 France"],
                   ["it", "🇮🇹 Italy"], ["es", "🇪🇸 Spain"], ["eu", "🇪🇺 Europe-wide"], ["world", "🌐 Rest of the world / no country"]];
const CATEGORIES = ["Politics", "World & conflicts", "Natural disasters", "Crime & accidents", "Sports", "Movies & TV",
                    "Music", "Gaming", "Tech & AI", "AI video & image", "Business", "Celebs & viral"];
const TYPES = [
  ["BREAKING", "Breaking news (trusted sources)"], ["JUST IN", "Just in (4+ news sites in the last hour)"],
  ["HOT", "Hot trends"], ["REPEATING", "Trends that keep coming back (day 2, 3, 5, 7)"], ["TRENDING", "Trending"],
  ["TOP NEWS", "Top news stories"], ["DISASTER", "Natural disasters (quakes, storms, floods...)"],
  ["SPORTS RESULT", "Results of big games"], ["LIVE", "Big games starting"], ["WATCHLIST", "Your watchlist words"],
  ["BRIEFING", "Claude briefing (09:00 and 18:00)"], ["DIGEST", "Top trends every 3 hours"],
  ["MUSIC CHART", "Music charts (new #1, new top 10)"], ["EVENT", "Upcoming event reminders"],
  ["SPREADING", "A trend reaches a new country"], ["SUMMARY", "While you were away"],
  ["AI MODEL", "New AI video / image / voice model (Hugging Face)"], ["AI TOOLS", "News about AI tools (Seedance, Kling, Veo...)"],
  ["GITHUB", "GitHub repos everyone is starring (trending + new AI tools)"],
];
const NEW_TYPES = ["GITHUB"];   // types added after 1.3.1: switched on for people who saved their types before
const IMPORTANCE = [[4, "Very important only", "Breaking, hot, just in, repeating trends, big disasters, briefing"],
                    [3, "Important + trending", "Also normal trends, top news, sports results, watchlist"],
                    [1, "Everything", "Also digests, music charts, reminders"]];
const COUNTRYLESS_OK = ["WATCHLIST", "BRIEFING", "DIGEST", "SUMMARY", "AI MODEL", "AI TOOLS", "GITHUB"];
const ICON = path.join(__dirname, "build", "icon.png");
const START_HIDDEN = process.argv.includes("--hidden");

let win = null, settingsWin = null, tray = null, cfg = {}, req = null, retryMs = 5000, retryTimer = null;
let quitting = false, pausedUntil = 0, connected = false;
const recent = new Map();

// ---------------------------------------------------------------- settings
const cfgFile = () => path.join(app.getPath("userData"), "settings.json");
function loadCfg() {
  try { cfg = JSON.parse(fs.readFileSync(cfgFile(), "utf8")); } catch { cfg = {}; }
  cfg.url = cfg.url || DEFAULT_URL;
  cfg.server = cfg.server || DEFAULT_SERVER;
  if (![1, 3, 4].includes(cfg.minPriority)) cfg.minPriority = 4;           // default: very important only
  if (!Array.isArray(cfg.countries) || !cfg.countries.length) cfg.countries = COUNTRIES.map(([v]) => v);
  if (!Array.isArray(cfg.categories) || !cfg.categories.length) cfg.categories = [...CATEGORIES];
  if (!Array.isArray(cfg.types) || !cfg.types.length) cfg.types = TYPES.map(([v]) => v);
  // a new alert type is ON by default, also for people who saved their own choice of types before it existed
  const known = Array.isArray(cfg.typesKnown) ? cfg.typesKnown : TYPES.map(([v]) => v).filter((v) => !NEW_TYPES.includes(v));
  for (const [v] of TYPES) if (!known.includes(v) && !cfg.types.includes(v)) cfg.types.push(v);
  cfg.typesKnown = TYPES.map(([v]) => v);
  if (cfg.autostart === undefined) cfg.autostart = true;
  if (cfg.briefAuto === undefined) cfg.briefAuto = true;
  if (!Array.isArray(cfg.briefTimes)) cfg.briefTimes = ["09:00", "18:00"];
  cfg.briefLang = cfg.briefLang || "English";
  if (!app.isPackaged && process.env.TR_TEST_TOPIC) { cfg.topic = process.env.TR_TEST_TOPIC; cfg.__test = true; } // developer test only
}
function saveCfg() {
  if (cfg.__test) return;   // never store a developer test topic
  try { fs.mkdirSync(path.dirname(cfgFile()), { recursive: true }); fs.writeFileSync(cfgFile(), JSON.stringify(cfg, null, 1)); } catch {}
}
function applyAutostart() {
  if (!app.isPackaged) return;
  app.setLoginItemSettings({ openAtLogin: !!cfg.autostart, openAsHidden: true, args: ["--hidden"] });
}

// ---------------------------------------------------------------- the filter
function passes(ev) {
  const tags = ev.tags || [];
  const label = tags.find((t) => TYPES.some(([v]) => v === t)) || "";
  const cat = tags.find((t) => CATEGORIES.includes(t)) || "";
  const flags = tags.filter((t) => FLAGS[t]);
  if ((ev.priority || 3) < cfg.minPriority) return false;
  if (label && !cfg.types.includes(label)) return false;
  if (cat && !cfg.categories.includes(cat)) return false;
  if (flags.length) return flags.some((f) => cfg.countries.includes(f));
  return cfg.countries.includes("world") || COUNTRYLESS_OK.includes(label);
}

// ---------------------------------------------------------------- windows
function defaultHash() {
  const only = cfg.countries.filter((c) => c !== "world");
  return only.length === 1 ? only[0] : "";
}
function dashboardUrl(hash) {
  const h = hash === undefined ? defaultHash() : hash;
  return cfg.url.replace(/#.*$/, "") + (h ? "#" + h : "");
}

function createWindow(show = true) {
  win = new BrowserWindow({
    width: 1300, height: 880, minWidth: 380, minHeight: 500, show: false, title: "Trend Radar",
    backgroundColor: "#0a0f1d", icon: ICON, autoHideMenuBar: false,
    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false },
  });
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https?:/.test(url)) shell.openExternal(url); return { action: "deny" }; });
  win.webContents.on("will-navigate", (e, url) => {
    try { if (new URL(url).origin !== new URL(cfg.url).origin) { e.preventDefault(); shell.openExternal(url); } } catch {}
  });
  win.webContents.on("did-fail-load", (_e, code, _d, _url, isMain) => {
    if (!isMain || code === -3) return;
    win.loadFile(path.join(__dirname, "offline.html"));
    setTimeout(() => win && !win.isDestroyed() && win.loadURL(dashboardUrl()), 20000);
  });
  win.on("close", (e) => { if (!quitting) { e.preventDefault(); win.hide(); } });
  win.once("ready-to-show", () => { if (show) win.show(); });
  win.loadURL(dashboardUrl());
}

function showDashboard(hash) {
  if (!win || win.isDestroyed()) createWindow(true);
  if (hash !== undefined) win.loadURL(dashboardUrl(hash));
  win.show(); win.focus();
}

function openSettings(section) {
  const target = typeof section === "string" ? section : "";
  if (settingsWin && !settingsWin.isDestroyed()) {
    if (target) settingsWin.webContents.executeJavaScript(`document.getElementById(${JSON.stringify(target)})?.scrollIntoView()`).catch(() => {});
    settingsWin.show(); settingsWin.focus(); return;
  }
  settingsWin = new BrowserWindow({
    width: 640, height: Math.min(860, screen.getPrimaryDisplay().workAreaSize.height - 40), resizable: true, title: "Trend Radar - Settings", backgroundColor: "#0a0f1d", icon: ICON,
    autoHideMenuBar: true,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true },
  });
  settingsWin.removeMenu();
  settingsWin.loadFile(path.join(__dirname, "settings.html"), target ? { hash: target } : {});
}

// ---------------------------------------------------------------- tray / menu bar
function setQuick(change) {
  Object.assign(cfg, change); saveCfg(); buildTray();
  if (change.countries && win && !win.isDestroyed()) win.loadURL(dashboardUrl());
}
function buildTray() {
  const size = process.platform === "darwin" ? 18 : 16;
  const img = nativeImage.createFromPath(ICON).resize({ width: size, height: size });
  if (!tray) {
    tray = new Tray(img);
    tray.setToolTip("Trend Radar");
    tray.on("click", () => showDashboard());
  }
  const paused = Date.now() < pausedUntil;
  const only = (list) => cfg.countries.length === list.length && list.every((c) => cfg.countries.includes(c));
  const all = COUNTRIES.map(([v]) => v);
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "Open Trend Radar", click: () => showDashboard() },
    { type: "separator" },
    { label: "💡 Video ideas", click: () => showDashboard("ideas") },
    { label: "🌍 Disasters", click: () => showDashboard("disasters") },
    { label: "⚽ Sports", click: () => showDashboard("sports") },
    { label: "🎬 AI tools & GitHub", click: () => showDashboard("ai") },
    { type: "separator" },
    { label: "🧠 Write briefing now", click: () => makeBriefing(true).then((r) => { if (!r.ok) notify({ title: "🧠 AI briefing", body: r.msg }); }) },
    { label: "🧠 Show last briefing", enabled: fs.existsSync(briefFile()), click: showBriefing },
    { type: "separator" },
    { label: "Notify me about", submenu: IMPORTANCE.map(([p, l]) => ({ label: l, type: "radio", checked: cfg.minPriority === p, click: () => setQuick({ minPriority: p }) })) },
    { label: "Countries", submenu: [
      { label: "All countries", type: "radio", checked: only(all), click: () => setQuick({ countries: all }) },
      { label: "🇺🇸 USA only", type: "radio", checked: only(["us"]), click: () => setQuick({ countries: ["us"] }) },
      { label: "🇩🇪 Germany only", type: "radio", checked: only(["de"]), click: () => setQuick({ countries: ["de"] }) },
      { label: "🇪🇺 Europe only", type: "radio", checked: only(["de", "gb", "fr", "it", "es", "eu"]), click: () => setQuick({ countries: ["de", "gb", "fr", "it", "es", "eu"] }) },
      { label: "🇺🇸 + 🇩🇪 USA and Germany", type: "radio", checked: only(["us", "de"]), click: () => setQuick({ countries: ["us", "de"] }) },
      { type: "separator" },
      { label: "More choices in Settings...", click: openSettings },
    ] },
    { type: "separator" },
    { label: cfg.topic ? (connected ? "● Connected" : "○ Connecting...") : "⚠ Set your topic in Settings", enabled: false },
    paused ? { label: "Resume notifications", click: () => { pausedUntil = 0; buildTray(); } }
           : { label: "Pause notifications for 1 hour", click: () => { pausedUntil = Date.now() + 3600e3; buildTray(); } },
    { label: "Settings...", click: openSettings },
    { type: "separator" },
    { label: "Quit Trend Radar", click: () => { quitting = true; app.quit(); } },
  ]));
}

// ---------------------------------------------------------------- notifications (ntfy stream)
function connect() {
  clearTimeout(retryTimer);
  if (req) { try { req.destroy(); } catch {} req = null; }
  connected = false;
  if (!cfg.topic) { buildTray(); return; }
  // "-all" = every alert; the filter above decides what you see.
  // since = last message we saw -> alerts that came while the computer slept are shown too (ntfy keeps 12h)
  const since = cfg.lastTime ? String(cfg.lastTime + 1) : "2m";
  const url = `${cfg.server.replace(/\/$/, "")}/${encodeURIComponent(cfg.topic + "-all")}/json?since=${encodeURIComponent(since)}`;
  req = https.get(url, { headers: { "User-Agent": "TrendRadar-Desktop/1.1" } }, (res) => {
    if (res.statusCode !== 200) { res.resume(); return scheduleRetry(); }
    connected = true; retryMs = 5000; buildTray();
    let buf = "";
    res.setEncoding("utf8");
    res.on("data", (chunk) => {
      buf += chunk;
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
        if (!line) continue;
        try { const ev = JSON.parse(line); if (ev.event === "message") handleMessage(ev); } catch {}
      }
    });
    res.on("end", scheduleRetry);
    res.on("error", scheduleRetry);
  });
  req.on("error", scheduleRetry);
  req.setTimeout(90000, () => { try { req.destroy(); } catch {} });   // ntfy sends a keepalive every ~45s
}

function scheduleRetry() {
  connected = false; buildTray();
  clearTimeout(retryTimer);
  retryTimer = setTimeout(connect, retryMs);
  retryMs = Math.min(retryMs * 2, 60000);
}

function handleMessage(ev) {
  cfg.lastTime = Math.max(cfg.lastTime || 0, ev.time || 0);
  saveCfg();
  const key = crypto.createHash("sha1").update((ev.title || "") + "|" + (ev.message || "")).digest("hex");
  const now = Date.now();
  for (const [k, t] of recent) if (now - t > 15 * 60e3) recent.delete(k);
  if (recent.has(key)) return;
  recent.set(key, now);
  if ((ev.tags || []).includes("BRIEFING")) { cfg.lastCloudBrief = now; saveCfg(); }
  const ok = now >= pausedUntil && passes(ev);
  if (process.env.TR_DEBUG) console.log(`[filter] ${ok ? "SHOW" : "skip"} p=${ev.priority} tags=${(ev.tags || []).join(",")} ${ev.title}`);
  if (!ok) return;
  const tags = ev.tags || [];
  const flags = tags.map((t) => FLAGS[t]).filter(Boolean).join("");
  const extra = tags.filter((t) => !FLAGS[t]).join(" · ");
  notify({
    title: (flags ? flags + " " : "") + (ev.title || "Trend Radar"),
    body: (ev.message || "") + (extra ? `\n[${extra}]` : ""),
    click: ev.click, urgent: (ev.priority || 3) >= 5,
  });
}

function notify({ title, body, click, urgent, onClick }) {
  if (!Notification.isSupported()) return;
  const n = new Notification({ title: title.slice(0, 200), body: (body || "").slice(0, 900), icon: ICON, urgency: urgent ? "critical" : "normal" });
  n.on("click", () => (onClick ? onClick() : click && /^https?:/.test(click) ? shell.openExternal(click) : showDashboard()));
  n.show();
}

// ---------------------------------------------------------------- AI briefing with Google Gemini (free key, on this PC)
const GEMINI = (!app.isPackaged && process.env.TR_GEMINI_URL) || "https://generativelanguage.googleapis.com/v1beta"; // test override (dev only)
const BRIEF_LANGS = ["English", "Moroccan Darija in Latin letters", "French", "German", "Arabic", "Spanish", "Italian"];
let briefWin = null, briefBusy = false;
const briefFile = () => path.join(app.getPath("userData"), "briefing.md");

async function gemini(pathPart, body) {
  const r = await fetch(`${GEMINI}/${pathPart}`, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json", "x-goog-api-key": cfg.geminiKey },
    body: body ? JSON.stringify(body) : undefined,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((j.error && j.error.message) || `HTTP ${r.status}`);
  return j;
}

async function pickModel() {
  if (cfg.geminiModel) return cfg.geminiModel.startsWith("models/") ? cfg.geminiModel : "models/" + cfg.geminiModel;
  try {
    const j = await gemini("models?pageSize=200");
    let best = null;
    for (const m of j.models || []) {
      if (!(m.supportedGenerationMethods || []).includes("generateContent")) continue;
      const mm = /^models\/gemini-(\d+(?:\.\d+)?)-flash(-[a-z0-9.-]+)?$/.exec(m.name);
      if (!mm || /lite|image|tts|audio|live|exp|thinking|8b/.test(m.name)) continue;
      const rank = parseFloat(mm[1]) * 10 + (mm[2] ? 0 : 1);
      if (!best || rank > best[0]) best = [rank, m.name];
    }
    return best ? best[1] : "models/gemini-2.5-flash";
  } catch { return "models/gemini-2.5-flash"; }
}

function briefPrompt(data, when) {
  return `You write the "Trend Radar" briefing for a video creator who makes short trend videos for audiences in the
USA, Germany, UK, France, Italy and Spain. Below is a JSON snapshot of what is trending now.
Use ONLY this data - never invent facts, numbers, results, quotes or dates.
Choose the 5 best topics for a video right now. Prefer: just_in, high score, new (small first_pub_h = hours since the
first article), many articles in the last hour (recent1), trending in several audience countries, and categories that
bring views (celebs, movies & TV, music, gaming, sports, tech, AI tools, natural disasters). At most 2 politics topics.
${cfg.countries.length < 8 ? `Focus on these countries: ${cfg.countries.join(", ")}.` : ""}
Write in ${cfg.briefLang || "English"}. Simple markdown, max 3500 characters. Format:
# Briefing ${when}
## <n>. <name> - <category> - <countries> - since <time since the first article>
- What happened: 1-2 sentences, only facts from the headlines
- Confirmed / not yet: what several headlines confirm, what is still unclear
- Titles: EN: ... | DE: ... | plus one FR, IT or ES title if it trends there
- 30s hook: one sentence to open the video
- Hashtags: 5
- Source: the best headline url
Then "## Coming up" (max 3 items from events_next_14_days, date + one video idea each)
and "## Watchlist" (one line per watchlist term with today >= 5).
For death, crime, war or disasters: only what 2 or more headlines say, otherwise write "verification pending".

DATA:
${JSON.stringify(data).slice(0, 60000)}`;
}

// ---- the 4 engines: none (no AI, free) · gemini (free key) · openai (paid key) · ollama (free, local, no key)
const ENGINES = [["none", "No AI - free smart summary (no key, no account)"], ["gemini", "Google Gemini - free API key"],
                 ["openai", "OpenAI (ChatGPT API) - paid API key"], ["ollama", "Ollama - free AI on this PC (no key, no account)"]];
function engine() { return cfg.aiEngine || (cfg.geminiKey ? "gemini" : "none"); }

async function openaiText(prompt) {
  const H = { "Content-Type": "application/json", Authorization: "Bearer " + cfg.openaiKey };
  let model = cfg.openaiModel;
  if (!model) {
    try {
      const j = await (await fetch("https://api.openai.com/v1/models", { headers: H })).json();
      const mini = (j.data || []).map((m) => m.id).filter((id) => /^gpt-\d+(\.\d+)?-mini$/.test(id))
        .sort((a, b) => parseFloat(b.slice(4)) - parseFloat(a.slice(4)));
      model = mini[0] || "gpt-4o-mini";
    } catch { model = "gpt-4o-mini"; }
  }
  const r = await fetch("https://api.openai.com/v1/chat/completions", { method: "POST", headers: H,
    body: JSON.stringify({ model, messages: [{ role: "user", content: prompt }] }) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error((j.error && j.error.message) || `HTTP ${r.status}`);
  return [(j.choices || [])[0]?.message?.content || "", model];
}

async function ollamaText(prompt) {
  const base = (cfg.ollamaUrl || "http://localhost:11434").replace(/\/$/, "");
  let model = cfg.ollamaModel;
  try {
    const tags = await (await fetch(base + "/api/tags")).json();
    const names = (tags.models || []).map((m) => m.name);
    if (!names.length) throw new Error("Ollama has no model yet - open a terminal and run: ollama pull llama3.2");
    if (!model || !names.some((n) => n === model || n.startsWith(model + ":"))) model = names[0];
  } catch (e) {
    if (/no model/.test(e.message)) throw e;
    throw new Error("Ollama is not running - install it from ollama.com and start it");
  }
  const r = await fetch(base + "/api/chat", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model, stream: false, messages: [{ role: "user", content: prompt }] }) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
  return [j.message?.content || "", "ollama " + model];
}

async function geminiText(prompt) {
  const model = await pickModel();
  const j = await gemini(`${model}:generateContent`, { contents: [{ role: "user", parts: [{ text: prompt }] }],
                                                       generationConfig: { temperature: 0.4, maxOutputTokens: 8192 } });
  return [((j.candidates || [])[0]?.content?.parts || []).filter((p) => !p.thought).map((p) => p.text || "").join(""), model.replace("models/", "")];
}

// no AI at all: pick the best topics with the same rules and write the briefing from the data itself
function plainBriefing(snap, when) {
  const W = { "Celebs & viral": 1.3, "Movies & TV": 1.25, "Gaming": 1.25, "Music": 1.2, "AI video & image": 1.2, "Sports": 1.15,
              "Tech & AI": 1.1, "Natural disasters": 1.05, "Politics": 0.95, "World & conflicts": 0.9, "Crime & accidents": 0.85 };
  const fresh = (t) => { const h = t.first_pub_h; return h == null ? 1 : h <= 2 ? 1.5 : h <= 6 ? 1.3 : h <= 24 ? 1 : 0.8; };
  const want = cfg.countries.filter((c) => c !== "world");
  const inCountry = (t) => want.length >= 7 || (t.countries || []).some((c) => want.includes(c.toLowerCase()));
  const all = [...(snap.trends || []), ...(snap.stories || [])].filter(inCountry)
    .map((t) => ({ t, s: (t.score || 0) * fresh(t) * (W[t.category] || 1) * (t.just_in ? 1.3 : 1) }))
    .sort((a, b) => b.s - a.s);
  const pick = []; let politics = 0;
  for (const { t } of all) {
    if (pick.length >= 5) break;
    if (t.category === "Politics" && ++politics > 2) continue;
    pick.push(t);
  }
  const ago = (h) => h == null ? "" : h < 1 ? Math.max(1, Math.round(h * 60)) + " min" : h < 48 ? Math.round(h) + "h" : Math.round(h / 24) + " days";
  const tag = (s) => "#" + String(s).replace(/[^\p{L}\p{N}]/gu, "");
  let md = `# Briefing ${when}\n_Smart summary without AI - top topics picked by the radar's score._\n`;
  pick.forEach((t, i) => {
    const n = t.name.replace(/^#/, "");
    const news = t.news || [];
    md += `\n## ${i + 1}. ${t.name} - ${t.category} - ${(t.countries || []).slice(0, 4).join(", ")}${t.first_pub_h != null ? " - since " + ago(t.first_pub_h) : ""}\n`;
    if (t.context) md += `- What happened: ${t.context}\n`;
    news.slice(t.context ? 1 : 0, 3).forEach((h) => { md += `- ${h.t} (${h.s})\n`; });
    md += `- Why now: ${t.summary}\n`;
    md += `- Titles: EN: ${n}: why everyone is talking about it | DE: ${n}: Das steckt dahinter\n`;
    md += `- Hashtags: ${tag(n)} ${tag(t.category)} ${(t.countries || []).slice(0, 2).map((c) => tag(c.toLowerCase())).join(" ")} #news\n`;
    if (news[0] && news[0].u) md += `- Source: ${news[0].u}\n`;
  });
  const ev = (snap.events_next_14_days || []).slice(0, 3);
  if (ev.length) md += `\n## Coming up\n` + ev.map((e) => `- ${e.date}: ${e.title} - post a "what you need to know" video 1-3 days before`).join("\n") + "\n";
  const wl = Object.entries(snap.watchlist || {}).filter(([, w]) => w.today >= 5).slice(0, 10);
  if (wl.length) md += `\n## Watchlist\n` + wl.map(([k, w]) => `- ${k} (${w.today}): ${(w.top[0] || {}).t || ""}`).join("\n") + "\n";
  return md;
}

async function makeBriefing(manual = false) {
  if (briefBusy) return { ok: false, msg: "Already writing..." };
  const eng = engine();
  if (eng === "gemini" && !cfg.geminiKey) return { ok: false, msg: "Add your Gemini API key first (or choose 'No AI')." };
  if (eng === "openai" && !cfg.openaiKey) return { ok: false, msg: "Add your OpenAI API key first (or choose 'No AI')." };
  briefBusy = true;
  try {
    const r = await fetch(cfg.url.replace(/#.*$/, "").replace(/\/?$/, "/") + "latest.json", { cache: "no-store" });
    if (!r.ok) throw new Error("could not load the trends (" + r.status + ")");
    const snap = await r.json();
    const data = { ...snap,
      trends: (snap.trends || []).slice(0, 20).map(({ related, ...t }) => ({ ...t, news: (t.news || []).slice(0, 3) })),
      stories: (snap.stories || []).slice(0, 6),
      headlines_by_country: Object.fromEntries(Object.entries(snap.headlines_by_country || {}).map(([c, v]) => [c, v.slice(0, 5)])) };
    const when = new Date().toLocaleString("en-GB", { day: "2-digit", month: "long", hour: "2-digit", minute: "2-digit" });
    let text, who;
    if (eng === "none") { text = plainBriefing(snap, when); who = "the radar (no AI)"; }
    else {
      const prompt = briefPrompt(data, when);
      [text, who] = eng === "openai" ? await openaiText(prompt) : eng === "ollama" ? await ollamaText(prompt) : await geminiText(prompt);
    }
    text = String(text || "").replace(/^```(?:markdown)?\s*|\s*```$/g, "").trim();
    if (!text) throw new Error("empty answer");
    if (!text.startsWith("#")) text = `# Briefing ${when}\n` + text;
    fs.writeFileSync(briefFile(), text + `\n\n_Written by ${who} on this computer._\n`);
    const first = text.split("\n").find((l) => /^##\s*1\./.test(l)) || "";
    notify({ title: "🧠 " + text.split("\n")[0].replace(/^#+\s*/, ""), body: first.replace(/^#+\s*/, "") + "\nClick to read the full briefing", onClick: showBriefing });
    return { ok: true, msg: "Briefing written ✓" };
  } catch (e) {
    return { ok: false, msg: ENGINES.find(([v]) => v === eng)[1].split(" - ")[0] + ": " + String(e.message || e).slice(0, 200) };
  } finally { briefBusy = false; }
}

function showBriefing() {
  if (briefWin && !briefWin.isDestroyed()) { briefWin.reload(); briefWin.show(); briefWin.focus(); return; }
  briefWin = new BrowserWindow({ width: 760, height: 880, title: "Trend Radar - AI briefing", backgroundColor: "#0a0f1d", icon: ICON,
    autoHideMenuBar: true, webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true } });
  briefWin.webContents.setWindowOpenHandler(({ url }) => { if (/^https?:/.test(url)) shell.openExternal(url); return { action: "deny" }; });
  briefWin.removeMenu();
  briefWin.loadFile(path.join(__dirname, "briefing.html"));
}

// the briefing is written at your times (local time). If the cloud already sent one in the last 3 hours, skip.
function briefTick() {
  if (!cfg.briefAuto) return;
  const now = new Date(), today = now.toISOString().slice(0, 10);
  for (const t of cfg.briefTimes || []) {
    const [h, m] = String(t).split(":").map(Number);
    if (Number.isNaN(h)) continue;
    const at = new Date(now); at.setHours(h, m || 0, 0, 0);
    const slot = `${today} ${t}`;
    if (now >= at && now - at < 3 * 3600e3 && cfg.lastBriefSlot !== slot) {
      cfg.lastBriefSlot = slot; saveCfg();
      if (cfg.lastCloudBrief && now - cfg.lastCloudBrief < 3 * 3600e3) return;
      makeBriefing(false);
      return;
    }
  }
}

function applyAiFields(c) {
  if (c.geminiKey !== undefined) cfg.geminiKey = String(c.geminiKey || "").trim();
  if (c.openaiKey !== undefined) cfg.openaiKey = String(c.openaiKey || "").trim();
  if (c.ollamaModel !== undefined) cfg.ollamaModel = String(c.ollamaModel || "").trim();
  if (ENGINES.some(([v]) => v === c.aiEngine)) cfg.aiEngine = c.aiEngine;
  if (BRIEF_LANGS.includes(c.briefLang)) cfg.briefLang = c.briefLang;
}

// ---------------------------------------------------------------- update check (GitHub download page)
const RELEASES = "https://api.github.com/repos/fatimazahra789078/trend-radar/releases/latest";
const RELEASE_PAGE = "https://github.com/fatimazahra789078/trend-radar/releases/latest";
const newer = (a, b) => { const x = a.split(".").map(Number), y = b.split(".").map(Number);
  for (let i = 0; i < 3; i++) { if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0); } return false; };
async function checkUpdate(manual = false) {
  try {
    const j = await (await fetch(RELEASES, { headers: { "User-Agent": "TrendRadar-Desktop" } })).json();
    const m = /(\d+\.\d+\.\d+)/.exec(j.name || j.tag_name || "");
    if (m && newer(m[1], app.getVersion())) {
      notify({ title: `⬆ Trend Radar ${m[1]} is available`, body: `You have ${app.getVersion()}. Click to download the update.`,
               onClick: () => shell.openExternal(RELEASE_PAGE) });
      return `Update ${m[1]} available`;
    }
    if (manual) notify({ title: "Trend Radar is up to date", body: `Version ${app.getVersion()}` });
    return "Up to date";
  } catch { if (manual) notify({ title: "Update check failed", body: "No internet?" }); return "failed"; }
}

// ---------------------------------------------------------------- IPC for the settings window
ipcMain.handle("cfg:get", () => ({ ...cfg, lists: { COUNTRIES, CATEGORIES, TYPES, IMPORTANCE, BRIEF_LANGS, ENGINES }, version: app.getVersion(), platform: process.platform }));
ipcMain.handle("brief:now", async (_e, c) => {
  if (c) { applyAiFields(c); saveCfg(); }
  return makeBriefing(true);
});
ipcMain.handle("brief:get", () => { try { return fs.readFileSync(briefFile(), "utf8"); } catch { return ""; } });
ipcMain.handle("open:url", (_e, u) => { if (/^https:\/\//.test(u)) shell.openExternal(u); });
ipcMain.handle("cfg:save", (_e, c) => {
  const pick = (arr, allowed) => (Array.isArray(arr) ? arr.filter((v) => allowed.includes(v)) : []);
  cfg.topic = String(c.topic || "").trim();
  cfg.minPriority = [1, 3, 4].includes(Number(c.minPriority)) ? Number(c.minPriority) : 4;
  cfg.countries = pick(c.countries, COUNTRIES.map(([v]) => v));
  cfg.categories = pick(c.categories, CATEGORIES);
  cfg.types = pick(c.types, TYPES.map(([v]) => v));
  if (!cfg.countries.length) cfg.countries = COUNTRIES.map(([v]) => v);
  if (!cfg.categories.length) cfg.categories = [...CATEGORIES];
  if (!cfg.types.length) cfg.types = TYPES.map(([v]) => v);
  cfg.url = String(c.url || DEFAULT_URL).trim() || DEFAULT_URL;
  cfg.autostart = !!c.autostart;
  applyAiFields(c);
  cfg.briefAuto = !!c.briefAuto;
  cfg.briefLang = BRIEF_LANGS.includes(c.briefLang) ? c.briefLang : "English";
  cfg.briefTimes = (c.briefTimes || []).filter((t) => /^\d{1,2}:\d{2}$/.test(t)).slice(0, 4);
  saveCfg(); applyAutostart(); connect(); buildTray();
  if (win && !win.isDestroyed()) win.loadURL(dashboardUrl());
  return true;
});
ipcMain.handle("notify:test", () => {
  notify({ title: "🇺🇸🇩🇪 🔥 HOT: Trend Radar works!", body: "📰 This is how a trend notification looks.\n🌍 USA, Germany · Politics\n🕒 since 2h · 12 articles in the last hour\n[Politics · HOT]" });
  return true;
});

// ---------------------------------------------------------------- start
if (!app.isPackaged && process.env.TR_USERDATA) app.setPath("userData", process.env.TR_USERDATA);   // developer test only
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => showDashboard());
  app.whenReady().then(() => {
    app.setAppUserModelId(app.isPackaged ? "com.trendradar.desktop" : process.execPath);
    // a visible menu bar: Settings is always one click away (also Ctrl+, / Cmd+,)
    const briefMenu = { label: "🧠 AI briefing", submenu: [
      { label: "Write a briefing now", click: () => makeBriefing(true).then((r) => { if (!r.ok) { notify({ title: "🧠 Briefing", body: r.msg }); openSettings("ai"); } }) },
      { label: "Show last briefing", click: showBriefing },
      { label: "AI engine, keys and times...", click: () => openSettings("ai") },
    ] };
    const pages = { label: "Pages", submenu: [
      { label: "All trends", click: () => showDashboard("") }, { label: "🇺🇸 USA", click: () => showDashboard("us") },
      { label: "💡 Video ideas", click: () => showDashboard("ideas") }, { label: "🎬 AI tools & GitHub", click: () => showDashboard("ai") },
      { label: "🌍 Disasters", click: () => showDashboard("disasters") }, { label: "⚽ Sports", click: () => showDashboard("sports") },
      { type: "separator" }, { label: "Reload", accelerator: "F5", click: () => win && win.reload() },
      { label: "Check for updates", click: () => checkUpdate(true) },
    ] };
    const settingsItem = { label: "⚙ Settings", accelerator: "CmdOrCtrl+,", click: () => openSettings() };
    Menu.setApplicationMenu(Menu.buildFromTemplate(process.platform === "darwin"
      ? [{ label: app.name, submenu: [{ role: "about" }, { type: "separator" }, { ...settingsItem, label: "Settings..." }, { type: "separator" }, { role: "quit" }] },
         { role: "editMenu" }, pages, briefMenu, { role: "windowMenu" }]
      : [settingsItem, briefMenu, pages, { label: "Quit", click: () => { quitting = true; app.quit(); } }]));
    loadCfg();
    applyAutostart();
    createWindow(!START_HIDDEN);
    buildTray();
    connect();
    if (!cfg.topic) openSettings();
    else if (!cfg.aiBoxShown) { cfg.aiBoxShown = true; saveCfg(); openSettings("ai"); }  // show the new AI box once after the update
    powerMonitor.on("resume", () => setTimeout(connect, 3000));   // woke up from sleep -> catch up
    setInterval(briefTick, 5 * 60e3); setTimeout(briefTick, 60e3);
    setTimeout(() => checkUpdate(false), 30e3); setInterval(() => checkUpdate(false), 6 * 3600e3);
    if (!app.isPackaged && process.env.TR_BRIEF_NOW) {   // developer test only
      cfg.aiEngine = process.env.TR_ENGINE || "none"; if (cfg.aiEngine === "gemini") cfg.geminiKey = "test-key"; cfg.__test = true;
      makeBriefing(true).then((r) => { console.log("[brief]", JSON.stringify(r)); if (r.ok) showBriefing(); });
    }
    app.on("activate", () => showDashboard());                    // macOS dock icon
  });
  app.on("before-quit", () => { quitting = true; });
  app.on("window-all-closed", () => { /* keep running in the tray */ });
}
