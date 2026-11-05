## Trend Radar – desktop app (Windows + Mac)

Trends, breaking news, sports and natural disasters for the USA, Germany and Europe – in its own window, with notifications.
The radar runs in the cloud 24/7; this app shows it and notifies you. Nothing else to install.

**New in 1.3:** Settings has a **🧠 AI & API key** box at the top (Ctrl+, / Cmd+,). Choose the briefing engine:
No AI (free, no key), Ollama (free, on your computer), Google Gemini (free key) or OpenAI. The app also tells you when a new version is out.
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
