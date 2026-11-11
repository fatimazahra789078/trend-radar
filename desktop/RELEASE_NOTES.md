## Trend Radar – desktop app (Windows + Mac)

Trends, breaking news, sports and natural disasters for the USA, Germany and Europe – in its own window, with notifications.
The radar runs in the cloud 24/7; this app shows it and notifies you. Nothing else to install.

**New in 1.3:** Settings has a **🧠 AI & API key** box at the top (Ctrl+, / Cmd+,). Choose the briefing engine:
No AI (free, no key), Ollama (free, on your computer), Google Gemini (free key) or OpenAI. The app also tells you when a new version is out.
**1.5.1:** your keys (Gemini, YouTube, OpenAI) and ntfy topic are stored **encrypted** with Windows / macOS protection instead of plain text · warning when the cloud radar has been **silent for 3 hours** (notification + tray tooltip).

**New in 1.5:** 🔔 **Inbox** (menu → Inbox, Ctrl+I, or click the tray icon when something is unread): every notification stays readable - the ones that popped up and the ones your filters skipped - with search and unread count. 🎮 **Games** and 📚 **Books** pages in the menu. New alert type **GAME** (a mobile game new in the top free list or climbing fast).

**1.4.1:** 🌐 button on the dashboard and **Alt+Shift+T** to switch between your language and English on the spot · Gemini **model list** in Settings: pick a model, **Test** it or **Test all** (✓ / ✗ saved); Auto uses the newest *flash-lite* (more free requests) · clearer explanation of the ntfy topic.

**New in 1.4:** 🌐 **Trends in your language** (Settings → 🧠 AI & API keys): the whole dashboard and the notifications are translated automatically from English into Arabic, French, Spanish, German, Italian, Portuguese, Turkish or Dutch - free Google Translate, no key, does not use your Gemini quota. **Test** buttons next to every key (green = works, red = what is wrong). 🔁 badge + "What happened" on trends that keep repeating.

Also in 1.4: Settings → 🧠 AI & API keys has a **▶️ YouTube API key** field (free, optional). With it the app checks how many YouTube videos already exist about the top USA topics (🟢 GO NOW · 🟢 GOOD · 🟡 BUSY · 🔴 CROWDED) every hour, inside your free quota, and shows it in 🎯 Make today and in the briefing. No GitHub step needed.
1.3.3: new alert types **TOP 3** (today's 3 best videos to make, twice a day) and **TRAVELING** (trending in the USA/UK, not yet in your other countries); menu → 🎯 Make today.
1.3.2: new alert type **GITHUB** – repos everyone is starring (GitHub Trending + new AI tools); it is switched on automatically.
1.3.1: the AI & API key box is now the second box in Settings, with jump links at the top, and the window fits small Mac screens.

You choose what you get: importance, countries (e.g. USA only), topics and alert types.

### Windows
- **TrendRadar-Setup-x.y.z.exe** → install (Start menu + desktop icon, starts with Windows).
- **TrendRadar-Portable-x.y.z.exe** → no install, just double-click (e.g. from a USB stick).
- Windows may say "Windows protected your PC" (the app is not signed): click **More info → Run anyway**.

### Mac (Intel and Apple Silicon)
- **TrendRadar-mac.dmg** → open it and drag **Trend Radar** into **Applications**.
- First start: **right-click the app → Open → Open** (the app is not signed by Apple).
- If macOS says the app is "damaged": open Terminal and run `xattr -cr "/Applications/Trend Radar.app"`, then open it again.

### First start
Settings opens by itself: paste **your ntfy topic** (the same one as in the ntfy phone app), choose what you want to be
notified about, click **Save**. Your topic stays only on that computer.
