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
  ["TOP 3", "Today's top 3 videos to make (twice a day)"],
  ["TRAVELING", "Trending in the USA / UK, not yet in your other countries - be first"],
];
// types added after 1.3.1: switched on for people who saved their types before
const NEW_TYPES = ["GITHUB", "TOP 3", "TRAVELING"];
const IMPORTANCE = [[4, "Very important only", "Breaking, hot, just in, repeating trends, big disasters, briefing"],
                    [3, "Important + trending", "Also normal trends, top news, sports results, watchlist"],
                    [1, "Everything", "Also digests, music charts, reminders"]];
const COUNTRYLESS_OK = ["WATCHLIST", "BRIEFING", "DIGEST", "SUMMARY", "AI MODEL", "AI TOOLS", "GITHUB", "TOP 3"];
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
    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false, preload: path.join(__dirname, "dashpreload.js") },
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
  win.webContents.on("did-finish-load", () => setTimeout(() => { injectYT(); injectTR(); }, 300));   // your YouTube results + language
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
    { label: "🎯 Make today (top videos)", click: () => showDashboard("today") },
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
  const show = (title, body) => notify({
    title: (flags ? flags + " " : "") + (title || "Trend Radar"),
    body: (body || "") + (extra ? `\n[${extra}]` : ""),
    click: ev.click, urgent: (ev.priority || 3) >= 5,
  });
  // your language: translated with free Google Translate (falls back to English after 8 s)
  if (cfg.trLang) translateNotif(ev.title || "", ev.message || "").then(([t, b]) => show(t, b)).catch(() => show(ev.title, ev.message));
  else show(ev.title, ev.message);
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
Each topic has a 'video' object: prefer phase 'rising', yt.rating 'go' or 'good' (few YouTube videos yet), a 'travel'
entry (trending in the USA/UK, not yet in the 'missing' countries: suggest that language first) and a high video score;
avoid 'falling' and 'crowded'; if 'sensitive' is true, warn that YouTube may limit ads.
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
    for (const t of [...(snap.trends || []), ...(snap.stories || [])]) {   // add this computer's YouTube results
      const y = (cfg.ytCache || {})[t.id];
      if (y && t.video && !t.video.yt) t.video.yt = { n24: y.n24, full: y.full, rating: y.rating, txt: y.txt, vph_top: y.vph_top };
    }
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

// ---------------------------------------------------------------- YouTube competition check with YOUR free key (USA)
// How many YouTube videos were uploaded about a top topic in the last 24h. Free quota: 10,000 units a day per key
// (reset at midnight Pacific); one check = 101 units. Results stay on this computer and fill the "Make today" tab.
const YT = (!app.isPackaged && process.env.TR_YT_URL) || "https://www.googleapis.com/youtube/v3/";   // test override (dev only)
const YT_COUNTRIES = ["US"];
const YT_LIMIT = 9000;
let ytBusy = false;
const pacific = () => {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-CA", { timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit",
    day: "2-digit", hour: "2-digit", hourCycle: "h23" }).formatToParts(new Date()).map((x) => [x.type, x.value]));
  return { day: `${p.year}-${p.month}-${p.day}`, hour: Number(p.hour) };
};
function ytQuota() {
  const { day, hour } = pacific();
  if (!cfg.ytq || cfg.ytq.day !== day) cfg.ytq = { day, used: 0, checks: 0 };
  return { q: cfg.ytq, hoursLeft: Math.max(1, 24 - hour) };
}
async function ytGet(path, params, q, cost) {
  q.used += cost;
  const r = await fetch(YT + path + "?" + new URLSearchParams({ ...params, key: cfg.youtubeKey }));
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    const m = (j.error && j.error.message) || `HTTP ${r.status}`;
    if (/not valid|API_KEY_INVALID/i.test(m)) throw new Error("this key is not valid - copy it again (it starts with AIza)");
    if (/has not been used|disabled|accessNotConfigured/i.test(m)) throw new Error("turn on 'YouTube Data API v3' in Google Cloud for this key's project");
    if (/quota/i.test(m)) { q.used = YT_LIMIT; throw new Error("today's free YouTube quota is used up - it comes back at midnight Pacific time"); }
    throw new Error(m.replace(/<[^>]+>/g, "").slice(0, 160));
  }
  return j;
}
async function ytSupply(p, q) {
  const cc = YT_COUNTRIES.find((c) => (p.countries || []).includes(c)) || YT_COUNTRIES[0];
  const after = new Date(Date.now() - 24 * 3600e3).toISOString().replace(/\.\d+Z$/, "Z");
  const s = await ytGet("search", { part: "id", type: "video", q: p.query || p.name, publishedAfter: after, order: "viewCount",
                                    maxResults: "50", regionCode: cc, relevanceLanguage: "en" }, q, 100);
  const ids = (s.items || []).map((i) => i.id && i.id.videoId).filter(Boolean);
  let vids = [];
  if (ids.length) {
    const v = await ytGet("videos", { part: "snippet,statistics", id: ids.slice(0, 50).join(",") }, q, 1);
    vids = (v.items || []).map((it) => {
      const views = Number((it.statistics || {}).viewCount || 0);
      const age = Math.max(0.5, (Date.now() - new Date((it.snippet || {}).publishedAt).getTime()) / 3600e3);
      return { t: ((it.snippet || {}).title || "").slice(0, 120), ch: (it.snippet || {}).channelTitle || "", views,
               vph: Math.round(views / age), u: `https://www.youtube.com/watch?v=${it.id}` };
    }).sort((a, b) => b.views - a.views);
  }
  const n = ids.length, vphTop = Math.max(0, ...vids.map((x) => x.vph));
  let [rating, txt] = n <= 5 ? ["go", "🟢 GO NOW - almost no YouTube videos yet"] : n <= 20 ? ["good", "🟢 GOOD - only a few YouTube videos"]
    : n < 50 ? ["busy", "🟡 BUSY - many videos, find your own angle"] : ["crowded", "🔴 CROWDED - 50+ videos in 24h"];
  if (vphTop >= 5000 && (rating === "busy" || rating === "crowded")) txt += ` (but people watch a lot: top video ${vphTop.toLocaleString("en-US")} views/hour)`;
  return { at: new Date().toISOString(), n24: n, full: n >= 50, vph_top: vphTop, views_sum: vids.reduce((a, x) => a + x.views, 0),
           rating, txt, country: cc, query: p.query || p.name, top: vids.slice(0, 3), by: "app" };
}
async function ytTick(manual = false) {
  if (!cfg.youtubeKey) return { ok: false, msg: "Paste your YouTube API key first." };
  if (ytBusy) return { ok: false, msg: "Already checking..." };
  ytBusy = true;
  try {
    const { q, hoursLeft } = ytQuota();
    const free = Math.floor((YT_LIMIT - q.used) / 101);
    if (free <= 0) return { ok: false, msg: "Today's free YouTube quota is used up - it comes back at midnight Pacific time." };
    const perRun = Math.min(manual ? 5 : 8, Math.max(1, Math.floor(free / hoursLeft)));
    const r = await fetch(cfg.url.replace(/#.*$/, "").replace(/\/?$/, "/") + "latest.json", { cache: "no-store" });
    if (!r.ok) throw new Error("could not load the trends (" + r.status + ")");
    const snap = await r.json();
    const cache = cfg.ytCache = Object.fromEntries(Object.entries(cfg.ytCache || {}).filter(([, v]) => Date.now() - new Date(v.at) < 24 * 3600e3));
    const fresh = (id) => cache[id] && Date.now() - new Date(cache[id].at) < 4 * 3600e3;
    const cands = (snap.video_top || []).filter((p) => (p.countries || []).some((c) => YT_COUNTRIES.includes(c)))
      .slice(0, 25).filter((p) => p.phase !== "falling" && !p.has_yt && !fresh(p.id)).slice(0, perRun);
    let n = 0;
    for (const p of cands) { cache[p.id] = await ytSupply(p, q); q.checks += 1; n += 1; }
    saveCfg();
    injectYT();
    const have = (snap.video_top || []).filter((p) => cache[p.id]).length;
    return { ok: true, msg: `YouTube ✓ ${n ? `checked ${n} new topic${n > 1 ? "s" : ""}` : "all top topics are up to date"} · ${have} with data · quota today ${q.used.toLocaleString("en-US")} / 10,000` };
  } catch (e) {
    saveCfg();
    return { ok: false, msg: "YouTube: " + String(e.message || e).slice(0, 200) };
  } finally { ytBusy = false; }
}
// put this computer's YouTube results into the online dashboard's "Make today" tab
function injectYT() {
  if (!win || win.isDestroyed() || !cfg.youtubeKey) return;
  const Y = cfg.ytCache || {}, q = (cfg.ytq || {});
  const js = `(() => { try { if (typeof DATA === "undefined" || !DATA || !DATA.plan) return 0; const Y = ${JSON.stringify(Y)}; let n = 0;
    for (const p of [...(DATA.plan.top || []), ...(DATA.plan.travel || [])]) if (!p.yt && Y[p.id]) { p.yt = Y[p.id]; n++; }
    DATA.plan.yt_key = true; if (!DATA.plan.quota || !DATA.plan.quota.checks) DATA.plan.quota = { used: ${Number(q.used) || 0}, limit: 10000, checks: ${Number(q.checks) || 0} };
    if (typeof state !== "undefined" && state.tab === "today" && typeof render === "function") render(); return n; } catch (e) { return -1; } })()`;
  win.webContents.executeJavaScript(js).then((n) => { if (process.env.TR_DEBUG) console.log("[yt inject]", n); }).catch(() => {});
}

// ---------------------------------------------------------------- trends in YOUR language (no key, no AI quota)
// The same free Google Translate endpoint as the "Japanese Auto Translate" extension: the whole dashboard and the
// notifications are translated from English into the language you choose in Settings.
const TR_LANGS = [["ar", "Arabic - العربية"], ["fr", "French - Français"], ["es", "Spanish - Español"], ["de", "German - Deutsch"],
                  ["it", "Italian - Italiano"], ["pt", "Portuguese - Português"], ["tr", "Turkish - Türkçe"], ["nl", "Dutch - Nederlands"]];
const GT_HOSTS = ["translate.googleapis.com", "clients5.google.com"];
const gtCache = new Map();
let gtHost = 0, gtRunning = 0;
const gtWaiting = [];
const gtAcquire = () => gtRunning < 3 ? (gtRunning++, Promise.resolve()) : new Promise((r) => gtWaiting.push(r));
const gtRelease = () => { const n = gtWaiting.shift(); if (n) n(); else gtRunning--; };
const escHtml = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const unHtml = (s) => String(s).replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, "&");
async function gtRequest(texts, tl) {
  let last;
  for (let attempt = 0; attempt < 4; attempt++) {
    const host = GT_HOSTS[(gtHost + attempt) % GT_HOSTS.length];
    await gtAcquire();
    try {
      const body = new URLSearchParams();
      for (const t of texts) body.append("q", escHtml(t));
      const r = await fetch(`https://${host}/translate_a/t?client=dict-chrome-ex&sl=auto&tl=${encodeURIComponent(tl)}&format=html`, {
        method: "POST", body, headers: { "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" }, signal: AbortSignal.timeout(20000) });
      if (!r.ok) throw new Error("HTTP " + r.status);
      let j = await r.json();
      if (typeof j === "string") j = [j];
      if (texts.length === 1 && j.length === 2 && typeof j[0] === "string" && typeof j[1] === "string") j = [j];
      if (!Array.isArray(j) || j.length !== texts.length) throw new Error("unexpected answer");
      gtHost = GT_HOSTS.indexOf(host);
      return j.map((x) => unHtml(Array.isArray(x) ? x[0] : x));
    } catch (e) { last = e; } finally { gtRelease(); }
    await new Promise((r) => setTimeout(r, 700 * 2 ** attempt));
  }
  throw last;
}
async function gtranslate(texts, tl) {
  const out = new Array(texts.length).fill(null), todo = new Map();
  texts.forEach((t, i) => {
    const s = String(t || "");
    if (!s.trim()) return;
    const k = tl + "\u0001" + s;
    if (gtCache.has(k)) out[i] = gtCache.get(k);
    else { if (!todo.has(k)) todo.set(k, { s, idx: [] }); todo.get(k).idx.push(i); }
  });
  const batches = [];
  let cur = [], chars = 0;
  for (const [k, e] of todo) {
    if (cur.length && (chars + e.s.length > 4500 || cur.length >= 60)) { batches.push(cur); cur = []; chars = 0; }
    cur.push([k, e]); chars += e.s.length;
  }
  if (cur.length) batches.push(cur);
  await Promise.all(batches.map(async (b) => {
    try {
      const res = await gtRequest(b.map(([, e]) => e.s), tl);
      b.forEach(([k, e], n) => { gtCache.set(k, res[n]); for (const i of e.idx) out[i] = res[n]; });
    } catch (e) { if (process.env.TR_DEBUG) console.log("[translate] failed", e.message); }
  }));
  if (gtCache.size > 20000) for (const k of [...gtCache.keys()].slice(0, 5000)) gtCache.delete(k);
  return out;
}
ipcMain.handle("page:lang", () => cfg.trLang || "");
ipcMain.handle("page:translate", async (_e, texts) => (cfg.trLang && Array.isArray(texts) ? gtranslate(texts.slice(0, 3000).map(String), cfg.trLang) : []));
// runs inside the dashboard: translates every text on screen, again after each re-render (tabs, filters, new scan)
const PAGE_TRANSLATOR = `(async () => {
  if (!window.trApp) return "no bridge";
  if (window.__trOn) { window.__trRun && window.__trRun(); return "again"; }
  const lang = await window.trApp.lang(); if (!lang) return "off";
  window.__trOn = true;
  document.documentElement.lang = lang;
  const st = document.createElement("style");
  st.textContent = "body *{unicode-bidi:plaintext}";
  document.head.appendChild(st);
  const SKIP = new Set(["SCRIPT", "STYLE", "CODE", "PRE", "TEXTAREA", "INPUT", "SELECT", "NOSCRIPT"]);
  const done = new WeakSet();
  const pick = () => { const out = []; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode(n) {
      const p = n.parentElement; if (!p || SKIP.has(p.tagName) || done.has(n) || p.closest(".notranslate,.score,.rank,.clock,code")) return 2;
      const s = n.nodeValue.trim(); return s.length >= 2 && /\\p{L}{2}/u.test(s) ? 1 : 2; } });
    let n; while ((n = w.nextNode())) out.push(n); return out; };
  let busy = false, again = false;
  async function run() {
    if (busy) { again = true; return; }
    busy = true;
    try {
      do {
        again = false;
        const nodes = pick(); if (!nodes.length) break;
        for (let i = 0; i < nodes.length; i += 400) {
          const part = nodes.slice(i, i + 400);
          const res = await window.trApp.translate(part.map((n) => n.nodeValue.trim()));
          part.forEach((n, k) => {
            done.add(n);
            const t = res[k], o = n.nodeValue.trim();
            if (!t || t === o) return;
            const lead = n.nodeValue.match(/^\\s*/)[0], trail = n.nodeValue.match(/\\s*$/)[0];
            // trend names (titles): keep the original next to the translation - names like "Lens" are often mistranslated
            const title = n.parentElement && n.parentElement.closest("h3");
            n.nodeValue = lead + (title ? t + " (" + o + ")" : t) + trail;
            if (n.parentElement && !n.parentElement.title) n.parentElement.title = o;
          });
        }
      } while (again);
    } finally { busy = false; }
  }
  window.__trRun = run;
  new MutationObserver(() => { clearTimeout(window.__trT); window.__trT = setTimeout(run, 200); }).observe(document.body, { childList: true, subtree: true });
  run();
  return "on";
})()`;
function injectTR() {
  if (!win || win.isDestroyed() || !cfg.trLang) return;
  win.webContents.executeJavaScript(PAGE_TRANSLATOR).then((r) => { if (process.env.TR_DEBUG) console.log("[tr page]", r); }).catch(() => {});
}
async function translateNotif(title, body) {
  const res = await Promise.race([gtranslate([title, body], cfg.trLang), new Promise((_, rej) => setTimeout(() => rej(new Error("slow")), 8000))]);
  return [res[0] || title, res[1] || body];
}

// ---------------------------------------------------------------- "Test" buttons next to each key (free tests)
async function keyTest(kind, key) {
  key = String(key || "").trim();
  if (kind !== "ollama" && !key) return { ok: false, msg: "Paste the key first" };
  try {
    if (kind === "gemini") {
      const old = cfg.geminiKey; cfg.geminiKey = key;
      try {
        const list = await gemini("models?pageSize=200");            // valid key? (free, no tokens)
        if (!(list.models || []).length) throw new Error("no models for this key");
        const model = await pickModel();
        const j = await gemini(`${model}:generateContent`, { contents: [{ role: "user", parts: [{ text: "Reply with the word OK" }] }],
                                                              generationConfig: { maxOutputTokens: 20 } });
        if (!(j.candidates || []).length) throw new Error("no answer");
        return { ok: true, msg: `Works ✓ (${model.replace("models/", "")}, free tier)` };
      } finally { cfg.geminiKey = old; }
    }
    if (kind === "youtube") {                                          // 1 quota unit
      const r = await fetch(YT + "videos?" + new URLSearchParams({ part: "id", chart: "mostPopular", regionCode: "US", maxResults: "1", key }));
      const j = await r.json().catch(() => ({}));
      if (!r.ok) {
        const m = (j.error && j.error.message) || `HTTP ${r.status}`;
        if (/not valid|API_KEY_INVALID/i.test(m)) throw new Error("this key is not valid - copy it again (it starts with AIza)");
        if (/has not been used|disabled|accessNotConfigured/i.test(m)) throw new Error("turn on 'YouTube Data API v3' in Google Cloud for this key's project");
        throw new Error(m.replace(/<[^>]+>/g, "").slice(0, 160));
      }
      const { q } = ytQuota();
      return { ok: true, msg: `Works ✓ (YouTube Data API v3 · quota used today ${q.used.toLocaleString("en-US")} / 10,000)` };
    }
    if (kind === "openai") {
      const r = await fetch("https://api.openai.com/v1/models", { headers: { Authorization: "Bearer " + key } });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error((j.error && j.error.message) || `HTTP ${r.status}`);
      return { ok: true, msg: "Works ✓ (OpenAI key valid - usage is paid per request)" };
    }
    if (kind === "ollama") {
      const base = (cfg.ollamaUrl || "http://localhost:11434").replace(/\/$/, "");
      let tags;
      try { tags = await (await fetch(base + "/api/tags")).json(); } catch { throw new Error("Ollama is not running - install it from ollama.com and start it"); }
      const names = (tags.models || []).map((m) => m.name);
      if (!names.length) throw new Error("Ollama runs but has no model - run: ollama pull llama3.2");
      return { ok: true, msg: `Works ✓ (Ollama: ${names.slice(0, 3).join(", ")})` };
    }
    return { ok: false, msg: "unknown key" };
  } catch (e) {
    return { ok: false, msg: String(e.message || e).replace(/^\[?\w*Error\]?:?\s*/, "").slice(0, 200) };
  }
}

function applyAiFields(c) {
  if (c.trLang !== undefined) cfg.trLang = TR_LANGS.some(([v]) => v === c.trLang) ? c.trLang : "";
  if (c.youtubeKey !== undefined) cfg.youtubeKey = String(c.youtubeKey || "").trim();
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
ipcMain.handle("cfg:get", () => ({ ...cfg, lists: { COUNTRIES, CATEGORIES, TYPES, IMPORTANCE, BRIEF_LANGS, ENGINES, TR_LANGS }, version: app.getVersion(), platform: process.platform }));
ipcMain.handle("brief:now", async (_e, c) => {
  if (c) { applyAiFields(c); saveCfg(); }
  return makeBriefing(true);
});
ipcMain.handle("key:test", (_e, kind, key) => keyTest(String(kind), key));
ipcMain.handle("yt:now", async (_e, c) => {
  if (c) { applyAiFields(c); saveCfg(); }
  return ytTick(true);
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
  if (cfg.youtubeKey) setTimeout(() => ytTick(false), 4000);
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
      { label: "🎯 Make today", click: () => showDashboard("today") },
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
    setTimeout(() => ytTick(false), 90e3); setInterval(() => ytTick(false), 60 * 60e3);   // YouTube check with your key
    if (!app.isPackaged && process.env.TR_LANG) {   // developer test only
      cfg.trLang = process.env.TR_LANG; cfg.__test = true;
      setTimeout(() => win.webContents.executeJavaScript(`[document.title, (document.querySelector("#tabs")||{}).innerText, (document.querySelector("#main")||{}).innerText]`)
        .then((r) => console.log("[tr text]", JSON.stringify(r).slice(0, 900))), 15000);
    }
    if (!app.isPackaged && process.env.TR_KEYTEST) {   // developer test only, e.g. TR_KEYTEST=gemini:somekey
      const [kind, key] = process.env.TR_KEYTEST.split(":");
      keyTest(kind, key).then((r) => console.log("[keytest]", kind, JSON.stringify(r)));
    }
    if (!app.isPackaged && process.env.TR_YT_KEY) {   // developer test only
      cfg.youtubeKey = process.env.TR_YT_KEY; cfg.__test = true;
      setTimeout(() => ytTick(true).then((r) => { console.log("[yt]", JSON.stringify(r)); win.loadURL(dashboardUrl("today")); }), 4000);
    }
    if (!app.isPackaged && process.env.TR_BRIEF_NOW) {   // developer test only
      cfg.aiEngine = process.env.TR_ENGINE || "none"; if (cfg.aiEngine === "gemini") cfg.geminiKey = "test-key"; cfg.__test = true;
      makeBriefing(true).then((r) => { console.log("[brief]", JSON.stringify(r)); if (r.ok) showBriefing(); });
    }
    app.on("activate", () => showDashboard());                    // macOS dock icon
  });
  app.on("before-quit", () => { quitting = true; });
  app.on("window-all-closed", () => { /* keep running in the tray */ });
}
