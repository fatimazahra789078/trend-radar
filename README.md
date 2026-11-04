# Trend Radar – nidam dial trendat o l'akhbar (USA · Germany · Europe)

Had l'programme kaykhdem bo7do f PC dyalk: **kol 15 d9i9a** kayjm3 ga3 li trend f USA, Almania o Europe,
kay7seb chno kbir o chno kay3awd bzaf, o kaysifet lik **notification f PC** o **f telephone** (ntfy).

---

## 1. Chno kayn daba (installed)

| Chno | Fin |
|---|---|
| Check automatique kol 15 d9i9a (Task Scheduler "TrendRadar") | kaybda m3a Windows, khdam 7ta 3la battery |
| Notifications Windows ("Trend Radar") | f la9ine dyal notifications |
| Notifications f telephone | app **ntfy** (chouf r9m 3) |
| Icon f Desktop **"Trend Radar"** | click = check daba + y7el dashboard |
| Dashboard | `dashboard.html` (kayt7el f browser) |

**Mlli tclicki 3la notification** → kay7el l'khbar. Les boutons: **Open** (l'khbar), **YouTube** (videos jdad 3la nafs topic), **Dashboard**.

### Ila kan PC tafi (wla f veille) – "While you were away"

Mlli tch3el PC, b3d **2 d9aye9** (bach Wi-Fi ytconnecta), l'programme kaychouf ch7al kan tafi, o kaysifet lik **notification wa7da**:

* 📥 **While you were away (14h)**: top 8 trends li w9e3o
* 🏆 **Results while you were away**: natayej dyal les matchs kbar li fatouk (kayjib 7ta natayej dyal lbare7)
* ⭐ **Watchlist while you were away**: ch7al mn khbar jdid 3la kol kelma (Tesla, GTA 6...)
* 🚨 Breaking dyal akhir 2 s3at kayjik bo7do

O f dashboard kayban **cadre "While you were away"** lfo9 (12 s3a). Ila kanet internet mazal ma khdamach, ma kaysifet walo o kay3awd f check li moraha.

---

## 2. Ach kayjme3 (les sources li testit o khdamin)

**Bldan:** 🇺🇸 USA · 🇩🇪 Almania (+ Austria, Switzerland) · 🇬🇧 UK · 🇫🇷 France · 🇮🇹 Italia · 🇪🇸 Spain · 🇪🇺 Europe

* **Trends dial recherche**: Google Trends (US, DE, AT, CH, GB, FR, IT, ES, NL)
* **X / Twitter**: trends24 (US, DE, UK, FR, IT, ES) – o kay3ref ch7al mn sa3a b9a trend
* **Akhbar**: Google News (top + Sports + Entertainment + Tech + Business) f 6 bldan
  * 🇩🇪 Tagesschau, ZDFheute, SPIEGEL, DW · 🇺🇸 NPR, NYT, CBS, Fox
  * 🇬🇧 BBC UK, BBC World, The Guardian, Sky News · 🇫🇷 France24, Le Monde, franceinfo
  * 🇮🇹 ANSA, Corriere, Repubblica · 🇪🇸 El País, RTVE, 20minutos · 🇪🇺 Euronews, Politico Europe
* **Wikipedia**: chno nas kay9raw bzaf (en, de, fr, it, es)
* **Reddit** r/popular + r/de, **Hacker News** (tech)
* **Sport (ESPN)**: NFL (Super Bowl), NBA, MLB, NHL, College Football, UFC, MLS, Bundesliga, DFB-Pokal, Champions League, Premier League, LaLiga, Serie A, Ligue 1
* **Musique**: Apple Music top songs f 6 bldan (new #1 o new top 10 → notification)
* **Aflam**: iTunes top movies US + Google News Entertainment + Wikipedia
* **Stocks / Tesla...**: Yahoo Finance trending tickers (TSLA, NVDA...)
* **GDELT**: kaychof wach l'akhbar 3la topic kaytzadou b zerba (acceleration)
* **Watchlist**: kol kelma 3ndha recherche Google News dyalha (Tesla, GTA 6, Avengers, Super Bowl...)

Ila chi source t7bes (b7al Reddit "429"), l'programme kaykmel b lba9i o kayst3mel akhir data mzyana.

---

## 3. Telephone (ntfy) – chno hiya o kifach

**ntfy machi programme b7al dyalna, o machi a7ssan menno.** Hiya ghir **l'facteur** li kayhez notification mn PC l telephone:

```
Trend Radar (PC dyalk)  ──►  serveur ntfy.sh  ──►  app ntfy (telephone)
   kayl9a trends,             kaydouz l'message      kayseft lik
   kay7seb, kaykteb           (mjjani)               notification
```

* **Trend Radar** = l'mokh: kayjm3, kay7seb, kaykhtar chno yseft.
* **ntfy** = ghir l'tri9 l telephone. Bla biha, notifications kayjiwk ghir f PC.
* **Topic** (mktob ghir f `config.local.json` f PC dyalk – machi f GitHub) = r9m dyal sondo9 l'barid dyalk. Li 3ref had r9m y9der y9ra nafs notifications (ghir akhbar 3amma, walo chakhsi) – 3la hadi khlih secret.

**Installation:**

| Fin | Kifach |
|---|---|
| **Android** | Play Store → "ntfy" → Install → **+** → kteb topic → Subscribe |
| **iPhone** | App Store → "ntfy" → Install → **+** → kteb topic → Subscribe |
| **Mac / Windows (akhor)** | ma kaynach app 3adia: 7el **https://ntfy.sh/app** f Chrome / Edge / Safari → **+ Subscribe** → kteb topic → 9bel "notifications". F Chrome / Edge t9der dir "Install app" (icon f bar dyal adresse) bach twli b7al app. |
| **Had PC Windows** | ma m7tajch ntfy – Trend Radar deja kayseft notifications dyal Windows. |

### Channels f telephone (filter: USA bo7dha, Almania, Europe, sport, kawarit)

F l'app ntfy, kol channel = topic dyalk + **nihaya**. Dir **+** o subscribe **ghir l li bghiti**:

| Channel | Kteb f ntfy | Chno kayjik |
|---|---|---|
| Kolchi | `topic dyalk` | ga3 notifications |
| 🇺🇸 **USA bo7dha** | `topic dyalk` + **`-us`** | ghir li fih USA (+ résumé "Top trends USA" kol 3 s3at) |
| 🇩🇪 Almania | + `-de` | Almania / Austria / Switzerland |
| 🇪🇺 Europe | + `-eu` | UK, France, Italia, Spain... |
| ⚽ Sport | + `-sports` | natayej o trends dyal sport |
| 🌍 Kawarit + breaking | + `-disasters` | zalazil, a3asir, fayadanat, 7ra2e9, vulkan, breaking |

Mtalan bach tchof **ghir USA**: subscribe l `trendradar-...-us` (b nafs r9m dyalk) o ma tsubscribich l "kolchi" (bach ma ytkerrouch).
Bouton **Dashboard** f kol notification kay7el dashboard **3la nafs l'filtre** (USA, disasters...).

### Dashboard b7al app f telephone
7el dashboard online f Chrome (Android) wla Safari (iPhone) → menu → **"Add to Home screen"**. Ghaytla3 lik icon **Trend Radar** f telephone, o kayt7el b7al app (bla barre dyal browser).

⚠️ ntfy kayseft ghir mlli **PC dyal Trend Radar ch3el**. Ila PC tafi, mlli tch3lo kayjik "While you were away" (f PC o f telephone).

Ila bghiti Telegram wla Discord f blast (wla m3a) ntfy: 3mer `telegram_bot_token` + `telegram_chat_id` wla `discord_webhook` f `config.json`.

---

## 3b. App dyal PC o Mac (Trend Radar Desktop)

Nzelha mn: **https://github.com/fatimazahra789078/trend-radar/releases/latest**

| PC | Fichier | Kifach |
|---|---|---|
| Windows | `TrendRadar-Setup-x.exe` | installer. Ila tla3 "Windows protected your PC" → **More info → Run anyway** |
| Windows (bla installation) | `TrendRadar-Portable-x.exe` | double-click, t9der t7ttha f clé USB |
| Mac (Intel + M1/M2/M3/M4) | `TrendRadar-mac.dmg` | jerr l'app l **Applications** → l'awel mra: click limen → **Open** → **Open**. Ila gal "damaged": f Terminal `xattr -cr "/Applications/Trend Radar.app"` |

F l'awel lancement kat7el **Settings**: colli topic dyalk, khtar channels (mtalan **USA only**), Save.
L'app kat werik dashboard f window dyalha, kat b9a f tray / menu bar, o kat seft notifications dyal Windows / Mac (7ta li fatouk mlli kan PC f veille).
Ila zedti chi 7aja f `desktop/`, 3awd tbniha: GitHub → **Actions** → **Desktop app** → **Run workflow**.

## 4. Anwa3 dyal notifications

| Icon | Ma3nah |
|---|---|
| 🚨 BREAKING | khbar 3ajel mn source ti9a (Tagesschau, NPR, BBC...) – "verification pending" ila ba9i source wa7ed |
| ⚡ JUST IN | **yallah w9e3**: 4+ sites dyal akhbar ktbo 3lih f akhir sa3a (kayban ch7al mn article o mn imta bda) |
| 🔥 HOT | trend kbir bzaf (bzaf dyal sources + bzaf dyal bldan) |
| 🔁 STILL TRENDING · DAY 2 | trend li **kay3awd** o mazal kbir f nhar 2, 3, 5, 7 → mzyan l video twila / série |
| 📈 TRENDING | trend jdid kaytl3 |
| 📰 TOP NEWS | khbar kbir f top news wakha mazal ma wlach recherche |
| ⭐ WATCHLIST | khbar jdid 3la kelma mn list dyalk (max mra kol 6 s3at l kol kelma) |
| ⚡ SPIKING | kelma mn watchlist fiha 10+ articles f 2 s3at (daghya) |
| 🌍 EARTHQUAKE M6.1 | zalzal: M6+ f l3alam, M5+ f Europe, M4.5+ f bldan dyalk (USGS + EMSC) – ch7al hadi, 3m9, tsunami |
| 🌀 / 🌊 / 🔥 / 🌋 RED · ORANGE ALERT | kawarit kbar mn GDACS (UN): a3asir, fayadanat, 7ra2e9, vulkan, jafaf |
| ⚠️ USA: Tornado Warning x5 | tanbihat rasmiya dyal l'jaww f USA (tornado, hurricane, extreme...) |
| 🏆 FINAL / 🔴 LIVE | natija dyal match kbir (playoffs, Super Bowl, finals, teams dyalk) |
| 🎵 | #1 jdid wla song jdida dkhlat top 10 (US / DE) |
| 📅 | event 9rib (9bel b 7 ayam, 2 ayam, o nhar l'event) |
| 📊 | résumé dyal top trends kol 3 s3at |

**"also: ..."** = trends li kayhdro 3la nafs l'9issa jaw f notification wa7da (bach ma tjikch 10 notifications 3la midterms).

**Score** (f dashboard, 7et souris 3la r9m bach tchof 3lach): recherche + ranking f X + ch7al mn site dyal akhbar + articles jdad f 2 s3at + ch7al mn blad + ch7al mn mra rje3 (s3at / iyam). **Hot ≥ 16**, **Trending ≥ 9**.

---

## 5. Dashboard – les onglets

* **Trends**: kolchi mrteb b score. Filter: USA / Germany / UK / France / Italy / Spain / Europe / 🔥 Hot / ⚡ Just in / 🔁 Repeats / ⭐ Watchlist / category (Sports, Politics, Music, Movies, Gaming, Tech, Business...). Tri: Biggest · Newest · Rising fastest · Repeats most.
  F kol carte: 🕒 **mn imta bda** ("first article 3h ago · latest 4 min ago · 12 in the last hour"), liens News · YouTube · TikTok · X · Trend graph, o **Video ideas** (titres b lugha dyal kol blad + hashtags).
* **💡 Ideas**: **afkar li tjib views daba**, mrtbin b chance dyal views (jdid + kayt l3 + f bzaf dyal bldan + categories li kayjibo views):
  * 🚀 **Film this now** – jdid o kaykber: video sghira, postiha daghya
  * 🌍 **One topic, many countries** – video wa7da b 2–3 lughat
  * 🔁 **Long trends** – explainer twil / série
  * 📅 **Prepare before it happens** – events f 10 ayam jayin
  
  F kol fikra: formats (chno t9der tsowr), titres EN/DE/FR/IT/ES, hashtags, o **wa9t l'posting b wa9t l'Maghrib**.
* **Top news**: chno kol blad kat hder 3lih daba (Almania / USA / UK / France / Italia / Spain), b category, o **ch7al hadi khrej kol khbar** ("16 min ago").
* **🌍 Disasters**: kawarit tabi3iya: akhbar 3la kawarit, zalazil dyal 24 sa3a, tanbihat GDACS (red / orange), tanbihat l'jaww f USA, NASA (7ra2e9, a3asir, vulkan).
* **Watchlist**: akhir akhbar 3la kol kelma dyalk.
* **Sports**: live, big games jayin, natayej.
* **Charts**: top songs USA + Almania, top movies, stocks trending, Hacker News.
* **Upcoming**: calendar dyal events (GTA VI, Avengers, Thanksgiving, Black Friday...).
* **Best sites**: ga3 les sites li khasek t3ref.
* **Sent**: ga3 notifications li tsiftou.

---

## 6. Planning – kifach tkhdem b had nidam (routine yawmia)

**Wa9t (Maroc = UTC+1, daba nafs wa9t Berlin; New York = Maroc − 6 s3at; Los Angeles = − 9):**

| Wa9t f Maroc | Chno tdir |
|---|---|
| 09:00–10:00 | 7el dashboard: chno wa9e3 f lil f USA (lil dyalhom = sbah dyalk). Khtar 1–2 topics. |
| 10:00–14:00 | Sowb videos dyal Almania (hiya f nafs wa9t dyalk). |
| **17:00–21:00** | **Wa9t dhabi**: Almania f la soirée + USA f l'3chiya (11:00–15:00 NY). Postei hna. |
| 00:00–03:00 | Prime time USA (18:00–21:00 NY) – ila 3ndek video USA, programmih l had wa9t. |

**Wa9t l'posting (b wa9t l'Maghrib):** USA 17:00–21:00 o 00:00–02:00 · Almania / France / Italia / Spain 18:00–21:00 · UK 19:00–22:00.

**Kifach tkhtar topic:**
0. **7el onglet 💡 Ideas** – howa l'awel: kay3tik chno tsowr daba.
1. **🚨 Breaking / ⚡ Just in / 🔥 Hot jdid** → video sghira (Short/TikTok) **f 2–6 s3at**. L'awel kayrba7. Chouf "Check YouTube / TikTok": ila kayn deja bzaf, khod angle akhor.
2. **Trend li kay3awd** (dashboard → sort "Repeats most", "seen in X hours · Y days") → video twila / explainer: had chi mazal ghadi y3ich.
3. **Trend f 2+ bldan** (US + DE) → video wa7da b 2 lughat (EN + DE).
4. **Events (Upcoming)** → wjjed **9bel b 3–7 ayam** (trend kaybda 9bel nhar).
5. Dima **verify**: ila khbar dyal mout / jarima / 7arb → 9ol ghir li 2 sources tiqa 9alouh.

**Checklist 9bel ma tposti:** 2 sources? · titre fih smiya dyal trend · hashtags (f "Video ideas") · thumbnail fiha wjeh / smiya · lugha mzyana (EN l USA, DE l Almania).

---

## 7. Events jayin (deja f `events.json` – zid dyalk)

| Date | Event |
|---|---|
| 10 Nov | GTA VI pre-load (PS5 / Xbox) |
| 11 Nov | Karneval 11.11 (DE) + Veterans Day (US) |
| 14 Nov | Protests "Gen Z regelt!" (DE) |
| **19 Nov** | **GTA VI release** |
| 20 Nov | Hunger Games: Sunrise on the Reaping |
| 26 Nov | Thanksgiving (US) · Narnia (IMAX, ~) |
| 27 Nov | Black Friday · Weihnachtsmärkte (DE) |
| 29 Nov | 1. Advent |
| 30 Nov | Cyber Monday |
| ~2 Dec | Spotify Wrapped |
| 10 Dec | The Game Awards |
| **18 Dec** | **Avengers: Doomsday + Dune: Part Three ("Dunesday")** – rumeur: Marvel y9der yzid ychi date |
| 24–31 Dec | Christmas / Silvester |
| ~14 Feb 2027 | Super Bowl LXI |

(~ = date ma mta2kdach 100%, verify 9bel.)

---

## 8. Bdel l'réglages (`config.json` – 7ello b Notepad)

* `focus_countries` – bldan dyal l'public dyalk (daba: US, DE, GB, FR, IT, ES).
* `just_in_outlets` – ch7al mn site f sa3a bach ykoun "⚡ JUST IN" (daba 4).
* `repeat_notify_days` – f ina nhar ywslek "🔁 STILL TRENDING" (daba 2, 3, 5, 7).
* `watchlist` – zid ay kelma: `"tesla"`, `"bundesliga"`, `"kanye"`...
* `watch_teams` – teams dyalk (smiya kamla b7al f onglet Sports).
* `hot_score` / `trend_score` – kber r9m = notifications 9lal; sghar = ktar.
* `max_toasts_per_run` – ch7al mn notification f kol check (lba9i kayji f "+X more").
* `quiet_hours` – mtalan `[1, 8]` = mn 1 l 8 sbah ghir HOT o BREAKING.
* `check_every_minutes` – mn ba3d ma tbdlo, 3awd `INSTALL.cmd`.
* `youtube_api_key` – (ikhtiyari) key mjjani dyal YouTube Data API → YouTube trending US + DE.
* `extra_feeds` – zid ay RSS (mtalan RSS dyal **Talkwalker Alerts**).

Events: `events.json` → zid `{"date": "2026-12-05", "title": "...", "region": "US", "category": "Music"}`.

---

## 9. Fichiers

| Fichier | Dor dyalo |
|---|---|
| `trend_radar.py` | l'programme (Python, bla ta library) |
| `config.json` | réglages |
| `events.json` | calendar |
| `dashboard_template.html` → `dashboard.html` | dashboard |
| `INSTALL.cmd` / `UNINSTALL.cmd` | installer / 7iyed |
| `data/log.txt` | chno dar f kol check (ila chi mochkil) |

**Commands mfidin** (f had dossier):

```bash
python trend_radar.py --report
```
(check bla notifications + ranking f l'écran)

```bash
python trend_radar.py --test
```
(notification test f PC + telephone)

---

## 10. Mochkil?

* **Ma jatnich notification f PC**: Settings → System → Notifications → khass "Trend Radar" ykoun On, o "Focus assist" ykoun Off.
* **Ma jatnich f telephone**: chof wach topic f ntfy hwa nafso li f `config.local.json`. Dir `python trend_radar.py --test`. O chof wach cloud khdam: GitHub → repo `trend-radar` → onglet **Actions**.
* **Bghit n7bes kolchi**: double-click `UNINSTALL.cmd`.
* **PC tafi = ma kayn notifications f wa9tha**, walakin mlli tch3lo kayjik résumé "While you were away". Ila bghiti 24/24 f wa9tha khass VPS / serveur (n9dro ndirouh mn ba3d).

---

## 11. Men l'document dyal Manus – chno dkhel o chno la

**Dkhel:** GDELT · Google News RSS (sections + recherches) · RSS rasmiyin (NPR, NYT, BBC, DW, ZDF, Euronews, Politico...) · ntfy (telephone) · Telegram/Discord (ikhtiyari) · YouTube Data API (ikhtiyari) · Talkwalker (b RSS f `extra_feeds`) · clustering / dedup · score explainable · alerts b cooldown · breaking "verification pending" · digest kol 3 s3at · categories · history · dashboard local · dry-run (`--report`).

**Ma dkhelch (daba):** Event Registry (khlass / quota) · résumé b AI (khass API key o kayswa flous) – f blasto kayn "Video ideas" b templates bla ma ykhtar3 facts. Ila bghiti résumé AI b Claude mn ba3d, n9dro nzidouh.
