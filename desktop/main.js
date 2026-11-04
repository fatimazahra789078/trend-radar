// Trend Radar desktop app (Windows + macOS).
// - shows the online dashboard in its own window
// - lives in the tray / menu bar and starts with the computer
// - listens to your ntfy channels and shows native notifications (also the ones missed while asleep)
// The radar itself runs in the cloud (GitHub Actions), so this app needs nothing else installed.
const { app, BrowserWindow, Tray, Menu, Notification, shell, ipcMain, nativeImage, powerMonitor } = require("electron");
const path = require("path");
const fs = require("fs");
const https = require("https");
const crypto = require("crypto");

const DEFAULT_URL = "https://fatimazahra789078.github.io/trend-radar/";
const DEFAULT_SERVER = "https://ntfy.sh";
const CHANNELS = [
  ["", "Everything"], ["-us", "USA only"], ["-de", "Germany / Austria / Switzerland"],
  ["-eu", "Europe (UK, France, Italy, Spain)"], ["-sports", "Sports"], ["-disasters", "Natural disasters + breaking"],
];
const FLAGS = { us: "🇺🇸", de: "🇩🇪", gb: "🇬🇧", fr: "🇫🇷", it: "🇮🇹", es: "🇪🇸", eu: "🇪🇺" };
const ICON = path.join(__dirname, "build", "icon.png");
const START_HIDDEN = process.argv.includes("--hidden");

let win = null, settingsWin = null, tray = null, cfg = {}, req = null, retryMs = 5000, retryTimer = null;
let quitting = false, pausedUntil = 0, connected = false;
const recent = new Map(); // de-duplicate the same alert coming from 2 channels

// ---------------------------------------------------------------- settings
const cfgFile = () => path.join(app.getPath("userData"), "settings.json");
function loadCfg() {
  try { cfg = JSON.parse(fs.readFileSync(cfgFile(), "utf8")); } catch { cfg = {}; }
  cfg.url = cfg.url || DEFAULT_URL;
  cfg.server = cfg.server || DEFAULT_SERVER;
  cfg.channels = Array.isArray(cfg.channels) && cfg.channels.length ? cfg.channels : [""];
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

// ---------------------------------------------------------------- windows
function dashboardUrl(hash) { return cfg.url.replace(/#.*$/, "") + (hash ? "#" + hash : ""); }

function createWindow(show = true) {
  win = new BrowserWindow({
    width: 1300, height: 880, minWidth: 380, minHeight: 500, show: false, title: "Trend Radar",
    backgroundColor: "#0a0f1d", icon: ICON, autoHideMenuBar: true,
    webPreferences: { contextIsolation: true, sandbox: true, nodeIntegration: false },
  });
  win.webContents.setWindowOpenHandler(({ url }) => { if (/^https?:/.test(url)) shell.openExternal(url); return { action: "deny" }; });
  win.webContents.on("will-navigate", (e, url) => {
    const home = new URL(cfg.url);
    try { if (new URL(url).origin !== home.origin) { e.preventDefault(); shell.openExternal(url); } } catch {}
  });
  win.webContents.on("did-fail-load", (_e, code, _d, url, isMain) => {
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
    width: 560, height: 720, resizable: true, title: "Trend Radar - Settings", backgroundColor: "#0a0f1d", icon: ICON,
    autoHideMenuBar: true, parent: win && win.isVisible() ? win : undefined,
    webPreferences: { preload: path.join(__dirname, "preload.js"), contextIsolation: true, sandbox: true },
  });
  settingsWin.loadFile(path.join(__dirname, "settings.html"));
}

// ---------------------------------------------------------------- tray / menu bar
function buildTray() {
  const img = nativeImage.createFromPath(ICON).resize({ width: process.platform === "darwin" ? 18 : 16, height: process.platform === "darwin" ? 18 : 16 });
  if (!tray) {
    tray = new Tray(img);
    tray.setToolTip("Trend Radar");
    tray.on("click", () => showDashboard());
  }
  const paused = Date.now() < pausedUntil;
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: "Open Trend Radar", click: () => showDashboard() },
    { type: "separator" },
    { label: "🇺🇸 USA only", click: () => showDashboard("us") },
    { label: "💡 Video ideas", click: () => showDashboard("ideas") },
    { label: "🌍 Disasters", click: () => showDashboard("disasters") },
    { label: "⚽ Sports", click: () => showDashboard("sports") },
    { type: "separator" },
    { label: cfg.topic ? (connected ? "● Notifications on" : "○ Connecting...") : "⚠ Set your topic in Settings", enabled: false },
    paused ? { label: "Resume notifications", click: () => { pausedUntil = 0; buildTray(); } }
           : { label: "Pause notifications for 1 hour", click: () => { pausedUntil = Date.now() + 3600e3; buildTray(); } },
    { label: "Settings...", click: openSettings },
    { type: "separator" },
    { label: "Quit Trend Radar", click: () => { quitting = true; app.quit(); } },
  ]));
}

// ---------------------------------------------------------------- notifications (ntfy stream)
function topicsParam() {
  return cfg.channels.map((s) => cfg.topic + s).join(",");
}

function connect() {
  clearTimeout(retryTimer);
  if (req) { try { req.destroy(); } catch {} req = null; }
  connected = false;
  if (!cfg.topic) { buildTray(); return; }
  // since = last message we showed -> messages that came while the PC slept are shown too (ntfy keeps 12h)
  const since = cfg.lastTime ? String(cfg.lastTime + 1) : "2m";
  const url = `${cfg.server.replace(/\/$/, "")}/${topicsParam()}/json?since=${encodeURIComponent(since)}`;
  req = https.get(url, { headers: { "User-Agent": "TrendRadar-Desktop/1.0" } }, (res) => {
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
  if (now < pausedUntil) return;
  const flags = (ev.tags || []).map((t) => FLAGS[t]).filter(Boolean).join("");
  const label = (ev.tags || []).find((t) => !FLAGS[t]);
  notify({
    title: (flags ? flags + " " : "") + (ev.title || "Trend Radar"),
    body: (ev.message || "") + (label ? `\n[${label}]` : ""),
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
ipcMain.handle("cfg:get", () => ({ ...cfg, channelsList: CHANNELS, version: app.getVersion(), platform: process.platform }));
ipcMain.handle("cfg:save", (_e, c) => {
  cfg.topic = String(c.topic || "").trim();
  cfg.channels = (c.channels || []).filter((s) => CHANNELS.some(([v]) => v === s));
  if (!cfg.channels.length) cfg.channels = [""];
  cfg.url = String(c.url || DEFAULT_URL).trim() || DEFAULT_URL;
  cfg.autostart = !!c.autostart;
  saveCfg(); applyAutostart(); connect();
  if (win && !win.isDestroyed()) win.loadURL(dashboardUrl());
  return true;
});
ipcMain.handle("notify:test", () => {
  notify({ title: "🇺🇸🇩🇪 🔥 HOT: Trend Radar works!", body: "📰 This is how a trend notification looks.\n🌍 USA, Germany · Politics\n🕒 since 2h · 12 articles in the last hour" });
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
