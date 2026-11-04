// Trend Radar desktop app (Windows + macOS).
// - shows the online dashboard in its own window
// - lives in the tray / menu bar and starts with the computer
// - listens to your ntfy topic and shows native notifications, filtered by YOUR choices:
//   importance, countries, topics and types (also the ones missed while the computer slept)
// The radar itself runs in the cloud (GitHub Actions), so this app needs nothing else installed.
const { app, BrowserWindow, Tray, Menu, Notification, shell, ipcMain, nativeImage, powerMonitor } = require("electron");
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
];
const IMPORTANCE = [[4, "Very important only", "Breaking, hot, just in, repeating trends, big disasters, briefing"],
                    [3, "Important + trending", "Also normal trends, top news, sports results, watchlist"],
                    [1, "Everything", "Also digests, music charts, reminders"]];
const COUNTRYLESS_OK = ["WATCHLIST", "BRIEFING", "DIGEST", "SUMMARY", "AI MODEL", "AI TOOLS"];
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
  if (cfg.autostart === undefined) cfg.autostart = true;
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
    backgroundColor: "#0a0f1d", icon: ICON, autoHideMenuBar: true,
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

function openSettings() {
  if (settingsWin && !settingsWin.isDestroyed()) { settingsWin.show(); settingsWin.focus(); return; }
  settingsWin = new BrowserWindow({
    width: 640, height: 860, resizable: true, title: "Trend Radar - Settings", backgroundColor: "#0a0f1d", icon: ICON,
    autoHideMenuBar: true,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true },
  });
  settingsWin.loadFile(path.join(__dirname, "settings.html"));
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

function notify({ title, body, click, urgent }) {
  if (!Notification.isSupported()) return;
  const n = new Notification({ title: title.slice(0, 200), body: (body || "").slice(0, 900), icon: ICON, urgency: urgent ? "critical" : "normal" });
  n.on("click", () => (click && /^https?:/.test(click) ? shell.openExternal(click) : showDashboard()));
  n.show();
}

// ---------------------------------------------------------------- IPC for the settings window
ipcMain.handle("cfg:get", () => ({ ...cfg, lists: { COUNTRIES, CATEGORIES, TYPES, IMPORTANCE }, version: app.getVersion(), platform: process.platform }));
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
  saveCfg(); applyAutostart(); connect(); buildTray();
  if (win && !win.isDestroyed()) win.loadURL(dashboardUrl());
  return true;
});
ipcMain.handle("notify:test", () => {
  notify({ title: "🇺🇸🇩🇪 🔥 HOT: Trend Radar works!", body: "📰 This is how a trend notification looks.\n🌍 USA, Germany · Politics\n🕒 since 2h · 12 articles in the last hour\n[Politics · HOT]" });
  return true;
});

// ---------------------------------------------------------------- start
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => showDashboard());
  app.whenReady().then(() => {
    app.setAppUserModelId(app.isPackaged ? "com.trendradar.desktop" : process.execPath);
    if (process.platform === "darwin") {
      Menu.setApplicationMenu(Menu.buildFromTemplate([{ role: "appMenu" }, { role: "editMenu" }, { role: "viewMenu" }, { role: "windowMenu" }]));
    } else {
      Menu.setApplicationMenu(null);
    }
    loadCfg();
    applyAutostart();
    createWindow(!START_HIDDEN);
    buildTray();
    connect();
    if (!cfg.topic) openSettings();
    powerMonitor.on("resume", () => setTimeout(connect, 3000));   // woke up from sleep -> catch up
    app.on("activate", () => showDashboard());                    // macOS dock icon
  });
  app.on("before-quit", () => { quitting = true; });
  app.on("window-all-closed", () => { /* keep running in the tray */ });
}
