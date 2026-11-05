# Trend Radar – trends & breaking news radar (USA · Germany · Europe)

Trend Radar watches what is trending and what just happened in the **USA, Germany (+ Austria, Switzerland), UK, France,
Italy, Spain and Europe** – news, search trends, X, sports, music, movies, tech, stocks and natural disasters – scores
every topic, and notifies you about the ones that matter. It is built for video creators who need to know **what to
film next**.

It runs **in the cloud every 15 minutes, 24/7**, even when your computer is off.

| Where | What you get |
|---|---|
| 📱 Phone | notifications through the free **ntfy** app |
| 💻 Windows / 🍎 Mac | the **Trend Radar desktop app**: dashboard window + notifications you filter yourself |
| 🌐 Browser | the online dashboard: **https://fatimazahra789078.github.io/trend-radar/** |
| 🧠 Twice a day | a **Claude briefing** (09:00 and 18:00 Morocco time): top 5 video ideas with facts, titles, hooks, hashtags |

---

## 1. Desktop app (Windows + Mac)

Download: **https://github.com/fatimazahra789078/trend-radar/releases/latest**

| Computer | File | How |
|---|---|---|
| Windows | `TrendRadar-Setup-x.y.z.exe` | install. If you see "Windows protected your PC" → **More info → Run anyway** |
| Windows (no install) | `TrendRadar-Portable-x.y.z.exe` | double-click, works from a USB stick |
| Mac (Intel + Apple Silicon) | `TrendRadar-mac.dmg` | drag the app to **Applications** → first start: **right-click → Open → Open**. If it says "damaged": run `xattr -cr "/Applications/Trend Radar.app"` in Terminal |

On first start, **Settings** opens:

- **Your ntfy topic** – the secret topic (same as in the phone app). Saved only on that computer.
- **How many notifications?**
  - *Very important only* (default) – breaking news, hot trends, "just in", trends that keep repeating, big disasters, the briefing
  - *Important + trending* – also normal trends, top news, sports results, watchlist
  - *Everything* – also digests, music charts, reminders
- **Countries** – e.g. **USA only** (one click), Europe, or any mix.
- **Topics** – politics, world & conflicts, natural disasters, crime & accidents, sports, movies & TV, music, gaming,
  tech & AI, business, celebs & viral.
- **Types of alerts** – breaking, just in, hot, repeating, trending, top news, disasters, sports results, live games,
  watchlist, briefing, digest, music charts, events…

The app lives in the **tray** (Windows) / **menu bar** (Mac) and starts with the computer. Its menu has quick
switches: *Notify me about…* (importance) and *Countries* (All / USA only / Germany only / Europe only / USA + Germany).
Notifications that arrived while the computer was asleep are shown when it wakes up (ntfy keeps 12 hours).

---

## 2. Phone (ntfy)

ntfy is only the **messenger**: the radar writes the notification, ntfy delivers it to your phone.

1. Install **ntfy** (Android: Play Store · iPhone: App Store – free).
2. Tap **+** → *Subscribe to topic* → type your topic (it is in `config.local.json` on your PC – keep it secret,
   anyone who knows it can read your alerts).

Pick the **channels** you want (your topic + an ending):

| Channel | What arrives |
|---|---|
| `your-topic` | **very important only** (breaking, hot, just in, repeating, big disasters, briefing) |
| `your-topic-all` | everything |
| `your-topic-us` | USA – trending and up (+ a "Top trends USA" digest every 3 hours) |
| `your-topic-de` | Germany / Austria / Switzerland – trending and up |
| `your-topic-eu` | Europe (UK, France, Italy, Spain…) – trending and up |
| `your-topic-sports` | sports results and sports trends |
| `your-topic-disasters` | natural disasters + breaking news |
| `your-topic-ai` | AI video / image / voice tools: new models + news (Seedance, Kling, Veo, LTX, Wan...) + GitHub repos everyone is starring |

Example – **USA only**: subscribe to `your-topic-us` and nothing else.
On Android you can also set a *minimum priority* per subscription (urgent = 5, very important = 4, normal = 3, low = 2).
The **Dashboard** button in each notification opens the online dashboard on the matching page (USA, disasters…).
Tip: open the dashboard on the phone and choose **Add to Home screen** – it then opens like an app.

---

## 3. What the radar watches

- **Search trends:** Google Trends (US, DE, AT, CH, GB, FR, IT, ES, NL)
- **X / Twitter:** trends24 (US, DE, UK, FR, IT, ES) – including how many hours a trend lasted
- **News:** Google News (top + sports + entertainment + tech + business) in 6 countries, plus
  Tagesschau, ZDFheute, SPIEGEL, DW · NPR, NYT, CBS, Fox · BBC, The Guardian, Sky News · France24, Le Monde, franceinfo ·
  ANSA, Corriere, Repubblica · El País, RTVE, 20minutos · Euronews, Politico Europe
- **Wikipedia:** most read pages (en, de, fr, it, es)
- **Community:** Reddit (r/popular, r/de), Hacker News
- **Sports (ESPN):** NFL / Super Bowl, NBA, MLB, NHL, college football, UFC, MLS, Bundesliga, DFB-Pokal,
  Champions League, Premier League, LaLiga, Serie A, Ligue 1
- **Music:** Apple Music top songs in 6 countries · **Movies:** iTunes top movies · **Stocks:** Yahoo Finance trending
- **Natural disasters:** USGS + EMSC (earthquakes), GDACS (UN alerts: cyclones, floods, volcanoes, wildfires, droughts),
  NWS (US weather warnings), NASA EONET
- **GDELT:** is coverage of a topic accelerating?
- **Watchlist:** a news search for each of your words (Tesla, GTA 6, Avengers, Super Bowl…)
- **AI tools for creators:** news search for Seedance, Kling, Veo, Hailuo, Runway, Pika, Luma, Midjourney, Nano Banana,
  Seedream, FLUX, LTX, Wan, HunyuanVideo, ComfyUI, Higgsfield, ElevenLabs, Suno… · **new open models trending on
  Hugging Face** (text-to-video, image-to-video, text-to-image, text-to-speech – most run free on your own PC with
  ComfyUI) · TechCrunch AI, The Verge AI, The Decoder, Reddit r/aivideo. The dashboard tab **🎬 AI tools** also has a
  tools guide (`ai_tools.json`, edit it freely).
- **GitHub:** the repos with the most new stars today and this week (github.com/trending, all languages) and the
  most-starred **new** repos of the last 30 days for AI video, video generation, AI images, ComfyUI, AI voice, AI agents,
  LLM tools and MCP / Claude tools (GitHub search). Shown in the **🎬 AI tools** tab. Change the topics and limits in
  `config.json` → `github`. NSFW / cheat repos are filtered out.

If a source fails (for example Reddit refusing servers), the radar continues with the others.

---

## 4. Alert types

| Alert | Meaning |
|---|---|
| 🚨 BREAKING | urgent news from a trusted source – "verification pending" until several sources confirm |
| ⚡ JUST IN | 4+ news sites wrote about it in the last hour – it just happened |
| 🔥 HOT | very big trend (many sources, several countries) |
| 🔁 STILL TRENDING · DAY 2 | keeps coming back day after day (day 2, 3, 5, 7) – good for longer videos |
| 📈 TRENDING | new trend that is rising |
| 📰 TOP NEWS | big headline that is not (yet) a search trend |
| 🌍 EARTHQUAKE / 🌀 RED ALERT / ⚠️ USA warning | natural disasters (M6+ worldwide, M5+ Europe, M4.5+ in your countries; GDACS orange/red; US tornado, hurricane, extreme…) |
| 🏆 FINAL / 🔴 LIVE | big games: playoffs, Super Bowl, finals, special games, your teams |
| ⭐ WATCHLIST / ⚡ SPIKING | new articles about your words (max every 6 h per word) / 10+ articles in 2 hours |
| 🎵 | new #1 or new top-10 song |
| 📅 | event reminder (7 days, 2 days and on the day) |
| 📊 | top trends every 3 hours |
| 🧠 | Claude briefing |
| 🎬 NEW AI MODEL | a new open AI video / image / voice model reached the top 5 on Hugging Face |
| 🏆 TODAY'S TOP 3 VIDEOS | twice a day (06:00 and 15:00 UTC): the 3 best videos to make now – phase, time left, YouTube competition, what people search |
| ✈️ NOT IN GERMANY YET | trending in the USA / UK for 2+ hours but not yet in Germany / France / Italy / Spain – make that language version first |
| ⭐ GITHUB TRENDING / 🆕 NEW ON GITHUB | a repo entered the top 10 of GitHub Trending with 300+ new stars today, or a repo younger than 30 days passed 1,000 stars (very important if it is an AI tool with 1,500+ stars today) |

"also: …" means several trends about the same story were grouped into one notification.

**Score** (hover the number in the dashboard to see why): search volume + X ranking + number of news sites + new
articles in the last hours + number of countries + how long it keeps coming back. Hot ≥ 18, trending ≥ 10.

---

## 5. Dashboard

Online: **https://fatimazahra789078.github.io/trend-radar/** (add `#today`, `#us`, `#de`, `#eu`, `#disasters`,
`#sports`, `#ai` or `#ideas` to open a page directly).

- **🎯 Make today** – which video to make **now**. Every topic gets a **video score** = trend strength × freshness ×
  phase × YouTube competition × categories that get views (+ a bonus when it has not reached your other countries yet):
  - **Phase:** 🌱 rising (about 6–12 h left) · 🔥 at the peak (about 3–6 h left) · 📉 falling (only with a new angle)
  - **YouTube competition** (needs the free `YOUTUBE_API_KEY` secret): how many videos were uploaded about it in the
    last 24 h – 🟢 GO NOW (≤5) · 🟢 GOOD (≤20) · 🟡 BUSY · 🔴 CROWDED (50+), plus the views per hour of the top videos.
    Default: **USA only** (`config.json` → `youtube.countries`), so the free quota is not spent on other countries
  - **TikTok / Instagram / Facebook:** these have no free public data API, so the radar reads the news instead
    ("viral on TikTok", "Instagram Reels"…) and shows 📱 *In the news as big on*; one-click buttons open the same
    search on YouTube (today), TikTok, Instagram and Facebook
  - **Shared with friends:** the radar runs once in the cloud and everybody uses the same dashboard, phone channel and
    desktop app – one YouTube key (added once by the owner) serves everyone; each person may add their own free Gemini
    key in the app for the AI briefing
  - **People search:** what people type in the YouTube search box, in English and the country's language
  - **✈️ Travelling trends:** trending in the USA / UK, not yet in DE / FR / IT / ES, with the usual delay per country
  - ⚠️ **Sensitive** topics (death, war, crime…): YouTube may limit ads

- **Trends** – everything ranked by score; filters for USA / Germany / UK / France / Italy / Spain / Europe /
  Hot / Just in / Repeats / Watchlist / category; each card shows since when (first and latest article), research
  links (News, YouTube, TikTok, X, trend graph) and **video ideas** in the audience's languages.
- **💡 Ideas** – what to film now: *Film this now* · *One topic, many countries* · *Long trends* · *Prepare before it
  happens*, with formats, titles (EN / DE / FR / IT / ES), hashtags and the best posting time (Morocco time).
- **Top news** – what each country is talking about, by category, with how long ago each story came out.
- **🌍 Disasters** – disaster news, earthquakes (24 h), GDACS alerts, US warnings, NASA events.
- **Watchlist · Sports · Charts · Upcoming · Best sites · Sent**.

---

## 6. How to use it for videos

**Posting times (Morocco time = UTC+1, same as Berlin in winter; New York −6 h; Los Angeles −9 h):**
USA 17:00–21:00 and 00:00–02:00 · Germany / France / Italy / Spain 18:00–21:00 · UK 19:00–22:00.

1. Open **🎯 Make today** first (or wait for the 🏆 TOP 3 notification), then **💡 Ideas**.
2. **Breaking / Just in / Hot** → short video within 2–6 hours; check YouTube and TikTok first – if there are already
   many videos, take a different angle.
3. **Repeating trends** (day 2+) → longer explainer or a series.
4. **Trending in several countries** → one video in 2–3 languages.
5. **Upcoming events** → publish 1–3 days before; people search early.
6. Sensitive topics (death, crime, war, disasters): only say what two trusted sources confirm.

---

## 7. Settings (`config.json`)

- `watchlist` – your words (each gets its own news search)
- `watch_teams` – your teams (full ESPN names)
- `focus_countries` – your audience countries
- `hot_score` / `trend_score` – higher = fewer alerts
- `phone_important_priority` (4) / `phone_country_min_priority` (3) – what goes to the main / country phone channels
- `just_in_outlets`, `repeat_notify_days`, `digest_hours`, `quiet_hours`, `max_toasts_per_run`
- `disasters` – earthquake magnitudes and GDACS levels
- `extra_feeds` – add any RSS (e.g. a Talkwalker Alerts feed)
- `video_planner` – top 3 times, travel countries, travel alerts
- `youtube` – how much of the free YouTube quota the radar may use (`daily_units`, default 9,000 of 10,000)
- `youtube_api_key` – optional (cloud: secret `YOUTUBE_API_KEY`): YouTube competition check + YouTube trending videos

Secrets are never in `config.json`: on the PC they are in `config.local.json` (not uploaded), in the cloud in the
GitHub secret `NTFY_TOPIC`. Events (calendar): `events.json`.

After changing `config.json`, commit and push it – the cloud uses the version on GitHub.

---

## 8. How it runs

| Part | Where | Schedule |
|---|---|---|
| Radar (`trend_radar.py`, Python standard library only) | GitHub Actions – `.github/workflows/radar.yml` | every 15 minutes |
| Memory (`state.json`) + snapshot (`latest.json`) | branch `data` | every run |
| Online dashboard | GitHub Pages | every run |
| Claude briefing | Claude routine → branch `claude/briefing` → sent by the next radar run | 09:00 and 18:00 Morocco time |
| Desktop app | `desktop/` (Electron) – built by `.github/workflows/desktop.yml` | when you run the workflow |

Useful commands (in this folder):

```bash
python trend_radar.py --report
```
(one check without notifications, prints the ranking)

```bash
python trend_radar.py --test
```
(sends a real example notification)

The local Windows radar (`INSTALL.cmd` / `UNINSTALL.cmd`) is optional now – the cloud and the desktop app replace it.

---

### What costs what

| Part | Cost |
|---|---|
| GitHub Actions (radar), GitHub Pages (dashboard), the download page | free (public repository) |
| ntfy (phone notifications) | free |
| YouTube Data API (competition check) | free – 10,000 units a day; the radar uses at most 9,000 (about 85 checks a day + trending videos) |
| Desktop app | free |
| Claude briefing routine (2 runs a day) | uses your Claude plan's usage – pause or delete it at https://claude.ai/code/routines |

Note: GitHub runs scheduled jobs "best effort" – when GitHub is busy, the 15-minute check can run less often
(seen: about once an hour). Notifications still arrive, just later.

---

## 9. Troubleshooting

- **No notification on Windows:** Settings → System → Notifications → "Trend Radar" must be on, Focus assist off.
- **No notification on the phone:** check the topic in ntfy, and that the cloud runs: GitHub → `trend-radar` → **Actions**.
- **Too many notifications:** desktop app → *Very important only*; phone → subscribe only to the main channel
  (`your-topic`), not to `-all`.
- **Rebuild the desktop app after a change:** GitHub → Actions → **Desktop app** → **Run workflow**.

---

## 10. Credits & sources

Data from Google Trends, Google News, trends24, Wikipedia/Wikimedia, Reddit, Hacker News, ESPN, Apple, Yahoo Finance,
USGS, EMSC, GDACS, NWS/NOAA, NASA EONET, GDELT and the listed news publishers' RSS feeds. Notifications via ntfy.sh.
