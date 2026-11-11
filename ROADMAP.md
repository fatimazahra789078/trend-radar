# Trend Radar – audit and roadmap (11 November 2026)

## What works well

- **Runs alone, 24/7:** GitHub Actions ran 29 of the last 30 checks without error (about once an hour), also when every PC is off.
- **220+ sources, 4,500 signals per check:** Google Trends, X, Google News (6 countries), 60+ official feeds, Wikipedia, Reddit, Hacker News, ESPN, Apple Music, Yahoo, GDELT, USGS / EMSC / GDACS / NWS / NASA, Hugging Face, GitHub, App Store game charts, Steam, itch.io, Apple Books.
- **One cloud serves everybody:** friends install the same app, read the same dashboard and phone channel; only a free Gemini key (and a YouTube key if wanted) is personal.
- **Decides, not only detects:** video score, phase + time window, YouTube competition (USA), travelling trends, TOP 3 twice a day, briefing (Gemini / Ollama / none).
- **Readable in your language:** the whole dashboard and the notifications in Arabic, French… with free Google Translate, switchable on the spot.
- **Costs nothing:** GitHub, GitHub Pages, ntfy, Google Translate, YouTube and Gemini free tiers.

## What was wrong – and the fix

| Problem found | Why it matters | Fix (done unless noted) |
|---|---|---|
| **~150 alerts a day** on the `-all` channel (63 trends, 50 watchlist, 26 "more") | noise; you stop reading | watchlist cooldown 6 h → **12 h**; extra alerts per check 4 → **3**; the app's **Inbox** keeps everything readable, so the filters can stay strict ("Very important only") |
| **Cloud memory 15 MB** (topics kept 7 days, long key lists) | every check downloads and re-uploads it; slower; GitHub may complain | topics kept **4 days**, key lists halved → about 3–4 MB |
| **One check marked failed** (GitHub Pages hiccup while publishing the dashboard) | red run, confusing; the data was fine | the publish step is now **non-fatal**; the next run publishes again |
| **Repubblica** blocks the cloud (HTTP 403) | Italy had one feed less | replaced by **Corriere della Sera** |
| **Reddit** sometimes answers 429 from the cloud | community signal missing for an hour | already falls back to the last good copy (up to 6 h); nothing more to do without an API key – Reddit blocks data-center IPs |
| **Notifications disappear**; nothing to read later | you miss alerts while working | **🔔 Inbox** in the app (Ctrl+I, tray icon): all received alerts, search, unread count, "skipped by your filters" view |
| **Search** only in the Trends tab | hard to find a game, repo or old alert | **Search everything** box in the header (Ctrl+K) |
| Trend names mistranslated ("Lens" → "lens") | confusing in Arabic | names keep the **original next to the translation** |
| GitHub runs the 15-minute schedule about **hourly** | alerts arrive later than possible | **not fixed** (GitHub "best effort"); fix = an external free cron pinging `workflow_dispatch` every 15 min – say if you want it |
| Mac build never tested on a real Mac | unknown bugs on macOS | **open** – needs a Mac to try the .dmg once |
| TikTok / Instagram / Facebook have no free data | can't count competition there | news-based "buzz" signal + one-click search buttons; no legal free API exists |

## Where the money is for a trend creator (priority order)

1. **Speed:** trend → published video in under 3 hours. Use 🎯 Make today + TOP 3; the Inbox so nothing is missed.
2. **Right market:** ✈️ travelling trends – be first with the German / French / Italian / Spanish version.
3. **Low competition:** YouTube 🟢 GO NOW / GOOD before filming (needs your free YouTube key in the app).
4. **Second income – games:** 🎮 Games tab, clone score ≥ 60 = a simple game that is proven in the charts; remake it with a new theme (the hyper-casual model: Voodoo, Homa, Rollic, SayGames).
5. **Third income – books:** 📚 Books tab; low-content and guide books on repeating trends; never trademarked names.

## Next phases

**Phase 2 – produce faster (2–3 weeks)**
- "Video pack" button per trend (Gemini free): 30–60 s script EN + DE (+ FR/IT/ES), 3 titles, thumbnail text, hashtags, B-roll prompts for Kling / Seedance / Veo.
- Monetization check: ⚠️ limited-ads topics (death, war, crime, drugs) and "not yet confirmed" warnings before you post.
- Competitor watch: 10–20 channels in your niche (free YouTube feeds) – alert when one of their videos does 3× its normal views.
- Games: Google Play signal via the same App Store ids (unofficial, best effort) and a "mechanic" label from the description (merge, sort, parking, idle…).

**Phase 3 – learn from your channel (month 2)**
- Connect your YouTube channel (free API): the radar learns which topics / countries / formats work for *you* and re-weights the video score.
- Production board in the app: Idea → Script → Recorded → Published → Views; measures trend-to-publish time.
- Multiply each video by 5 languages: translation + voice (ElevenLabs, or free local Kokoro / Piper).

**Phase 4 – look ahead (month 3)**
- Calendar of coming trends (releases, finals, award shows, anniversaries, local holidays) with "prepare 3 days before" alerts.
- After weeks of data: which early signals predicted the big trends → earlier alerts.

## Numbers to watch

| Metric | Target |
|---|---|
| Trend → published | < 3 h |
| Videos above your channel average | > 50 % |
| Alerts you turn into videos | ≥ 1 in 5 |
| Game clone score of what you build | ≥ 60 |
