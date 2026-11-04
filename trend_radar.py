#!/usr/bin/env python3
"""
Trend Radar - watches trends, breaking news, sports, music, movies, tech and stocks
for the USA, Germany and Europe, and sends notifications (Windows + phone via ntfy).
Standard library only (no pip install needed).

Usage:
  pythonw trend_radar.py            one check (what the scheduled task runs)
  python  trend_radar.py --report   one check, no notifications, print the ranking
  python  trend_radar.py --open     one check, then open the dashboard
  python  trend_radar.py --show     open the dashboard only
  python  trend_radar.py --test     send a test notification (PC + phone)
"""
import argparse
import base64
import hashlib
import html
import json
import math
import os
import re
import struct
import subprocess
import sys
import time
import traceback
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
IMG = DATA / "img"
STATE_FILE = DATA / "state.json"
LOG_FILE = DATA / "log.txt"
LOCK_FILE = DATA / "run.lock"
DASHBOARD = ROOT / "dashboard.html"
APP_ID = "TrendRadar.Notifier"
PROTO = "trendradar"
DASH_LINK = f"{PROTO}://dashboard"
POWERSHELL = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
NO_WINDOW = 0x08000000
CLOUD = os.environ.get("TRENDRADAR_CLOUD") == "1"   # running on GitHub Actions (24/7, phone only)
IS_WIN = os.name == "nt"
LATEST_FILE = DATA / "latest.json"                  # compact data for the Claude briefing

FOCUS = ("US", "DE", "GB", "FR", "IT", "ES")   # replaced by config "focus_countries" at each check
DACH = ("DE", "AT", "CH")
NEWS_EDITION = {  # Google News search links in the audience's language
    "US": ("hl=en-US&gl=US&ceid=US:en", "US"), "GB": ("hl=en-GB&gl=GB&ceid=GB:en", "GB"),
    "DE": ("hl=de&gl=DE&ceid=DE:de", "DE"), "AT": ("hl=de&gl=AT&ceid=AT:de", "AT"), "CH": ("hl=de&gl=CH&ceid=CH:de", "CH"),
    "FR": ("hl=fr&gl=FR&ceid=FR:fr", "FR"), "IT": ("hl=it&gl=IT&ceid=IT:it", "IT"), "ES": ("hl=es&gl=ES&ceid=ES:es", "ES"),
}
COUNTRY_NAMES = {"US": "USA", "DE": "Germany", "AT": "Austria", "CH": "Switzerland", "GB": "UK", "EU": "Europe",
                 "FR": "France", "IT": "Italy", "ES": "Spain", "NL": "Netherlands"}
HEAD_KINDS = ("news", "community", "youtube")
TOP_FEEDS = ("Tagesschau", "ZDFheute", "BBC UK", "franceinfo", "ANSA", "RTVE")
TRUSTED = ("Google News", "Tagesschau", "ZDFheute", "DW Deutsch", "NPR", "NYT", "CBS News", "BBC World",
           "BBC Europe", "BBC UK", "Euronews", "SPIEGEL", "The Guardian", "Sky News", "France24", "Le Monde",
           "franceinfo", "ANSA", "Corriere", "Repubblica", "El País", "RTVE")
SECTION_CAT = {"SPORTS": "Sports", "ENTERTAINMENT": "Movies & TV", "TECHNOLOGY": "Tech & AI", "BUSINESS": "Business"}
BREAKING_RE = re.compile(r"\b(breaking|eilmeldung|just in|eil\b)", re.I)
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc?query={q}&mode=timelinevolraw&format=json&timespan=1d"

STOP = set("""
a an the and or of in on at to for from by with is are was were be been it its this that these those as vs v
not no yes you your we our he she his her they them their who what when where why how will can new
der die das den dem des ein eine einer eines und oder im in am an auf zu zum zur fur mit von vom bei ist
sind war wird werden nach uber unter aus wie was wer nicht auch noch nur sich bis gegen neue neuer neues
live news today heute update updates result results ergebnis ergebnisse game spiel score highlights stream
watch video time date how why says said after before first last year years day days week jahr tag
united states state county city world national international president film series season episode list
open close free best top big small good bad home online official
pour dans avec sont cette plus nous elle selon apres avant mais etre tout tous direct actualite info infos
della delle nella dello degli anche dopo sono ancora oggi diretta notizie ultime ultima cosa come
sobre para como pero tras desde contra entre hoy directo vivo noticias ultimas ultima este esta
2023 2024 2025 2026 2027 2028
""".split())

WEEKDAY_FLUFF = re.compile(
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|montag|dienstag|mittwoch|donnerstag|"
    r"freitag|samstag|sonntag|weekend|wochenende)\b.*\b(good|happy|motivation|vibes|mood|guten|schonen|"
    r"feeling|blessed)\b|\b(good|happy|guten|schonen)\b.*\b(monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|morning|night|montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|morgen)\b")

WIKI_SKIP = re.compile(
    r"^(Main_Page|Special:|Spezial:|Wikipedia:|File:|Datei:|Portal:|Help:|Hilfe:|Category:|Kategorie:|"
    r"User:|Benutzer:|Template:|Vorlage:|Talk:|Diskussion:|Deaths_in_|Nekrolog|List_of_|Liste_|-$|"
    r"Cleopatra$|XXX|Pornhub|xHamster|Bible$|YouTube$|Google$|Facebook$|ChatGPT$|Undefined$|"
    r"Search$|Wiki$|Microsoft_Office$|Wikipedia$|\d{1,2}\._[A-Z]\w+$|"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)_\d{1,2}$|"
    r"\d{4}$|\d{4}_in_)", re.I)

ACRONYMS = {"gta", "nba", "nfl", "mlb", "nhl", "ufc", "wwe", "usa", "uk", "eu", "afd", "cdu", "csu", "spd",
            "fdp", "bsw", "fbi", "cia", "ice", "ai", "tv", "psg", "bvb", "dfb", "ard", "zdf", "nasa", "ps5", "gop"}

TICKERS = {
    "TSLA": "Tesla", "AAPL": "Apple", "NVDA": "Nvidia", "AMD": "AMD", "MSFT": "Microsoft", "GOOGL": "Google",
    "GOOG": "Google", "AMZN": "Amazon", "META": "Meta", "NFLX": "Netflix", "PLTR": "Palantir", "GME": "GameStop",
    "AMC": "AMC", "COIN": "Coinbase", "MSTR": "Strategy (MicroStrategy)", "BTC-USD": "Bitcoin", "ETH-USD": "Ethereum",
    "DOGE-USD": "Dogecoin", "INTC": "Intel", "BA": "Boeing", "DIS": "Disney", "RDDT": "Reddit", "HOOD": "Robinhood",
    "SMCI": "Super Micro", "AVGO": "Broadcom", "ORCL": "Oracle", "UBER": "Uber", "ABNB": "Airbnb", "NKE": "Nike",
    "WMT": "Walmart", "TGT": "Target", "PFE": "Pfizer", "LLY": "Eli Lilly", "NVO": "Novo Nordisk", "SNAP": "Snapchat",
    "RIVN": "Rivian", "LCID": "Lucid", "NIO": "NIO", "BABA": "Alibaba", "TSM": "TSMC", "ARM": "Arm", "MU": "Micron",
    "SBUX": "Starbucks", "MCD": "McDonald's", "KO": "Coca-Cola", "PEP": "PepsiCo", "SPOT": "Spotify", "SONY": "Sony",
    "TTWO": "Take-Two (GTA)", "EA": "Electronic Arts", "RBLX": "Roblox", "UNH": "UnitedHealth", "JPM": "JPMorgan",
    "SAP": "SAP", "VWAGY": "Volkswagen", "BMWYY": "BMW", "MBGYY": "Mercedes-Benz", "SIEGY": "Siemens", "CRWD": "CrowdStrike",
    "ANET": "Arista", "FSLR": "First Solar", "ENPH": "Enphase", "SPCX": "SpaceX", "OPAI": "OpenAI", "CRCL": "Circle",
}

CATEGORIES = {
    "Politics": "election midterm senate congress governor white house trump biden harris vance obama democrat republican gop vote ballot wahl bundestag kanzler merz scholz afd cdu spd grune fdp minister parlament parliament koalition steinmeier election elezioni elecciones gouvernement governo gobierno macron meloni sanchez starmer ministre ministro premier",
    "World & conflicts": "war krieg ukraine russia russland israel gaza iran china putin selenskyj zelensky military militar army missile rakete nato sanction guerre guerra",
    "Natural disasters": "earthquake quake tsunami hurricane typhoon cyclone tornado flood flooding wildfire bushfire volcano eruption landslide mudslide avalanche blizzard heatwave drought storm tropical "
                         "erdbeben beben hochwasser uberschwemmung unwetter sturm orkan waldbrand vulkan lawine hitzewelle durre "
                         "seisme tremblement inondation tempete ouragan canicule secheresse eruption "
                         "terremoto sisma alluvione inondazione frana tromba uragano siccita "
                         "sismo huracan inundacion dana borrasca riada incendio forestal",
    "Crime & accidents": "shooting shot killed dead death murder crash explosion attack anschlag unfall tote mord brand police polizei arrest festnahme cyberangriff hackerangriff accident incidente attentat attentato morto muerto meurtre omicidio asesinato polizia policia derailment entgleisung",
    "Sports": "nfl nba mlb nhl ufc wwe mls super bowl touchdown quarterback playoff bundesliga champions league premier league fussball football soccer goal coach trainer transfer olympic tennis formel f1 grand prix boxing boxen spieltag bayern dortmund calcio futbol ligue serie liga partita partido gol juventus milan inter napoli madrid barcelona psg",
    "Tech & AI": "ai ki ia openai chatgpt gemini anthropic claude apple iphone ipad microsoft nvidia tesla spacex musk meta tiktok instagram app software robot chip smartphone samsung google android",
    "Business": "stock market dow nasdaq aktie borse dax earning ipo economy wirtschaft inflation fed zinsen price preis tariff zoll bitcoin crypto bank layoff bourse borsa bolsa economie economia",
    "Movies & TV": "movie film trailer box office netflix disney marvel avenger serie kino oscar emmy actor actress schauspieler hbo streaming star wars cinema pelicula acteur attore actor",
    "Music": "song album tour concert konzert singer sanger rapper grammy chart music musik spotify billboard chanson canzone cancion concerto concierto sanremo eurovision",
    "Gaming": "gta playstation ps5 xbox nintendo game award fortnite minecraft steam gaming videogame rockstar",
    "Celebs & viral": "celebrity promi dating wedding hochzeit baby divorce scheidung viral meme influencer royal prince harry meghan kardashian mariage matrimonio boda",
    "AI video & image": "seedance kling veo sora hailuo minimax luma pika midjourney flux seedream ideogram krea "
                        "higgsfield comfyui ltx hunyuanvideo hunyuan lora diffusion deepfake elevenlabs suno udio "
                        "ai video ai image video generator image generator text-to-video image-to-video nano banana stable diffusion wan 2",
}

# --------------------------------------------------------------------------- utils


def log(msg):
    DATA.mkdir(exist_ok=True)
    line = f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > 1_000_000:
            LOG_FILE.write_text(LOG_FILE.read_text(encoding="utf-8")[-200_000:], encoding="utf-8")
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass
    if sys.stdout:
        try:
            print(line)
        except Exception:  # noqa: BLE001
            pass


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(path, obj):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def fetch(url, timeout=20, ua=None):
    req = urllib.request.Request(url, headers={"User-Agent": ua or UA, "Accept-Language": "en-US,en;q=0.9,de;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def fetch_json(url, timeout=20, ua=None):
    return json.loads(fetch(url, timeout, ua))


def post_json(url, body, timeout=15):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json", "User-Agent": "TrendRadar/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def split_hashtag(s):
    if s.startswith("#"):
        s = s[1:]
        s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", s)
        s = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", s)
    return s


def norm(s):
    s = split_hashtag((s or "").strip())
    s = re.sub(r"\s*\([^)]*\)", "", s)           # drop "(politician)", "(2026 film)"
    s = unicodedata.normalize("NFKD", s.casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("&", " and ").replace("_", " ")
    s = re.sub(r"[^\w\s]", " ", s)
    # light stemming so "midterms" == "midterm", "democrats" == "democrat"
    return " ".join(t[:-1] if len(t) > 4 and t.endswith("s") and not t.endswith("ss") else t for t in s.split())


STOP |= {norm(w) for w in STOP}   # so stemmed / accent-free tokens match too


def distinctive(tok):
    return len(tok) >= 4 and not tok.isdigit() and tok not in STOP


def smart_title(s):
    s = s.replace("_", " ")
    s = re.sub(r"\s*\([^)]*\)", "", s).strip()
    if any(c.isupper() for c in s):
        return s
    return " ".join(w.upper() if w in ACRONYMS else w[:1].upper() + w[1:] for w in s.split())


def parse_traffic(s):
    if not s:
        return 0
    s = s.strip().upper().replace(",", "").replace("+", "")
    mult = 1
    if s.endswith("K"):
        mult, s = 1000, s[:-1]
    elif s.endswith("M"):
        mult, s = 1_000_000, s[:-1]
    try:
        return int(float(s) * mult)
    except ValueError:
        return 0


def fmt_traffic(n):
    if n >= 1_000_000:
        return f"{n / 1_000_000:g}M+"
    if n >= 1000:
        return f"{n / 1000:g}K+"
    return f"{n}+"


def parse_date(s):
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).isoformat()


def hours_since(iso, now):
    if not iso:
        return 9999
    try:
        return (now - datetime.fromisoformat(iso)).total_seconds() / 3600
    except (TypeError, ValueError):
        return 9999


def sid(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def matches_phrase(phrase_toks, text_toks):
    return bool(phrase_toks) and set(phrase_toks) <= text_toks


CAT_PHRASES = {
    "Politics": ["white house"], "Sports": ["super bowl", "champions league", "premier league", "grand prix"],
    "Movies & TV": ["box office", "star wars"], "Gaming": ["game award"],
    "AI video & image": ["ai video", "ai image", "video generator", "image generator", "text-to-video", "image-to-video",
                         "nano banana", "stable diffusion", "wan 2", "runway gen", "runway ai", "runway ml", "leonardo ai"],
}


def _cat_index():
    idx = {}
    for cat, words in CATEGORIES.items():
        phrases = CAT_PHRASES.get(cat, [])
        text = words
        for p in phrases:
            text = text.replace(p, " ")
        idx[cat] = ({norm(w) for w in text.split()}, [norm(p) for p in phrases])
    return idx


CAT_INDEX = _cat_index()

# --------------------------------------------------------------------------- sources

HT = "{https://trends.google.com/trending/rss}"
ATOM = "{http://www.w3.org/2005/Atom}"


def src_google_trends(geo):
    root = ET.fromstring(fetch(f"https://trends.google.com/trending/rss?geo={geo}"))
    out = []
    for rank, it in enumerate(root.iter("item"), 1):
        term = (it.findtext("title") or "").strip()
        if not term:
            continue
        news = []
        for n in it.findall(HT + "news_item"):
            news.append({"title": html.unescape(n.findtext(HT + "news_item_title") or ""),
                         "url": n.findtext(HT + "news_item_url") or "",
                         "source": n.findtext(HT + "news_item_source") or ""})
        out.append({"kind": "search", "source": "Google Trends", "country": geo, "term": term,
                    "display": smart_title(term),
                    "traffic": parse_traffic(it.findtext(HT + "approx_traffic")), "rank": rank,
                    "url": f"https://trends.google.com/trending?geo={geo}",
                    "news": news, "picture": it.findtext(HT + "picture") or "",
                    "published": parse_date(it.findtext("pubDate"))})
    return out


def src_x_trends(cc, slug):
    page = fetch(f"https://trends24.in/{slug}/").decode("utf-8", "replace")
    blocks = [b for b in page.split("class=list-container")[1:] if "data-timestamp" in b[:300]]
    if not blocks:
        blocks = page.split("class=list-container")[1:]
    hours = Counter()
    latest = []
    for i, b in enumerate(blocks[:24]):
        names = [html.unescape(m).strip() for m in re.findall(r'class="?trend-link"?[^>]*>([^<]+)</a>', b)]
        for n in set(names):
            hours[n] += 1
        if i == 0:
            latest = names
    return [{"kind": "social", "source": "X", "country": cc, "term": n, "display": n, "rank": rank,
             "hours": hours.get(n, 1), "url": "https://x.com/search?q=" + urllib.parse.quote(n) + "&f=live"}
            for rank, n in enumerate(latest[:30], 1)]


def _rss_items(raw):
    root = ET.fromstring(raw)
    return list(root.iter("item")) or list(root.iter(ATOM + "entry"))


def src_google_news(cc, params, section=None):
    if section:
        url = f"https://news.google.com/rss/headlines/section/topic/{section}?{params}"
    else:
        url = "https://news.google.com/rss?" + params
    out = []
    for rank, it in enumerate(_rss_items(fetch(url)), 1):
        if rank > (15 if section else 30):
            break
        title = html.unescape(it.findtext("title") or "")
        outlet = it.findtext("source") or ""
        if outlet and title.endswith(" - " + outlet):
            title = title[: -len(outlet) - 3]
        desc = it.findtext("description") or ""
        out.append({"kind": "news", "source": "Google News" + (f" {section.title()}" if section else ""),
                    "section": section, "cat": SECTION_CAT.get(section), "country": cc, "term": title,
                    "outlet": outlet, "rank": rank, "coverage": max(1, desc.count("<li>")),
                    "url": it.findtext("link") or "", "published": parse_date(it.findtext("pubDate")),
                    "breaking": bool(BREAKING_RE.search(title))})
    return out


def src_feed(feed):
    out = []
    for rank, it in enumerate(_rss_items(fetch(feed["url"]))[:25], 1):
        title = it.findtext("title") or it.findtext(ATOM + "title") or ""
        link = it.findtext("link") or ""
        if not link:
            le = it.find(ATOM + "link")
            link = le.get("href", "") if le is not None else ""
        pub = (it.findtext("pubDate") or it.findtext(ATOM + "updated") or it.findtext(ATOM + "published")
               or it.findtext("{http://purl.org/dc/elements/1.1/}date"))
        title = html.unescape(title).strip()
        out.append({"kind": feed.get("kind", "news"), "source": feed["name"], "country": feed["country"],
                    "term": title, "outlet": feed["name"], "rank": rank, "url": link.strip(), "cat": feed.get("cat"),
                    "published": parse_date(pub), "breaking": bool(BREAKING_RE.search(title))})
    return out


# --------------------------------------------------------------------------- AI tools (video / image / voice models)

HF_PIPE_LABEL = {"text-to-video": "Text to video", "image-to-video": "Image to video", "text-to-image": "Text to image",
                 "text-to-speech": "Text to speech (voice)"}
VARIANT_RE = re.compile(r"lora|gguf|quant|pruned|fp8|fp16|nf4|int4|int8|bnb|awq|merge|hybrid|-turbo-|distill-lora", re.I)


def watch_terms(cfg):
    """Your watchlist + the AI tools list (tagged with the AI category)."""
    terms = [(t, None) for t in cfg.get("watchlist", [])]
    ac = cfg.get("ai_tools") or {}
    if ac.get("enabled", True):
        terms += [(t, "AI video & image") for t in ac.get("watch", []) if t not in cfg.get("watchlist", [])]
    return terms


def src_hf(pipeline):
    """Models trending on Hugging Face for one task: the newest open (often local) AI models."""
    d = fetch_json(f"https://huggingface.co/api/models?pipeline_tag={pipeline}&sort=trendingScore&direction=-1&limit=15",
                   timeout=25, ua=APP_UA)
    out = []
    for rank, m in enumerate(d, 1):
        mid = m.get("id") or m.get("modelId") or ""
        out.append({"kind": "ai_model", "source": "Hugging Face", "country": "", "term": mid, "id": mid,
                    "author": mid.split("/")[0] if "/" in mid else "", "pipeline": pipeline, "rank": rank,
                    "likes": m.get("likes") or 0, "downloads": m.get("downloads") or 0,
                    "created": parse_date(m.get("createdAt")), "trending": m.get("trendingScore") or 0,
                    "variant": bool(VARIANT_RE.search(mid)), "url": f"https://huggingface.co/{mid}"})
    return out


def ai_alerts(signals, state, cfg, now, quiet):
    """New AI models entering the Hugging Face top of their task -> one alert each (first run: one summary)."""
    ac = cfg.get("ai_tools") or {}
    seen = state.setdefault("ai_models", {})
    models = [s for s in signals if s["kind"] == "ai_model"]
    first_run = not seen
    out, fresh = [], []
    for m in sorted(models, key=lambda m: m["rank"]):
        key = m["id"]
        is_new = key not in seen
        seen.setdefault(key, now.isoformat())
        young = hours_since(m.get("created"), now) <= 24 * ac.get("new_model_days", 60)
        if not is_new or m["variant"] or m["rank"] > ac.get("top_n", 5) or not young or m["likes"] < ac.get("min_likes", 30):
            continue
        fresh.append(m)
    if not ac.get("notify_new_models", True) or quiet:
        fresh = []
    if first_run and fresh:
        names = ", ".join(f"{m['id'].split('/')[-1]} ({HF_PIPE_LABEL.get(m['pipeline'], m['pipeline'])})" for m in fresh[:6])
        out.append(mk_alert("\U0001F3AC AI models trending now", names[:200], "Open models - most run locally (see the AI tools tab)",
                            "https://huggingface.co/models?sort=trending", tag="aiinit", priority=3, short="AI models",
                            kind="ai", category="AI video & image", label="AI MODEL",
                            push_text="\n".join(f"\U0001F539 {m['id']} - {HF_PIPE_LABEL.get(m['pipeline'], m['pipeline'])}, "
                                                f"❤ {m['likes']}" for m in fresh[:8])))
    elif not first_run:
        for m in fresh[:3]:
            video = m["pipeline"] in ("text-to-video", "image-to-video")
            lines = [f"\U0001F525 #{m['rank']} trending on Hugging Face · {HF_PIPE_LABEL.get(m['pipeline'], m['pipeline'])}",
                     f"❤ {m['likes']} likes · ⬇ {m['downloads']:,} downloads · created {(m.get('created') or '')[:10]}",
                     "\U0001F4BB Open model - can run on your own PC (check the model card for GPU memory)"]
            out.append(mk_alert(f"\U0001F3AC NEW AI MODEL: {m['id']}", lines[0], lines[1], m["url"], tag="ai" + sid(m["id"]),
                                priority=4 if video else 3, short=m["id"], kind="ai", category="AI video & image",
                                label="AI MODEL", push_text="\n".join(lines)))
    for k in [k for k, v in seen.items() if hours_since(v, now) > 120 * 24]:
        del seen[k]
    data = {}
    for m in models:
        data.setdefault(m["pipeline"], []).append({
            "id": m["id"], "author": m["author"], "likes": m["likes"], "downloads": m["downloads"], "created": m.get("created"),
            "u": m["url"], "rank": m["rank"], "variant": m["variant"]})
    for v in data.values():
        v.sort(key=lambda x: x["rank"])
    return out, data


def src_wikipedia(lang, cc):
    data = None
    for back in (1, 2):
        d = datetime.now(timezone.utc) - timedelta(days=back)
        url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/{lang}.wikipedia/all-access/{d:%Y/%m/%d}"
        try:
            data = fetch_json(url)
            break
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
    if not data:
        return []
    out = []
    for a in data["items"][0]["articles"]:
        t = a["article"]
        if WIKI_SKIP.search(t) or ":" in t:
            continue
        out.append({"kind": "wiki", "source": f"Wikipedia {lang}", "country": cc, "term": t,
                    "display": smart_title(t), "views": a["views"], "rank": len(out) + 1,
                    "url": f"https://{lang}.wikipedia.org/wiki/{urllib.parse.quote(t)}"})
        if len(out) >= 25:
            break
    return out


def src_watch(term, edition, params):
    q = f'"{term}" when:1d' if " " in term else f"{term} when:1d"
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q)}&{params}"
    out = []
    for rank, it in enumerate(_rss_items(fetch(url))[:40], 1):
        title = html.unescape(it.findtext("title") or "")
        outlet = it.findtext("source") or ""
        if outlet and title.endswith(" - " + outlet):
            title = title[: -len(outlet) - 3]
        out.append({"kind": "watch", "watch_term": term, "source": "Google News search", "country": edition,
                    "term": title, "outlet": outlet, "rank": rank, "url": it.findtext("link") or "",
                    "published": parse_date(it.findtext("pubDate"))})
    return out


def src_espn(path, label, cc, day=None):
    d = fetch_json(f"https://site.api.espn.com/apis/site/v2/sports/{path}/scoreboard" + (f"?dates={day}" if day else ""))
    out = []
    for e in d.get("events", []):
        comp = (e.get("competitions") or [{}])[0]
        st = (e.get("status") or {}).get("type") or {}
        teams = []
        for x in comp.get("competitors", []):
            tm = x.get("team") or x.get("athlete") or {}
            teams.append({"name": tm.get("displayName") or tm.get("fullName") or "",
                          "short": tm.get("abbreviation") or tm.get("shortDisplayName") or "",
                          "score": x.get("score"), "home": x.get("homeAway") == "home", "winner": x.get("winner"),
                          "rank": (x.get("curatedRank") or {}).get("current")})
        teams.sort(key=lambda t: not t["home"])
        out.append({"kind": "sport", "source": "ESPN", "country": cc, "league": label, "id": str(e.get("id")),
                    "term": e.get("name") or "", "short": e.get("shortName") or "", "date": e.get("date"),
                    "state": st.get("state"), "detail": st.get("shortDetail") or st.get("detail") or "",
                    "season_type": (e.get("season") or {}).get("type"),
                    "notes": [n.get("headline") for n in comp.get("notes", []) if n.get("headline")],
                    "teams": teams, "url": ((e.get("links") or [{}])[0]).get("href", "")})
    return out


def src_apple_music(cc):
    d = fetch_json(f"https://rss.marketingtools.apple.com/api/v2/{cc.lower()}/music/most-played/25/songs.json", timeout=30)
    out = []
    for rank, r in enumerate(d["feed"]["results"], 1):
        artist = r.get("artistName", "")
        main = re.split(r",| & | feat\.? | ft\.? | x | und ", artist, flags=re.I)[0].strip()
        out.append({"kind": "music", "source": "Apple Music", "country": cc, "term": main, "display": main,
                    "rank": rank, "song": r.get("name", ""), "artist": artist, "url": r.get("url", ""),
                    "art": r.get("artworkUrl100", ""), "id": str(r.get("id")), "cat": "Music"})
    return out


def src_yahoo():
    d = fetch_json("https://query1.finance.yahoo.com/v1/finance/trending/US?count=20")
    out = []
    for rank, q in enumerate(d["finance"]["result"][0]["quotes"], 1):
        s = q["symbol"]
        name = TICKERS.get(s)
        out.append({"kind": "finance", "source": "Yahoo Finance", "country": "US", "term": name or s,
                    "display": name or s, "symbol": s, "known": bool(name), "rank": rank, "cat": "Business",
                    "url": f"https://finance.yahoo.com/quote/{urllib.parse.quote(s)}"})
    return out


def src_hn():
    d = fetch_json("https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30")
    return [{"kind": "community", "source": "Hacker News", "country": "US", "term": h.get("title") or "",
             "outlet": "Hacker News", "rank": rank, "points": h.get("points") or 0, "cat": "Tech & AI",
             "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
             "published": parse_date(h.get("created_at"))} for rank, h in enumerate(d.get("hits", []), 1)]


def src_itunes_movies():
    d = fetch_json("https://itunes.apple.com/us/rss/topmovies/limit=15/json")
    out = []
    for rank, e in enumerate(d.get("feed", {}).get("entry", []), 1):
        link = e.get("link")
        if isinstance(link, list):
            link = link[0] if link else {}
        imgs = e.get("im:image") or [{}]
        out.append({"kind": "movie_chart", "source": "iTunes", "country": "US", "term": e["im:name"]["label"],
                    "rank": rank, "url": (link or {}).get("attributes", {}).get("href", ""),
                    "art": imgs[-1].get("label", ""), "genre": e.get("category", {}).get("attributes", {}).get("label", "")})
    return out


def src_youtube(cc, key):
    d = fetch_json("https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&chart=mostPopular"
                   f"&regionCode={cc}&maxResults=25&key={urllib.parse.quote(key)}")
    out = []
    for rank, v in enumerate(d.get("items", []), 1):
        sn = v.get("snippet", {})
        out.append({"kind": "youtube", "source": "YouTube", "country": cc, "term": sn.get("title", ""),
                    "outlet": sn.get("channelTitle", ""), "rank": rank,
                    "views": int((v.get("statistics") or {}).get("viewCount", 0)),
                    "url": f"https://www.youtube.com/watch?v={v.get('id')}",
                    "art": ((sn.get("thumbnails") or {}).get("medium") or {}).get("url", "")})
    return out


# --------------------------------------------------------------------------- natural disasters

APP_UA = "TrendRadar/1.0 (personal trend monitor)"   # weather.gov asks for an app name
US_ABBR = ("AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK "
           "OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR").split()
US_WORDS = ("alaska", "hawaii", "puerto rico", "california", "nevada", "oklahoma", "texas", "washington", "oregon", "idaho",
            "montana", "utah", "wyoming", "arkansas", "tennessee", "missouri", "new mexico", "arizona", "colorado")
COUNTRY_BY_NAME = {"united states": "US", "usa": "US", "germany": "DE", "united kingdom": "GB", "uk": "GB", "england": "GB",
                   "scotland": "GB", "wales": "GB", "france": "FR", "italy": "IT", "sicily": "IT", "spain": "ES",
                   "canary islands": "ES", "austria": "AT", "switzerland": "CH"}
EUROPE_WORDS = ("greece", "turkey", "portugal", "iceland", "croatia", "albania", "romania", "bulgaria", "serbia", "bosnia",
                "montenegro", "slovenia", "ireland", "norway", "sweden", "finland", "poland", "czech", "slovakia", "hungary",
                "cyprus", "malta", "crete", "aegean", "adriatic", "ionian", "tyrrhenian", "balkan", "dodecanese",
                "macedonia", "netherlands", "belgium", "denmark", "azores", "europe", "mediterranean")
GDACS_TYPES = {"EQ": "earthquake", "TC": "cyclone", "FL": "flood", "VO": "volcano", "DR": "drought", "WF": "wildfire",
               "TS": "tsunami"}
DIS_ICON = {"earthquake": "\U0001F30D", "cyclone": "\U0001F300", "flood": "\U0001F30A", "volcano": "\U0001F30B",
            "drought": "☀️", "wildfire": "\U0001F525", "tsunami": "\U0001F30A", "storm": "\U0001F32A️",
            "us_weather": "⚠️"}
NWS_EVENTS = ("Tornado Warning", "Tornado Emergency", "Hurricane Warning", "Tropical Storm Warning", "Storm Surge Warning",
              "Tsunami Warning", "Blizzard Warning", "Ice Storm Warning", "Extreme Heat Warning", "Excessive Heat Warning",
              "Flash Flood Emergency", "Extreme Wind Warning", "Earthquake Warning", "Volcano Warning", "Dust Storm Warning")


def place_country(place):
    """'91 km ESE of Kyzyl-Eshme, Kyrgyzstan' -> '' ; '10 km SW of Ridgecrest, CA' -> 'US' ; 'SICILY, ITALY' -> 'IT'."""
    p = (place or "").strip()
    low = p.lower()
    m = re.search(r",\s*([A-Z]{2})$", p)
    if (m and m.group(1) in US_ABBR) or any(w in low for w in US_WORDS):
        return "US"
    for name, cc in COUNTRY_BY_NAME.items():
        if re.search(rf"\b{name}\b", low):
            return cc
    return "EU" if any(w in low for w in EUROPE_WORDS) else ""


def src_usgs():
    d = fetch_json("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson", ua=APP_UA)
    out = []
    for f in d.get("features", []):
        p = f.get("properties") or {}
        c = (f.get("geometry") or {}).get("coordinates") or []
        if not p.get("time"):
            continue
        out.append({"kind": "disaster", "dtype": "earthquake", "source": "USGS", "id": f.get("id"), "mag": p.get("mag") or 0,
                    "term": p.get("place") or p.get("title") or "", "time": datetime.fromtimestamp(p["time"] / 1000, timezone.utc).isoformat(),
                    "alert": p.get("alert"), "tsunami": bool(p.get("tsunami")), "felt": p.get("felt"),
                    "depth": round(c[2]) if len(c) > 2 and c[2] is not None else None, "url": p.get("url") or "",
                    "country": place_country(p.get("place"))})
    return out


def src_emsc():
    """European-Mediterranean quakes (often in Italian / Greek / Turkish news even when small)."""
    d = fetch_json("https://www.seismicportal.eu/fdsnws/event/1/query?limit=50&minmag=4&format=json", ua=APP_UA)
    out = []
    for f in d.get("features", []):
        p = f.get("properties") or {}
        place = (p.get("flynn_region") or "").title()
        cc = place_country(place)
        if cc not in ("IT", "ES", "FR", "DE", "GB", "AT", "CH", "EU") or not p.get("time"):
            continue
        unid = p.get("unid") or f.get("id")
        out.append({"kind": "disaster", "dtype": "earthquake", "source": "EMSC", "id": f"emsc{unid}", "mag": p.get("mag") or 0,
                    "term": place, "time": parse_date(p["time"]), "alert": None, "tsunami": False, "felt": None,
                    "depth": round(p["depth"]) if p.get("depth") is not None else None,
                    "url": f"https://www.seismicportal.eu/eventdetails.html?unid={unid}", "country": cc})
    return out


def src_gdacs():
    root = ET.fromstring(fetch("https://www.gdacs.org/xml/rss.xml", timeout=30, ua=APP_UA))
    G = "{http://www.gdacs.org}"
    out = []
    for it in root.iter("item"):
        if (it.findtext(G + "iscurrent") or "").lower() != "true":
            continue
        country = it.findtext(G + "country") or ""
        etype = it.findtext(G + "eventtype") or ""
        out.append({"kind": "disaster", "dtype": GDACS_TYPES.get(etype, etype.lower()), "source": "GDACS",
                    "id": f"{etype}{it.findtext(G + 'eventid')}", "level": it.findtext(G + "alertlevel") or "",
                    "term": html.unescape(it.findtext("title") or ""), "place": country,
                    "time": parse_date(it.findtext("pubDate")), "url": it.findtext("link") or "",
                    "severity": html.unescape(it.findtext(G + "severity") or ""),
                    "country": place_country(country) if country else ""})
    return out


def src_nws():
    d = fetch_json("https://api.weather.gov/alerts/active?status=actual&severity=Extreme,Severe", timeout=30, ua=APP_UA)
    out = []
    for f in d.get("features", []):
        p = f.get("properties") or {}
        ev = p.get("event") or ""
        if p.get("severity") != "Extreme" and ev not in NWS_EVENTS:
            continue
        states = sorted({s.strip()[-2:] for s in (p.get("areaDesc") or "").split(";") if "," in s})
        out.append({"kind": "disaster", "dtype": "us_weather", "source": "NWS", "id": p.get("id") or f.get("id"),
                    "event": ev, "severity": p.get("severity"), "term": p.get("headline") or ev,
                    "area": p.get("areaDesc") or "", "states": states, "time": parse_date(p.get("sent")),
                    "url": "https://alerts.weather.gov/", "country": "US"})
    return out


def src_eonet():
    d = fetch_json("https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=40&days=3", timeout=30, ua=APP_UA)
    kinds = {"Wildfires": "wildfire", "Severe Storms": "storm", "Volcanoes": "volcano", "Floods": "flood",
             "Earthquakes": "earthquake", "Landslides": "flood", "Sea and Lake Ice": "", "Snow": "storm"}
    out = []
    for e in d.get("events", []):
        cat = (e.get("categories") or [{}])[0].get("title", "")
        if not kinds.get(cat):
            continue
        geo = e.get("geometry") or [{}]
        src = (e.get("sources") or [{}])[0].get("url") or e.get("link", "")
        out.append({"kind": "disaster", "dtype": kinds[cat], "source": "NASA EONET", "id": e.get("id"),
                    "term": e.get("title", ""), "time": parse_date(geo[-1].get("date")), "url": src, "country": ""})
    return out


def disaster_alerts(signals, state, cfg, now, quiet):
    """Earthquakes, cyclones, floods, wildfires, volcanoes, US weather warnings -> alerts + dashboard data."""
    dc = {"quake_world_mag": 6.0, "quake_europe_mag": 5.0, "quake_country_mag": 4.5, "gdacs_levels": ["Orange", "Red"]}
    dc.update(cfg.get("disasters") or {})
    seen = state.setdefault("disasters", {})
    dis = [s for s in signals if s["kind"] == "disaster"]
    out = []
    focus = set(FOCUS) | {"AT", "CH"}

    # earthquakes (USGS + EMSC, without doubles)
    quakes = []
    for q in sorted((s for s in dis if s["source"] in ("USGS", "EMSC")), key=lambda s: s["source"] != "USGS"):
        if any(abs(hours_since(q["time"], datetime.fromisoformat(o["time"])) or 0) < 0.03 and abs(q["mag"] - o["mag"]) < 0.4
               for o in quakes if q.get("time") and o.get("time")):
            continue
        quakes.append(q)
    for q in quakes:
        age = hours_since(q["time"], now)
        cc = q["country"]
        big = (q["mag"] >= dc["quake_world_mag"] or (cc in focus and q["mag"] >= dc["quake_country_mag"])
               or (cc == "EU" and q["mag"] >= dc["quake_europe_mag"]) or q["alert"] in ("yellow", "orange", "red") or q["tsunami"])
        q["big"] = bool(big)
        key = "eq:" + str(q["id"])
        if not big or age > 12 or key in seen:
            continue
        seen[key] = now.isoformat()
        pr = 5 if (q["mag"] >= 7 or q["tsunami"] or q["alert"] in ("orange", "red")) else 4 if (q["mag"] >= 6 or cc in focus) else 3
        if quiet and pr < 4:
            continue
        lines = [f"\U0001F552 {fmt_age(age)} ago" + (f" · depth {q['depth']} km" if q.get("depth") is not None else "") + f" · {q['source']}"]
        if q["tsunami"]:
            lines.append("\U0001F30A Tsunami flag - check official warnings")
        if q["alert"]:
            lines.append(f"\U0001F6A6 Impact alert (PAGER): {q['alert']}")
        if q.get("felt"):
            lines.append(f"\U0001F465 {q['felt']} people reported feeling it")
        out.append(mk_alert(f"\U0001F30D EARTHQUAKE M{q['mag']:.1f} · {q['term']}", lines[0], " · ".join(lines[1:]), q["url"],
                            tag="eq" + sid(key), priority=pr, short=f"M{q['mag']:.1f} {q['term']}", kind="disaster",
                            countries=[cc] if cc else [], category="Natural disasters", push_text="\n".join(lines),
                            long=pr >= 4))
    # GDACS orange / red (UN global disaster alerts)
    for g in (s for s in dis if s["source"] == "GDACS"):
        key = f"gd:{g['id']}:{g['level']}"
        if g["level"] not in dc["gdacs_levels"] or key in seen:
            continue
        seen[key] = now.isoformat()
        pr = 5 if g["level"] == "Red" else 4
        icon = DIS_ICON.get(g["dtype"], "⚠️")
        lines = [f"\U0001F4CD {g['place'] or 'see map'} · \U0001F552 {fmt_age(hours_since(g['time'], now))} ago"]
        if g.get("severity"):
            lines.append(g["severity"][:160])
        out.append(mk_alert(f"{icon} {g['level'].upper()} ALERT · {g['term']}"[:150], lines[0], " · ".join(lines[1:]), g["url"],
                            tag="gd" + sid(key), priority=pr, short=g["term"][:60], kind="disaster",
                            countries=[g["country"]] if g["country"] else [], category="Natural disasters",
                            push_text="\n".join(lines), long=True))
    # US weather warnings, one alert per type (e.g. "Tornado Warning x5 · OK, KS")
    groups = {}
    for w in (s for s in dis if s["source"] == "NWS"):
        groups.setdefault(w["event"], []).append(w)
    nws_summary = []
    for ev, ws in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        states = sorted({s for w in ws for s in w["states"]})
        nws_summary.append({"event": ev, "n": len(ws), "states": states, "extreme": any(w["severity"] == "Extreme" for w in ws),
                            "headline": ws[0]["term"]})
        key = f"nws:{ev}"
        last = seen.get(key)
        prev_n = seen.get(key + ":n", 0)
        if last and hours_since(last, now) < 6 and len(ws) < 2 * max(1, prev_n):
            continue
        seen[key] = now.isoformat()
        seen[key + ":n"] = len(ws)
        pr = 5 if ("Emergency" in ev or any(w["severity"] == "Extreme" for w in ws)) else 4
        where = ", ".join(states[:8]) + (f" +{len(states) - 8}" if len(states) > 8 else "")
        out.append(mk_alert(f"⚠️ USA: {ev}" + (f" x{len(ws)}" if len(ws) > 1 else ""), f"\U0001F4CD {where}",
                            ws[0]["term"][:150], "https://alerts.weather.gov/", tag="nw" + sid(ev), priority=pr,
                            short=f"US {ev}", kind="disaster", countries=["US"], category="Natural disasters",
                            push_text=f"\U0001F4CD {where}\n{ws[0]['term'][:300]}", long=True))
    for k in [k for k, v in seen.items() if not k.endswith(":n") and hours_since(v, now) > 7 * 24]:
        seen.pop(k, None)
        seen.pop(k + ":n", None)
    out.sort(key=lambda a: -a["priority"])
    data = {
        "quakes": [{"mag": q["mag"], "place": q["term"], "time": q["time"], "u": q["url"], "c": q["country"], "big": q.get("big"),
                    "tsunami": q["tsunami"], "alert": q["alert"], "src": q["source"], "depth": q.get("depth")}
                   for q in sorted(quakes, key=lambda q: -q["mag"]) if hours_since(q["time"], now) <= 24][:40],
        "gdacs": [{"level": g["level"], "type": g["dtype"], "t": g["term"], "u": g["url"], "time": g["time"], "c": g["country"]}
                  for g in sorted((s for s in dis if s["source"] == "GDACS"),
                                  key=lambda g: ({"Red": 0, "Orange": 1}.get(g["level"], 2), g["time"] or ""))
                  if g["level"] in ("Red", "Orange") or g["country"] in focus][:40],
        "nws": nws_summary[:20],
        "eonet": [{"type": e["dtype"], "t": e["term"], "u": e["url"], "time": e["time"]} for e in dis if e["source"] == "NASA EONET"][:30],
    }
    return out, data


def collect(cfg, state, gap_h=0.0):
    # (name, function, args, cache minutes). Slow sources are cached, and a source that fails
    # falls back to its last good result for up to 6 hours. One broken source never stops the rest.
    # gap_h = hours the PC was off: then we also fetch the sports results of the missed days.
    jobs = []
    if gap_h >= 8:
        today = datetime.now(timezone.utc).date()
        for back in range(1, min(3, math.ceil(gap_h / 24) + 1) + 1):
            day = (today - timedelta(days=back)).strftime("%Y%m%d")
            for path, label, cc in cfg.get("sports_leagues", []):
                jobs.append((f"ESPN {label} {day}", src_espn, (path, label, cc, day), 0))
    for geo in cfg["google_trends_geos"]:
        jobs.append((f"Google Trends {geo}", src_google_trends, (geo,), 0))
    for cc, slug in cfg["x_trends_countries"].items():
        jobs.append((f"X trends {cc}", src_x_trends, (cc, slug), 0))
    for cc, params in cfg["google_news"].items():
        jobs.append((f"Google News {cc}", src_google_news, (cc, params), 0))
        if cc in cfg.get("google_news_section_countries", []):
            for sec in cfg.get("google_news_sections", []):
                jobs.append((f"Google News {cc} {sec.title()}", src_google_news, (cc, params, sec), 0))
    for feed in cfg.get("extra_feeds", []):
        jobs.append((feed["name"], src_feed, (feed,), 45 if feed.get("kind") == "community" else 0))
    for lang, cc in cfg.get("wikipedia", {}).items():
        jobs.append((f"Wikipedia {lang}", src_wikipedia, (lang, cc), 180))
    for ed in cfg.get("watch_news_editions", ["US"]):
        params = cfg["google_news"].get(ed)
        if params:
            for term, _group in watch_terms(cfg):
                jobs.append((f"Watch {ed}: {term}", src_watch, (term, ed, params), 30))
    ac = cfg.get("ai_tools") or {}
    if ac.get("enabled", True):
        for pipe in ac.get("hf_pipelines", list(HF_PIPE_LABEL)):
            jobs.append((f"Hugging Face {pipe}", src_hf, (pipe,), 60))
    for path, label, cc in cfg.get("sports_leagues", []):
        jobs.append((f"ESPN {label}", src_espn, (path, label, cc), 0))
    for cc in cfg.get("music_countries", []):
        jobs.append((f"Apple Music {cc}", src_apple_music, (cc,), 60))
    if cfg.get("stocks", True):
        jobs.append(("Yahoo Finance trending", src_yahoo, (), 0))
    jobs.append(("Hacker News", src_hn, (), 30))
    jobs.append(("iTunes top movies", src_itunes_movies, (), 360))
    if cfg.get("youtube_api_key"):
        for cc in FOCUS:
            jobs.append((f"YouTube {cc}", src_youtube, (cc, cfg["youtube_api_key"]), 60))
    if cfg.get("briefing_url"):
        jobs.append(("Claude briefing", src_briefing, (cfg["briefing_url"],), 10))
    if (cfg.get("disasters") or {}).get("enabled", True):
        jobs += [("USGS earthquakes", src_usgs, (), 0), ("EMSC earthquakes Europe", src_emsc, (), 0),
                 ("GDACS disaster alerts", src_gdacs, (), 20), ("NWS US weather alerts", src_nws, (), 0),
                 ("NASA EONET", src_eonet, (), 60)]

    cache = state.setdefault("cache", {})
    signals, health, todo = [], [], []
    for job in jobs:
        c = cache.get(job[0])
        if job[3] and c and time.time() - c["ts"] < job[3] * 60:
            signals += [dict(s) for s in c["signals"]]
            health.append({"name": job[0], "ok": True, "n": len(c["signals"]), "err": None, "cached": True})
        else:
            todo.append(job)

    def run(job):
        name, fn, args, _ = job
        for attempt in (1, 2):
            try:
                return name, fn(*args), None
            except Exception as e:  # noqa: BLE001 - one bad source must not stop the rest
                err = f"{type(e).__name__}: {str(e)[:120]}"
                if attempt == 2 or "429" in err:
                    return name, [], err
                time.sleep(3)

    with ThreadPoolExecutor(max_workers=8) as ex:
        for name, sigs, err in ex.map(run, todo):
            if err:
                log(f"source failed: {name}: {err}")
                c = cache.get(name)
                if c and time.time() - c["ts"] < 6 * 3600:
                    sigs = [dict(s) for s in c["signals"]]
            elif sigs:
                cache[name] = {"ts": time.time(), "signals": [dict(s) for s in sigs]}
            health.append({"name": name, "ok": err is None, "n": len(sigs), "err": err})
            signals += sigs
    state["cache"] = {k: v for k, v in cache.items() if time.time() - v["ts"] < 24 * 3600}
    return signals, health

# --------------------------------------------------------------------------- topics & scoring


class UF:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, i):
        while self.p[i] != i:
            self.p[i] = self.p[self.p[i]]
            i = self.p[i]
        return i

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a != b:
            self.p[b] = a


def is_ignored(key, cfg):
    if not key or WEEKDAY_FLUFF.search(key) or key in STOP:  # single generic word like "open"
        return True
    for ig in cfg.get("ignore", []):
        n = norm(ig)
        if key == n or key.startswith(n + " "):
            return True
    return False


def watch_hit(text_toks, text_norm, cfg):
    for w in cfg.get("watchlist", []):
        n = norm(w)
        wt = n.split()
        if wt and (set(wt) <= text_toks if len(wt) == 1 else f" {n} " in f" {text_norm} "):
            return w
    return None


def is_term(s):
    k = s["kind"]
    if k in ("search", "social", "wiki"):
        return True
    if k == "music":
        return s["rank"] <= 10
    if k == "finance":
        return s.get("known", False)
    return False


def build_topics(signals, cfg, now):
    cw = cfg.get("country_weight", {})
    terms, heads = [], []
    for s in signals:
        if s["kind"] in ("sport", "movie_chart", "watch", "briefing", "disaster", "ai_model"):
            continue
        s["key"] = norm(s["term"])
        s["toks"] = s["key"].split()
        if is_term(s):
            if not is_ignored(s["key"], cfg) and s["toks"]:
                terms.append(s)
        elif s["kind"] in HEAD_KINDS:
            heads.append(s)
        for n in s.get("news", []):  # Google Trends attaches its own articles
            k = norm(n["title"])
            heads.append({"kind": "news", "source": "Google Trends", "outlet": n["source"], "country": s["country"],
                          "term": n["title"], "url": n["url"], "rank": 99, "from_gt": True, "owner": s["key"],
                          "key": k, "toks": k.split()})
    for h in heads:
        h["tokset"] = set(h["toks"])
        h["age_h"] = hours_since(h.get("published"), now)   # 9999 = unknown
        h["recent"] = h["age_h"] <= 2

    # ---- cluster short trend terms
    keys = sorted({s["key"] for s in terms})
    kidx = {k: i for i, k in enumerate(keys)}
    ksets = {k: set(k.split()) for k in keys}
    uf = UF(len(keys))
    for a in keys:
        A = ksets[a]
        for b in keys:
            if a == b:
                continue
            B = ksets[b]
            if len(A) < len(B) and A <= B:
                if len(A) >= 2 or (distinctive(next(iter(A))) and len(B) <= 3):
                    uf.union(kidx[a], kidx[b])
    tokcount = Counter(t for k in keys for t in ksets[k] if distinctive(t))
    themes = {t for t, c in tokcount.items() if c >= 3}
    for t in themes:
        ks = [k for k in keys if t in ksets[k]]
        for k in ks[1:]:
            uf.union(kidx[ks[0]], kidx[k])
    groups = {}
    for s in terms:
        groups.setdefault(uf.find(kidx[s["key"]]), []).append(s)

    topics = []
    for members in groups.values():
        mkeys = sorted({m["key"] for m in members})
        theme = None
        if len(mkeys) >= 3:
            c = Counter(t for k in mkeys for t in set(k.split()) if t in themes)
            if c:
                theme = c.most_common(1)[0][0]
        topics.append({"members": members, "keys": mkeys, "theme": theme, "heads": [], "story": False})

    # ---- attach headlines as evidence
    unmatched = []
    for h in heads:
        hit = False
        for t in topics:
            for k in t["keys"]:
                kt = k.split()
                if h.get("owner") == k or ((len(kt) >= 2 or distinctive(kt[0])) and matches_phrase(kt, h["tokset"])):
                    t["heads"].append(h)
                    hit = True
                    break
        if not hit:
            unmatched.append(h)

    # ---- merge trend terms that are clearly the same story (they share most of their headlines),
    #      e.g. "Democrats", "Senate", "#Midterms2026" -> one topic instead of ten notifications
    hids = [{id(h) for h in t["heads"] if h["kind"] == "news"} for t in topics]
    uf2 = UF(len(topics))
    for i in range(len(topics)):
        for j in range(i + 1, len(topics)):
            A, B = hids[i], hids[j]
            if len(A) >= 2 and len(B) >= 2:
                s = len(A & B)
                r = s / min(len(A), len(B))
                if (s >= 2 and r >= 0.6) or (s >= 4 and r >= 0.4):
                    uf2.union(i, j)
    merged = {}
    for i, t in enumerate(topics):
        g = merged.setdefault(uf2.find(i), {"members": [], "keys": [], "theme": None, "heads": [], "story": False})
        g["members"] += t["members"]
        g["keys"] = sorted(set(g["keys"]) | set(t["keys"]))
        g["theme"] = g["theme"] or t["theme"]
        seen = {id(h) for h in g["heads"]}
        g["heads"] += [h for h in t["heads"] if id(h) not in seen]
    topics = list(merged.values())

    # ---- big headlines that are not already a trend term become "stories"
    def is_cand(h):
        if h.get("from_gt") or h["kind"] != "news":
            return False
        if h["source"] == "Google News":
            return h["rank"] <= 10
        if h.get("section"):
            return h["rank"] <= 3
        if h["source"] in TOP_FEEDS:
            return h["rank"] <= 5
        return bool(h.get("breaking")) and h["source"] in TRUSTED and h["recent"]
    cand = [h for h in unmatched if is_cand(h)]
    cand_ids = {id(h) for h in cand}
    stories = []
    for h in cand:
        sig = {t for t in h["toks"] if distinctive(t)}
        for st in stories:
            inter = sig & st["sig"]
            if len(inter) >= 2 and len(inter) / max(1, len(sig | st["sig"])) >= 0.3:
                st["heads"].append(h)
                st["sig"] |= sig
                break
        else:
            stories.append({"members": [], "keys": [h["key"]], "theme": None, "heads": [h], "story": True, "sig": sig})
    for h in unmatched:  # other outlets covering the same story
        if id(h) in cand_ids:
            continue
        sig = {t for t in h["toks"] if distinctive(t)}
        for st in stories:
            if len(sig & st["sig"]) >= 3:
                st["heads"].append(h)
                break
    topics += stories

    for t in topics:
        score_topic(t, cw, cfg)
    return [t for t in topics if t["score"] > 0]


def classify(t):
    votes = Counter()
    for m in t["members"]:
        if m.get("cat"):
            votes[m["cat"]] += 3
    for h in t["heads"][:30]:
        if h.get("cat"):
            votes[h["cat"]] += 2
    name_text = " " + " ".join(t["keys"]) + " "     # words in the trend itself count most
    head_text = " " + " ".join(h["key"] for h in t["heads"][:15]) + " "
    name_toks, head_toks = set(name_text.split()), set(head_text.split())
    for cat, (words, phrases) in CAT_INDEX.items():
        n = 3 * (len(words & name_toks) + sum(1 for p in phrases if f" {p} " in name_text))
        n += len(words & head_toks) + sum(2 for p in phrases if f" {p} " in head_text)
        if n:
            votes[cat] += n
    return votes.most_common(1)[0][0] if votes else "General"


def score_topic(t, cw, cfg):
    def w(cc):
        return cw.get(cc, 0.5)
    parts = Counter()
    countries, kinds = set(), set()
    gt, xs, wk, mu, fi = [], [], [], [], []
    for m in t["members"]:
        countries.add(m["country"])
        kinds.add(m["kind"])
        if m["kind"] == "search":
            parts["google"] += w(m["country"]) * (1 + 1.5 * math.log10(max(m["traffic"], 100) / 200 + 0.5))
            gt.append(m)
        elif m["kind"] == "social":
            parts["x"] += w(m["country"]) * (1 + 1.5 * (1 - (m["rank"] - 1) / 30) + 2 * min(m["hours"], 24) / 24)
            xs.append(m)
        elif m["kind"] == "wiki":
            parts["wiki"] += 0.6 * w(m["country"]) * max(0.3, 1 + math.log10(max(m["views"], 1) / 20000))
            wk.append(m)
        elif m["kind"] == "music":
            parts["charts"] += 0.4 * w(m["country"]) * (1 - (m["rank"] - 1) / 10) + 0.2
            mu.append(m)
        elif m["kind"] == "finance":
            parts["stocks"] += 0.6 * (1 - (m["rank"] - 1) / 20) + 0.4
            fi.append(m)
    trend_countries = set(countries)
    outlets, community, yt, recent, gn_best = set(), 0, 0, 0, None
    breaking = None
    for h in t["heads"]:
        if h["kind"] == "community":
            community += 1
            kinds.add("community")
        elif h["kind"] == "youtube":
            yt += 1
            kinds.add("youtube")
        else:
            outlets.add((h.get("outlet") or h["source"]).lower())
            kinds.add("news")
            if h["source"] == "Google News" or h["source"] in TOP_FEEDS or h.get("section"):
                if h["source"] == "Google News" or h["source"] in TOP_FEEDS:
                    gn_best = min(gn_best or 99, h["rank"])
                if t["story"]:
                    f = 0.7 if h.get("section") else 1.0
                    parts["topnews"] += f * w(h["country"]) * (2.5 * max(0, 1 - (h["rank"] - 1) / 10)
                                                               + 0.25 * min(h.get("coverage", 1), 10))
            if h.get("breaking") and h.get("recent") and h["source"] in TRUSTED and not breaking:
                breaking = h
        if h.get("recent"):
            recent += 1
        countries.add(h["country"])
    parts["news"] = min(5.0, 0.6 * len(outlets))
    if gn_best and gn_best <= 5 and not t["story"]:
        parts["news"] += 1.5
    parts["community"] = min(2.4, 0.8 * community)
    parts["youtube"] = min(2.4, 0.8 * yt)
    parts["velocity"] = min(4.0, 0.4 * recent)   # articles published in the last 2 hours
    # trending (search / X / Wikipedia / charts) in several countries is the strongest signal;
    # only being mentioned in another country's news counts a little.
    if t["story"]:
        parts["countries"] = 1.5 * max(0, len(countries) - 1)
    else:
        parts["countries"] = 2.5 * max(0, len(trend_countries) - 1) + min(2.0, 1.0 * len(countries - trend_countries))
    parts["sources"] = 2.0 * max(0, len(kinds) - 1)
    t["parts"] = parts
    t["base"] = sum(parts.values())
    if kinds == {"social"}:  # only on X, no search / news: often fandom or bot hashtags
        parts["x_only"] = -0.5 * t["base"]
        t["base"] *= 0.5
    t["score"] = round(t["base"], 1)
    t["countries"] = sorted(countries, key=lambda c: (-cw.get(c, 0.5), c))
    t["kinds"] = sorted(kinds)
    t["outlets"] = len(outlets)
    t["recent"] = recent
    # freshness: when did the first / latest article come out, how many in the last hour
    ages = [h["age_h"] for h in t["heads"] if -0.5 < h.get("age_h", 9999) <= 72]
    t["first_pub_h"] = round(max(ages), 2) if ages else None
    t["last_pub_h"] = round(max(0.0, min(ages)), 2) if ages else None
    hour1 = [h for h in t["heads"] if -0.5 < h.get("age_h", 9999) <= 1 and h["kind"] == "news"]
    t["recent1"] = len(hour1)
    t["recent1_outlets"] = len({(h.get("outlet") or h["source"]).lower() for h in hour1})
    t["just_in"] = t["recent1_outlets"] >= cfg.get("just_in_outlets", 4) and (t["first_pub_h"] or 99) <= 3
    t["breaking"] = breaking
    t["gt"], t["x"], t["wk"], t["mu"], t["fi"] = gt, xs, wk, mu, fi

    # name, context, picture, link
    if t["story"]:
        tops = [h for h in t["heads"] if h["source"] == "Google News" or h["source"] in TOP_FEEDS or h.get("section")]
        h0 = min(tops or t["heads"], key=lambda h: (bool(h.get("section")), h["rank"]))
        t["name"] = h0["term"]
        t["context"] = h0.get("outlet") or h0["source"]
        t["url"] = h0["url"]
        t["query"] = " ".join([x for x in h0["toks"] if distinctive(x)][:5]) or h0["term"]
    else:
        # a merged topic is named after what it is really about: the shared theme word
        # (e.g. "midterm"), else the member that most of its headlines mention
        cands = t["members"]
        if t["theme"]:
            cands = [m for m in t["members"] if t["theme"] in m["key"].split()] or cands
        elif len({m["key"] for m in t["members"]}) >= 4:
            cover = Counter({m["key"]: sum(1 for h in t["heads"] if set(m["toks"]) <= h["tokset"]) for m in t["members"]})
            top_key = cover.most_common(1)[0][0]
            cands = [m for m in t["members"] if m["key"] == top_key]
        prefer = ([m for m in cands if m["kind"] == "social"] or [m for m in cands if m["kind"] == "wiki"]
                  or [m for m in cands if m["kind"] in ("search", "finance")] or cands)
        best = max(prefer, key=lambda m: (m.get("traffic", 0), m.get("hours", 0), -m["rank"]))
        t["name"] = best["display"]
        news_heads = [h for h in t["heads"] if h["kind"] == "news"]
        news_heads.sort(key=lambda h: (not h.get("from_gt"), not h.get("recent"), h["rank"]))
        t["context"] = news_heads[0]["term"] if news_heads else ""
        t["url"] = news_heads[0]["url"] if news_heads else best["url"]
        t["query"] = split_hashtag(t["name"])
    t["picture"] = next((m["picture"] for m in gt if m.get("picture")), "") or next((m.get("art") for m in mu if m.get("art")), "")
    own = [h for h in t["heads"] if h.get("owner")][:4] + [h for h in t["heads"] if not h.get("owner")][:4]
    text_norm = " ".join(t["keys"] + [h["key"] for h in own])
    t["watch"] = watch_hit(set(text_norm.split()), text_norm, cfg)
    t["sig"] = sorted({x for k in t["keys"] for x in k.split() if distinctive(x)} | t.get("sig", set()))
    t["category"] = classify(t)


def summary_line(t):
    bits = [" ".join(t["countries"][:5])]
    if t.get("category") and t["category"] != "General":
        bits.append(t["category"])
    if t["gt"]:
        best = max(t["gt"], key=lambda m: m["traffic"])
        bits.append(f"Google {fmt_traffic(best['traffic'])} ({best['country']})")
    if t["x"]:
        best = min(t["x"], key=lambda m: m["rank"])
        h = max(m["hours"] for m in t["x"])
        bits.append(f"X #{best['rank']}" + (f" for {h}h" if h >= 3 else ""))
    if t["wk"]:
        bits.append(f"Wiki {max(m['views'] for m in t['wk']) // 1000}K views")
    if t["mu"]:
        m = min(t["mu"], key=lambda m: m["rank"])
        bits.append(f"#{m['rank']} chart {m['country']}")
    if t["fi"]:
        bits.append(f"stock {t['fi'][0]['symbol']} trending")
    if t["story"]:
        gn = [h for h in t["heads"] if h["source"] == "Google News" or h["source"] in TOP_FEEDS]
        if gn:
            h0 = min(gn, key=lambda h: h["rank"])
            bits.append(f"Top news #{h0['rank']} ({h0['country']})")
    if t["outlets"]:
        bits.append(f"{t['outlets']} news sites")
    if t.get("recent1", 0) >= 3:
        bits.append(f"{t['recent1']} articles in 1h")
    elif t.get("recent", 0) >= 3:
        bits.append(f"{t['recent']} new in 2h")
    if t.get("first_pub_h") is not None:
        bits.append(f"since {fmt_age(t['first_pub_h'])}")
    return " · ".join(bits)


def fmt_age(h):
    if h is None:
        return "?"
    if h < 1:
        return f"{max(1, round(h * 60))} min"
    if h < 48:
        return f"{round(h)}h"
    return f"{round(h / 24)} days"


def gdelt_boost(topics, state, cfg, health):
    """GDELT: is coverage of the top topics accelerating? (last 2h vs the day). Rate-limit friendly."""
    if not cfg.get("gdelt", True):
        return
    g = state.setdefault("gdelt", {"backoff": 0, "cache": {}})
    nowts = time.time()
    cache = {k: v for k, v in g.get("cache", {}).items() if nowts - v["ts"] < 3 * 3600}
    g["cache"] = cache
    asked, status = 0, "ok"
    if nowts < g.get("backoff", 0):
        status = "paused (rate limit)"
    for t in [t for t in topics if not t["story"]][:6]:
        q = norm(t["query"])
        if len(q) < 3:
            continue
        c = cache.get(q)
        if (not c or nowts - c["ts"] > 3600) and nowts >= g.get("backoff", 0) and asked < 2:
            if asked:
                time.sleep(5.5)  # GDELT allows one request every 5 seconds
            asked += 1
            phrase = f'"{q}"' if " " in q else q
            try:
                d = fetch_json(GDELT_URL.format(q=urllib.parse.quote(phrase)), timeout=15)
                vals = [p.get("value", 0) for p in (d.get("timeline") or [{}])[0].get("data", [])]
                c = cache[q] = {"ts": nowts, "vals": vals}
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    g["backoff"] = nowts + 2 * 3600
                    status = "rate limited - paused 2h"
                    break
                status = f"HTTP {e.code}"
                continue
            except Exception as e:  # noqa: BLE001
                status = f"{type(e).__name__}"
                continue
        if not c:
            continue
        vals = c["vals"]
        if len(vals) >= 16:
            recent = sum(vals[-8:])
            before = sum(vals[:-8]) / max(1, len(vals) - 8) * 8
            ratio = recent / max(before, 1)
            if recent >= 5 and ratio > 1:
                bonus = round(min(3.0, math.log2(ratio)), 1)
                t["parts"]["gdelt"] = bonus
                t["base"] += bonus
                t["gdelt"] = {"recent": recent, "ratio": round(ratio, 1)}
    health.append({"name": "GDELT (acceleration)", "ok": status == "ok", "n": asked,
                   "err": None if status == "ok" else status})

# --------------------------------------------------------------------------- state / memory


def update_state(topics, state, now):
    st = state.setdefault("topics", {})
    index = {}
    for tid, rec in st.items():
        for k in rec.get("keys", []):
            index.setdefault(k, tid)
    hour = now.strftime("%Y-%m-%dT%H")
    day = now.strftime("%Y-%m-%d")
    used = set()
    for t in topics:
        ids = Counter(index[k] for k in t["keys"] if k in index and index[k] not in used)
        tid = ids.most_common(1)[0][0] if ids else None
        if not tid:
            sig = set(t["sig"])
            for oid, rec in st.items():
                if oid in used or not rec.get("sig"):
                    continue
                o = set(rec["sig"])
                if sig and len(sig & o) >= 2 and len(sig & o) / len(sig | o) >= 0.5:
                    tid = oid
                    break
        parent = None
        if not tid:
            tid = sid((t["keys"] or [t["name"]])[0] + day)
            # a trend that split off a bigger topic (e.g. "Senate" from "Midterms") keeps the
            # parent's history, so it is not announced again as if it were new
            fam = Counter(index[k] for k in t["keys"] if k in index)
            parent = st.get(fam.most_common(1)[0][0]) if fam else None
        used.add(tid)
        if tid not in st and parent:
            st[tid] = {"first_seen": parent["first_seen"], "hours": list(parent.get("hours", [])),
                       "days": list(parent.get("days", [])), "notified_tier": parent.get("notified_tier", 0),
                       "notified_at": parent.get("notified_at"), "best": 0, "last_score": 0,
                       "notified_countries": list(parent.get("notified_countries", [])),
                       "breaking_sent": parent.get("breaking_sent", False)}
        rec = st.setdefault(tid, {"first_seen": now.isoformat(), "hours": [], "days": [], "notified_tier": 0,
                                  "notified_at": None, "notified_countries": [], "best": 0, "last_score": 0})
        rec["keys"] = sorted(set(rec.get("keys", [])) | set(t["keys"]))[-40:]
        rec["sig"] = t["sig"][:30]
        rec["name"] = t["name"]
        if hour not in rec["hours"]:
            rec["hours"] = (rec["hours"] + [hour])[-300:]
        if day not in rec["days"]:
            rec["days"] = (rec["days"] + [day])[-60:]
        rec["prev_score"] = rec.get("last_score", 0)
        rec["last_seen"] = now.isoformat()
        t["id"] = tid
        t["rec"] = rec
        # persistence = "repeats a lot": hours and days it has been on the radar
        n_hours, n_days = len(rec["hours"]), len(rec["days"])
        t["parts"]["repeat"] = min(4.0, 0.3 * (n_hours - 1)) + (2.0 if n_days >= 2 else 0) + (1.0 if n_days >= 4 else 0)
        t["score"] = round(t["base"] + t["parts"]["repeat"], 1)
        rec["last_score"] = t["score"]
        rec["best"] = max(rec.get("best", 0), t["score"])
        t["hours_seen"], t["days_seen"] = n_hours, n_days
        t["age_h"] = round(hours_since(rec["first_seen"], now), 1)
        t["rising"] = round(t["score"] - rec["prev_score"], 1) if rec["prev_score"] else None
    cutoff = now - timedelta(days=7)
    for tid in [k for k, r in st.items() if datetime.fromisoformat(r.get("last_seen", r["first_seen"])) < cutoff]:
        del st[tid]

# --------------------------------------------------------------------------- alerts


def tier_of(score, cfg, story=False):
    if story:  # a big headline that is not (yet) a search trend
        return 1 if score >= cfg.get("story_score", 9) else 0
    return 2 if score >= cfg["hot_score"] else 1 if score >= cfg["trend_score"] else 0


def in_quiet_hours(cfg, now):
    q = cfg.get("quiet_hours") or []
    if len(q) != 2:
        return False
    a, b = q
    h = now.hour
    return (a <= h < b) if a < b else (h >= a or h < b)


def cache_picture(url):
    if not url or not IS_WIN:
        return None
    IMG.mkdir(parents=True, exist_ok=True)
    p = IMG / (sid(url) + ".jpg")
    if not p.exists():
        try:
            p.write_bytes(fetch(url, timeout=10))
        except Exception:  # noqa: BLE001
            return None
    return p.as_uri()


# Importance (= ntfy priority) decides who gets an alert:
#   5 urgent (breaking, red disasters) · 4 very important (hot, just in, repeating, big finals, briefing)
#   3 trending / normal · 2 low (digest, music charts, reminders)
KIND_LABEL = {"disaster": "DISASTER", "watch": "WATCHLIST", "music": "MUSIC CHART", "event": "EVENT",
              "digest": "DIGEST", "catchup": "SUMMARY", "briefing": "BRIEFING", "ai": "AI MODEL"}
KIND_PRIORITY = {"music": 2, "digest": 2, "catchup": 4, "briefing": 4}


def mk_alert(title, line2="", line3="", url=None, actions=None, img=None, long=False, tag=None, priority=3,
             short=None, kind="info", **phone):
    """phone: optional push_text, countries, category, pic_url, label for the ntfy notification."""
    priority = KIND_PRIORITY.get(kind, priority)
    label = phone.pop("label", None) or (("LIVE" if "LIVE" in title else "SPORTS RESULT") if kind == "sport"
                                         else KIND_LABEL.get(kind))
    return {"title": title[:150], "line2": line2 or "", "line3": line3 or "", "url": url or DASH_LINK,
            "actions": actions or [("Dashboard", DASH_LINK)], "img": img, "long": long,
            "tag": (tag or sid(title))[:16], "priority": priority, "short": short or title, "kind": kind,
            "label": label, **phone}


def research_links(t):
    q = urllib.parse.quote(t["query"])
    main = next((c for c in t["countries"] if c in NEWS_EDITION), "US")
    hl, geo = NEWS_EDITION[main]
    return {
        "news": f"https://news.google.com/search?q={q}&{hl}",
        "youtube": f"https://www.youtube.com/results?search_query={q}&sp=CAI%253D",
        "tiktok": f"https://www.tiktok.com/search?q={q}",
        "x": f"https://x.com/search?q={q}&f=live",
        "trends": f"https://trends.google.com/trends/explore?date=now%207-d&geo={geo}&q={q}",
    }


def plan_topic_alerts(topics, cfg, now):
    queue = []
    quiet = in_quiet_hours(cfg, now)
    for t in topics:
        rec = t["rec"]
        tier = tier_of(t["score"], cfg, t["story"])
        t["tier"] = tier
        reason = None
        last = rec.get("notified_at")
        cool = hours_since(last, now) > cfg["renotify_hours"]
        new_focus = [c for c in t["countries"] if c in FOCUS and c not in rec.get("notified_countries", [])]
        if t["breaking"] and not rec.get("breaking_sent") and rec["notified_tier"] == 0:
            reason = "breaking"
        elif t["just_in"] and rec["notified_tier"] == 0 and not rec.get("justin_sent") and t["score"] >= 4:
            reason = "justin"     # many sites wrote about it in the last hour: it just happened
        elif tier > 0 and rec["notified_tier"] == 0:
            reason = "new"
        elif tier > rec["notified_tier"]:
            reason = "hot"
        elif (tier > 0 and t["days_seen"] in cfg.get("repeat_notify_days", []) and t["hours_seen"] >= 6
              and rec.get("repeat_day", 1) < t["days_seen"] and cool):
            reason = "repeat"     # keeps coming back day after day
        elif tier > 0 and new_focus and cool and not t["story"]:
            reason = "spread"
        if reason and quiet and tier < 2 and reason not in ("breaking", "justin"):
            reason = None
        if reason:
            queue.append((t, reason))
    order = {"breaking": 0, "justin": 1, "hot": 2, "new": 3, "repeat": 4, "spread": 5}
    queue.sort(key=lambda q: (order[q[1]], -q[0]["score"]))
    # trends about the same story (sharing many headlines) go into ONE notification: "also: ..."
    grouped, also = [], []
    for t, reason in queue:
        hs = {id(h) for h in t["heads"] if h["kind"] == "news"}
        parent = None
        if reason != "breaking" and hs:
            for g in grouped:
                if g[2] and len(hs & g[2]) / len(hs) >= 0.35:
                    parent = g
                    break
        if parent:
            parent[3].append(t["name"])
            parent[2] |= hs
            also.append((t, reason))
        else:
            grouped.append([t, reason, hs, []])
    return [(t, r, rel) for t, r, _, rel in grouped], also


FLAG_TAG = {"US": "us", "DE": "de", "GB": "gb", "FR": "fr", "IT": "it", "ES": "es", "EU": "eu"}  # ntfy shows flags
EU_SET = {"GB", "FR", "IT", "ES", "EU", "NL", "AT", "CH"}
# phone channels = your topic + suffix. Subscribe in ntfy only to the ones you want (e.g. USA only).
CHANNEL_FILTERS = {
    "-us": ("USA", lambda cs: "US" in cs),
    "-de": ("Germany", lambda cs: any(c in DACH for c in cs)),
    "-eu": ("Europe", lambda cs: any(c in EU_SET for c in cs)),
}
CHANNEL_HASH = {"": "", "-all": "", "-us": "#us", "-de": "#de", "-eu": "#eu", "-sports": "#sports",
                "-disasters": "#disasters", "-ai": "#ai"}


def channels_for(a, cfg):
    """Phone channels (your topic + ending):
    ''  = VERY IMPORTANT only (breaking, hot, just in, repeating, big disasters, briefing)
    '-all' = everything · '-us' / '-de' / '-eu' = that country, trending and up · '-sports' · '-disasters'."""
    if a.get("channels"):
        return a["channels"]
    pr, cs = a["priority"], a.get("countries") or []
    ch = ["-all"]
    if pr >= cfg.get("phone_important_priority", 4):
        ch.append("")
    if pr >= cfg.get("phone_country_min_priority", 3):
        ch += [suf for suf, (_, keep) in CHANNEL_FILTERS.items() if keep(cs)]
    if a.get("category") == "Sports":
        ch.append("-sports")
    if a.get("category") == "Natural disasters" or a["kind"] == "disaster" or a.get("label") == "BREAKING":
        ch.append("-disasters")
    if a.get("category") == "AI video & image" or a["kind"] == "ai":
        ch.append("-ai")
    return ch


def country_list(cs, n=4):
    names = [COUNTRY_NAMES.get(c, c) for c in cs]
    return ", ".join(names[:n]) + (f" +{len(names) - n}" if len(names) > n else "")


def phone_text(t, reason, related=()):
    """Clear, short lines for the phone (ntfy) instead of the dense PC line."""
    lines = []
    if reason == "breaking" and t["breaking"]:
        b = t["breaking"]
        lines.append(f"\U0001F6A8 {b['term']} ({b.get('outlet') or b['source']})")
        lines.append("✅ confirmed by several sources" if t["outlets"] >= 2 else "⏳ verification pending")
    elif t["context"] and not t["story"]:
        lines.append(f"\U0001F4F0 {t['context']}")
    elif t["story"]:
        lines.append(f"\U0001F4F0 {t['context']}")
    cat = f" · {t['category']}" if t.get("category") and t["category"] != "General" else ""
    lines.append(f"\U0001F30D {country_list(t['countries'])}{cat}")
    fresh = []
    if t.get("first_pub_h") is not None:
        fresh.append(f"since {fmt_age(t['first_pub_h'])}")
    if t.get("recent1"):
        fresh.append(f"{t['recent1']} articles in the last hour")
    if reason == "repeat":
        fresh.append(f"on the radar {t['hours_seen']}h / {t['days_seen']} days")
    if fresh:
        lines.append("\U0001F552 " + " · ".join(fresh))
    sig = []
    if t["gt"]:
        sig.append(f"Google {fmt_traffic(max(m['traffic'] for m in t['gt']))}")
    if t["x"]:
        sig.append(f"X #{min(m['rank'] for m in t['x'])}")
    if t["outlets"]:
        sig.append(f"{t['outlets']} news sites")
    if sig:
        lines.append("\U0001F4C8 " + " · ".join(sig))
    if related:
        lines.append("➕ also: " + ", ".join(related[:5]))
    return "\n".join(lines)


def short_line(i, t):
    since = f", since {fmt_age(t['first_pub_h'])}" if t.get("first_pub_h") is not None else ""
    return f"{i}. {t['name']} ({country_list(t['countries'], 3)}{since})"


def topic_alert(t, reason, related=()):
    rlab = {"hot": "HOT", "new": "TRENDING", "spread": "SPREADING", "breaking": "BREAKING", "justin": "JUST IN",
            "repeat": f"STILL TRENDING · DAY {t.get('days_seen', 2)}"}[reason]
    if reason == "new" and t["tier"] == 2:
        rlab = "HOT"
    icon = {2: "\U0001F525", 1: "\U0001F4C8", 0: "\U0001F4F0"}[t["tier"]]
    if t["story"]:
        icon = "\U0001F4F0"
        if reason == "new":
            rlab = "TOP NEWS"
    icon = {"breaking": "\U0001F6A8", "justin": "⚡", "repeat": "\U0001F501"}.get(reason, icon)
    title = f"{icon} {rlab}: {t['name']}"
    line2 = summary_line(t)
    if reason == "justin":
        line2 = (f"{t['recent1']} articles from {t['recent1_outlets']} sites in the last hour · "
                 f"first one {fmt_age(t['first_pub_h'])} ago · " + " ".join(t["countries"][:5]))
    if reason == "repeat":
        line2 = f"On the radar {t['hours_seen']}h over {t['days_seen']} days · " + line2
    if reason == "spread":
        line2 = "Now also in " + ", ".join(COUNTRY_NAMES.get(c, c) for c in t["countries"] if c in FOCUS) + " · " + line2
    if related:
        line2 = "also: " + ", ".join(related[:5]) + " · " + line2
    line3 = (t["context"] or "")[:150] if not t["story"] else ""
    if reason == "breaking":
        b = t["breaking"]
        line3 = f"{b['term'][:120]} ({b.get('outlet') or b['source']})"
        line3 += " · confirmed by several sources" if t["outlets"] >= 2 else " · verification pending"
    links = research_links(t)
    url = (t["breaking"]["url"] if reason == "breaking" else t["url"]) or links["news"]
    actions = [("Open", url), ("YouTube", links["youtube"]), ("Dashboard", DASH_LINK)]
    pr = (5 if reason == "breaking" else 4 if (t["tier"] == 2 or reason in ("justin", "repeat"))
          else 2 if reason == "spread" else 3)
    label = {"breaking": "BREAKING", "justin": "JUST IN", "repeat": "REPEATING", "spread": "SPREADING",
             "hot": "HOT"}.get(reason) or ("HOT" if t["tier"] == 2 else "TOP NEWS" if t["story"] else "TRENDING")
    a = mk_alert(title, line2, line3, url, actions, img=cache_picture(t.get("picture")),
                 long=(t["tier"] == 2 or reason in ("breaking", "justin")), tag=t["id"],
                 priority=pr, short=t["name"], kind="topic", label=label)
    a.update(push_text=phone_text(t, reason, related), countries=t["countries"], category=t.get("category"),
             pic_url=t.get("picture") or "")
    return a


def watch_alerts(signals, topics, state, cfg, now, quiet, since=None):
    """since = last check before the PC was off -> one 'while you were away' summary instead."""
    ws = state.setdefault("watch", {})
    arts = {}
    for s in signals:
        if s["kind"] == "watch":
            arts.setdefault(s["watch_term"], []).append(s)
    out, summary, first, missed = [], {}, [], []
    for term, group in watch_terms(cfg):
        extra_tags = {"category": group, "label": "AI TOOLS"} if group else {}
        items = sorted(arts.get(term, []), key=lambda a: a.get("published") or "", reverse=True)
        uniq, seen_t = [], set()
        for a in items:
            if a["term"] not in seen_t:
                seen_t.add(a["term"])
                uniq.append(a)
        recent2 = [a for a in uniq if hours_since(a.get("published"), now) <= 2]
        topic = next((t for t in topics if t.get("watch") == term), None)
        summary[term] = {"n24": len(uniq), "n2": len(recent2), "topic": topic["name"] if topic else None,
                         "topic_score": topic["score"] if topic else None, "group": group,
                         "items": [{"t": a["term"], "u": a["url"], "s": a["outlet"], "p": a.get("published")} for a in uniq[:8]]}
        rec = ws.setdefault(term, {"last": None, "spike": None, "seen": []})
        seen = set(rec["seen"])
        new_items = [a for a in uniq[:10] if sid(a["term"]) not in seen]
        if uniq:
            rec["seen"] = [sid(a["term"]) for a in uniq[:60]]
        if not rec.get("init"):
            rec["init"] = True
            rec["last"] = now.isoformat()
            if uniq:
                first.append((term, len(uniq)))
            continue
        if since:
            n_missed = sum(1 for a in uniq if (a.get("published") or "") > since)
            if n_missed:
                missed.append((term, n_missed, uniq[0]))
            rec["last"] = now.isoformat()
            continue
        spike = len(recent2) >= cfg.get("watch_spike_articles", 10) and hours_since(rec.get("spike"), now) >= 3
        cool = hours_since(rec.get("last"), now) >= cfg.get("watch_cooldown_hours", 6)
        if spike:
            a = recent2[0]
            out.append(mk_alert(f"\u26A1 {term.upper()} is spiking: {len(recent2)} articles in 2h", a["term"][:150],
                                f"{a['outlet']} · {len(uniq)} articles today", a["url"], tag="w" + sid(term),
                                priority=4, short=term, kind="watch", **extra_tags))
            rec["spike"] = rec["last"] = now.isoformat()
        elif cool and new_items and not quiet:
            a = new_items[0]
            extra = f" · trending: {topic['name']}" if topic and topic["score"] >= 3 else ""
            out.append(mk_alert(f"\u2B50 {term.upper()}: {a['term']}"[:150],
                                f"{a['outlet']} · {len(uniq)} articles today, {len(recent2)} in 2h{extra}",
                                (new_items[1]["term"][:140] if len(new_items) > 1 else ""), a["url"],
                                tag="w" + sid(term), short=term, kind="watch", **extra_tags))
            rec["last"] = now.isoformat()
    if first and not quiet:
        first.sort(key=lambda x: -x[1])
        out.append(mk_alert("\u2B50 Watchlist is on", " · ".join(f"{t} ({n}{'+' if n >= 40 else ''})" for t, n in first[:6]),
                            "Articles today. New ones will be sent automatically.", DASH_LINK, tag="watchinit",
                            short="watchlist", kind="watch", priority=2))
    if missed:
        missed.sort(key=lambda x: -x[1])
        lab = lambda n: f"{n}{'+' if n >= 40 else ''}"  # noqa: E731
        a = mk_alert("⭐ Watchlist while you were away", " · ".join(f"{t} ({lab(n)})" for t, n, _ in missed[:5]),
                     f"{missed[0][0].upper()}: {missed[0][2]['term'][:120]}", DASH_LINK, tag="watchaway",
                     short="watchlist", kind="watch")
        a["push_text"] = "\n".join(f"{t.upper()} ({lab(n)} new): {top['term']}" for t, n, top in missed[:10])
        out.append(a)
        state["catchup_watch"] = [{"term": t, "n": n, "t": top["term"], "u": top["url"]} for t, n, top in missed[:12]]
    return out, summary


BIG_NOTES = re.compile(r"super bowl|final|world series|championship|playoff|semifinal|klassiker|derby|madrid game|"
                       r"london game|munich game|berlin game|international|thanksgiving|christmas|all-star|wild card|"
                       r"divisional|conference|cup|pokal", re.I)


def big_game(g, cfg):
    if any(BIG_NOTES.search(n) for n in g["notes"]):
        return "special"
    if g["league"] in ("NFL", "NBA", "MLB", "NHL") and g.get("season_type") == 3:
        return "playoffs"
    if g["league"] == "UFC" and re.search(r"UFC \d{3}", g["term"] or ""):
        return "ufc"
    if g["league"] == "College Football":
        if sum(1 for t in g["teams"] if t.get("rank") and t["rank"] <= 15) == 2:
            return "ranked"
    names = {norm(t["name"]) for t in g["teams"]}
    for team in cfg.get("watch_teams", []):
        if norm(team) in names:
            return "team"
    return None


def score_text(g):
    ts = g["teams"]
    if g["league"] == "UFC":
        return g["term"]
    if len(ts) == 2:
        if g["state"] == "pre":
            return f"{ts[1]['name']} vs {ts[0]['name']}" if g["league"] in ("NFL", "NBA", "MLB", "NHL", "College Football") \
                else f"{ts[0]['name']} vs {ts[1]['name']}"
        return f"{ts[0]['name']} {ts[0]['score']} - {ts[1]['score']} {ts[1]['name']}"
    return g["term"]


def sports_alerts(signals, state, cfg, now, quiet, window_h=15):
    """window_h: how far back a FINAL may be and still be announced (longer after the PC was off)."""
    st = state.setdefault("sports", {})
    by_id = {}
    for s in signals:
        if s["kind"] == "sport":
            by_id[s["id"]] = s  # the same game can come from today's and yesterday's scoreboard
    games = list(by_id.values())
    out = []
    for g in games:
        g["big"] = big_game(g, cfg)
        g["score_text"] = score_text(g)
        if not g["big"] or not cfg.get("sports_notifications", True):
            continue
        rec = st.setdefault(g["id"], {"date": g["date"]})
        try:
            start = datetime.fromisoformat((g["date"] or "").replace("Z", "+00:00"))
        except ValueError:
            continue
        hrs = (now - start).total_seconds() / 3600
        note = " · ".join(g["notes"])
        if g["state"] == "post" and not rec.get("post"):
            rec["post"] = now.isoformat()
            if -1 < hrs < window_h and not quiet:
                out.append(mk_alert(f"\U0001F3C6 FINAL · {g['league']}: {g['score_text']}", note or g["detail"],
                                    "", g["url"], tag="s" + g["id"], short=g["score_text"], kind="sport",
                                    priority=4 if g["big"] in ("special", "playoffs") else 3,
                                    countries=[g["country"]], category="Sports",
                                    push_text=f"⚽ {g['score_text']}\n\U0001F3C1 {note or g['detail']}"))
        elif g["state"] == "in" and g["big"] in ("special", "playoffs", "ufc") and not rec.get("live"):
            rec["live"] = now.isoformat()
            if not quiet:
                out.append(mk_alert(f"\U0001F534 LIVE NOW · {g['league']}: {g['score_text']}", note or g["detail"],
                                    "", g["url"], tag="l" + g["id"], short=g["score_text"], kind="sport", priority=4,
                                    countries=[g["country"]], category="Sports"))
    for k in [k for k, v in st.items() if hours_since(parse_date(v.get("date")), now) > 96]:
        del st[k]
    return out, games


def music_alerts(signals, state, cfg, now, quiet):
    st = state.setdefault("music", {})
    out = []
    for cc in cfg.get("music_countries", []):
        rows = sorted([s for s in signals if s["kind"] == "music" and s["country"] == cc], key=lambda s: s["rank"])
        if not rows:
            continue
        ids = [r["id"] for r in rows]
        prev = st.get(cc)
        if prev and prev.get("top") and cfg.get("music_notifications", True) and not quiet:
            where = COUNTRY_NAMES.get(cc, cc)
            if ids[0] != prev["top"][0]:
                r = rows[0]
                out.append(mk_alert(f"\U0001F3B5 New #1 in {where}: {r['song']}", r["artist"], "Apple Music top songs",
                                    r["url"], img=cache_picture(r.get("art")), tag="m1" + cc, short=r["song"], kind="music",
                                    countries=[cc], category="Music", pic_url=r.get("art", ""),
                                    push_text=f"\U0001F3A4 {r['artist']}\n\U0001F947 New #1 on Apple Music {where}"))
            for r in rows[1:10]:
                if r["id"] not in prev["top"]:
                    out.append(mk_alert(f"\U0001F3B5 New in {where} top 10: #{r['rank']} {r['song']}", r["artist"],
                                        "Straight into the top 10", r["url"], img=cache_picture(r.get("art")),
                                        tag="m" + r["id"], short=r["song"], kind="music",
                                        countries=[cc], category="Music", pic_url=r.get("art", ""),
                                        push_text=f"\U0001F3A4 {r['artist']}\n\U0001F680 Straight into the top 10 ({where})"))
        st[cc] = {"top": ids, "ts": now.isoformat()}
    return out[:3]


def event_alerts(events, state, cfg, now, quiet):
    sent = state.setdefault("event_reminders", {})
    out = []
    today = now.date()
    for ev in events:
        try:
            d = date.fromisoformat(ev["date"])
        except (KeyError, ValueError):
            continue
        left = (d - today).days
        key = f"{ev['date']}|{ev['title']}|{left}"
        if left in cfg.get("event_reminder_days", []) and key not in sent and now.hour >= 9 and not quiet:
            when = "TODAY" if left == 0 else ("tomorrow" if left == 1 else f"in {left} days")
            line2 = f"{d:%a %d %b} · {ev.get('region', '')} · {ev.get('category', '')}" + \
                    (" (date not 100% sure)" if ev.get("approx") else "")
            out.append(mk_alert(f"\U0001F4C5 {when}: {ev['title']}", line2, ev.get("note", ""), ev.get("url") or DASH_LINK,
                                tag="e" + sid(key), short=ev["title"], kind="event", priority=3 if left == 0 else 2,
                                countries=[ev.get("region", "")], category=ev.get("category")))
            sent[key] = now.isoformat()
    for k in [k for k in sent if k.split("|")[0] < (today - timedelta(days=30)).isoformat()]:
        del sent[k]
    return out[:3]


def digest_alert(topics, state, cfg, now, quiet):
    last = state.get("last_digest")
    if not last:
        state["last_digest"] = now.isoformat()
        return None
    if hours_since(last, now) < cfg.get("digest_hours", 3) or quiet:
        return None
    top = [t for t in topics if not t["story"]][:6]
    if not top:
        return None
    state["last_digest"] = now.isoformat()
    items = [f"{i}. {t['name']} ({'/'.join(t['countries'][:2])})" for i, t in enumerate(top, 1)]
    a = mk_alert("\U0001F4CA Top trends right now", " · ".join(items[:3]), " · ".join(items[3:]), DASH_LINK,
                 tag="digest", short="digest", kind="digest", channels=["-all"])
    a["push_text"] = "\n".join(short_line(i, t) for i, t in enumerate(top, 1))
    out = [a]
    # the same digest for each country channel (phone only), e.g. "Top trends USA"
    for suffix, (label, keep) in CHANNEL_FILTERS.items():
        sel = [t for t in topics if not t["story"] and keep(t["countries"])][:6]
        if sel:
            out.append(mk_alert(f"\U0001F4CA Top trends {label}", "", "", DASH_LINK, tag="digest" + suffix,
                                short="digest", kind="digest", channels=[suffix], phone_only=True,
                                push_text="\n".join(short_line(i, t) for i, t in enumerate(sel, 1))))
    return out


def catchup_alerts(topics, queue, s_alerts, w_alerts, m_alerts, e_alerts, state, now, gap_h, since):
    """PC was off or asleep: one clear summary of what happened, instead of a flood."""
    gap = f"{round(gap_h)}h" if gap_h < 48 else f"{round(gap_h / 24)} days"
    top = [t for t in topics if t["tier"] > 0][:8] or topics[:8]
    items = [f"{i}. {t['name']} ({'/'.join(t['countries'][:2])})" for i, t in enumerate(top, 1)]
    a = mk_alert(f"\U0001F4E5 While you were away ({gap}): top trends", " · ".join(items[:4]), " · ".join(items[4:8]),
                 DASH_LINK, tag="catchup", priority=4, short="catch-up", kind="catchup")
    a["push_text"] = "\n".join(short_line(i, t) for i, t in enumerate(top, 1))
    alerts = [a]
    # breaking news of the last 2 hours still gets its own notification
    alerts += [topic_alert(t, r, rel) for t, r, rel in queue if r == "breaking"][:2]
    if s_alerts:
        res = [x["short"] for x in s_alerts]
        sa = mk_alert(f"\U0001F3C6 Results while you were away ({len(res)})", " · ".join(res[:3]), " · ".join(res[3:6]),
                      DASH_LINK, tag="sportsaway", short="results", kind="sport")
        sa["push_text"] = "\n".join(x["title"] for x in s_alerts[:15])
        alerts.append(sa)
    alerts += w_alerts[:2] + m_alerts[:2] + e_alerts[:3]
    state["catchup"] = {"at": now.isoformat(), "gap_h": round(gap_h, 1), "since": since,
                        "top": [{"name": t["name"], "summary": summary_line(t), "url": t["url"]} for t in top],
                        "results": [{"t": x["title"], "u": x["url"]} for x in s_alerts[:15]],
                        "watch": state.pop("catchup_watch", [])}
    return alerts


def fold(alerts, n, label):
    if len(alerts) <= n:
        return alerts
    rest = alerts[n:]
    return alerts[:n] + [mk_alert(f"{label} +{len(rest)} more", " · ".join(a["short"] for a in rest[:6])[:200],
                                  "Open the dashboard to see everything", DASH_LINK, tag="more" + sid(label),
                                  short=label, kind="more")]


def toast_xml(a):
    e = lambda s: html.escape(s or "", quote=True)  # noqa: E731
    x = [f'<toast activationType="protocol" launch="{e(a["url"])}"' + (' duration="long"' if a["long"] else "") + ">",
         '<visual><binding template="ToastGeneric">', f"<text>{e(a['title'])}</text>", f"<text>{e(a['line2'])}</text>"]
    if a["line3"]:
        x.append(f"<text>{e(a['line3'])}</text>")
    if a.get("img"):
        x.append(f'<image placement="appLogoOverride" hint-crop="circle" src="{e(a["img"])}"/>')
    x.append('<text placement="attribution">Trend Radar</text></binding></visual><actions>')
    for label, url in a["actions"][:5]:
        x.append(f'<action content="{e(label)}" activationType="protocol" arguments="{e(url)}"/>')
    x.append('</actions><audio src="ms-winsoundevent:Notification.Default"/></toast>')
    return "".join(x)


def show_toasts(alerts):
    """One PowerShell call shows all Windows notifications of this check."""
    if not alerts or not IS_WIN:   # in the cloud there is no screen: phone only
        return True
    lines = [
        "$ErrorActionPreference = 'Stop'",
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null",
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null",
        f"$n = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('{APP_ID}')",
    ]
    for a in alerts:
        b64 = base64.b64encode(toast_xml(a).encode("utf-8")).decode()
        lines.append(
            "$d = New-Object Windows.Data.Xml.Dom.XmlDocument; "
            f"$d.LoadXml([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{b64}'))); "
            "$t = New-Object Windows.UI.Notifications.ToastNotification $d; "
            f"$t.Tag = '{re.sub(r'[^A-Za-z0-9]', '', a['tag'])[:16] or 'x'}'; $t.Group = 'trends'; $n.Show($t); "
            "Start-Sleep -Milliseconds 500")
    ps1 = DATA / "toast.ps1"
    ps1.write_text("\n".join(lines), encoding="ascii")
    try:
        r = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
                           capture_output=True, text=True, timeout=120, creationflags=NO_WINDOW)
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"toast error: {e}")
        return False
    if r.returncode != 0:
        log(f"toast error: {r.stderr.strip()[:400]}")
        return False
    return True


def push_remote(alerts, cfg, force=False):
    """Phone / chat notifications: ntfy (default), Telegram and Discord if configured.
    When the cloud copy runs 24/7 it sends to the phone, so the PC can be told not to (no doubles)."""
    if not CLOUD and not force and cfg.get("phone_push_from_pc", True) is False:
        return 0
    topic = (cfg.get("ntfy_topic") or "").strip()
    server = (cfg.get("ntfy_server") or "https://ntfy.sh").rstrip("/")
    online = (cfg.get("online_dashboard") or "").strip()
    tg_token, tg_chat = cfg.get("telegram_bot_token"), cfg.get("telegram_chat_id")
    discord = cfg.get("discord_webhook")
    sent = 0
    for a in alerts:
        msg = a.get("push_text") or "\n".join(x for x in (a["line2"], a["line3"]) if x) or " "
        url = a["url"] if a["url"].startswith("http") else online
        try:
            for ch in (channels_for(a, cfg) if topic and cfg.get("phone_channels", True) else [""]):
                if not topic:
                    break
                dash = online + CHANNEL_HASH.get(ch, "") if online else ""
                body = {"topic": topic + ch, "title": a["title"][:250], "message": msg[:3800], "priority": a["priority"]}
                # flags in front of the title + the category as a small label
                tags = [FLAG_TAG[c] for c in a.get("countries") or [] if c in FLAG_TAG][:4]
                if a.get("category") and a["category"] != "General":
                    tags.append(a["category"])
                if a.get("label"):
                    tags.append(a["label"])     # HOT, BREAKING, REPEATING... (the desktop app filters on these)
                if tags:
                    body["tags"] = tags
                click = url if a["url"].startswith("http") else dash
                if click:
                    body["click"] = click
                acts = []
                for label, u in a["actions"]:
                    u = dash if u.startswith(PROTO + "://") else u
                    if u.startswith("http") and len(acts) < 3 and all(x["label"] != label for x in acts):
                        acts.append({"action": "view", "label": label, "url": u, "clear": True})
                if dash and len(acts) < 3 and all(x["label"] != "Dashboard" for x in acts):
                    acts.append({"action": "view", "label": "Dashboard", "url": dash, "clear": True})
                if acts:
                    body["actions"] = acts
                if (a.get("pic_url") or "").startswith("http"):
                    body["attach"] = a["pic_url"]       # the news picture shows in the notification
                    body["filename"] = "trend.jpg"
                if online:
                    body["icon"] = online.rstrip("/") + "/icon.png"
                post_json(server, body)
                sent += 1
            if tg_token and tg_chat:
                data = urllib.parse.urlencode({"chat_id": tg_chat, "text": f"{a['title']}\n{msg}\n{url}"[:4000],
                                               "disable_web_page_preview": "true"}).encode()
                urllib.request.urlopen(urllib.request.Request(
                    f"https://api.telegram.org/bot{tg_token}/sendMessage", data=data), timeout=15).read()
            if discord:
                post_json(discord, {"content": f"**{a['title']}**\n{msg}\n{url}"[:1900]})
        except Exception as e:  # noqa: BLE001
            log(f"push error: {type(e).__name__}: {str(e)[:150]}")
    return sent


def deliver(alerts, state, cfg, now, dry):
    if not alerts:
        return
    if dry:
        for a in alerts:
            log(f"[would notify] {a['title']} | {a['line2'][:90]}")
        return
    show_toasts([a for a in alerts if not a.get("phone_only")])
    push_remote([a for a in alerts if a["kind"] != "more"], cfg)
    hist = state.setdefault("alert_log", [])
    for a in (a for a in alerts if not a.get("phone_only")):
        hist.append({"at": now.isoformat(), "title": a["title"], "url": a["url"], "kind": a["kind"]})
    state["alert_log"] = hist[-150:]
    log(f"notified {len(alerts)}: " + " | ".join(a["title"] for a in alerts))


def mark_topics(sent, now):
    for t, reason in sent:
        rec = t["rec"]
        rec["notified_tier"] = max(rec["notified_tier"], t["tier"], 1 if reason in ("breaking", "justin") else 0)
        rec["notified_at"] = now.isoformat()
        rec["notified_countries"] = sorted(set(rec.get("notified_countries", [])) | {c for c in t["countries"] if c in FOCUS})
        if reason == "breaking":
            rec["breaking_sent"] = True
        if reason == "justin":
            rec["justin_sent"] = True
        rec["repeat_day"] = max(rec.get("repeat_day", 1), t.get("days_seen", 1))

# --------------------------------------------------------------------------- dashboard

SITES = [
    ["Trends - search & social", [
        ["Google Trends - Trending now", "https://trends.google.com/trending?geo=US", "Live search trends per country (change geo=US to geo=DE). Number 1 source."],
        ["Google Trends - Explore", "https://trends.google.com/trends/explore?date=now%207-d&geo=US", "Is a topic still rising or already dying? Compare 2-5 topics."],
        ["trends24.in", "https://trends24.in/united-states/", "X / Twitter trends hour by hour - USA, Germany, UK..."],
        ["GetDayTrends", "https://getdaytrends.com/united-states/", "X trends with tweet volume and how long they lasted."],
        ["TikTok Creative Center", "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en", "Trending hashtags, songs, creators and videos per country (US, DE)."],
        ["Exploding Topics", "https://explodingtopics.com/", "Topics growing over weeks and months - long trends."],
        ["Reddit r/popular", "https://www.reddit.com/r/popular/", "What the internet is talking about right now (US)."],
        ["Know Your Meme", "https://knowyourmeme.com/", "Origin and meaning of memes and viral formats."],
        ["Wikipedia Topviews", "https://pageviews.wmcloud.org/topviews/?project=en.wikipedia.org&platform=all-access&date=yesterday", "Most read articles (change to de.wikipedia.org for Germany)."],
        ["GDELT", "https://www.gdeltproject.org/", "World news monitor, 100+ languages, updated every 15 minutes."],
        ["Talkwalker Alerts", "https://www.talkwalker.com/alerts", "Free alerts for any keyword (web, news, X). Gives an RSS link you can add to config.json."],
    ]],
    ["Breaking news - USA", [
        ["AP News", "https://apnews.com/", "Fast and neutral. Good to check facts."],
        ["Reuters", "https://www.reuters.com/", "World, politics, business."],
        ["BNO News", "https://bnonews.com/", "Very fast breaking alerts."],
        ["Google News US", "https://news.google.com/?hl=en-US&gl=US&ceid=US:en", "All the top stories in one place."],
        ["NPR", "https://www.npr.org/", "Public radio - reliable."],
        ["Axios", "https://www.axios.com/", "Short, clear: why it matters."],
        ["CNN / NBC / Fox", "https://www.cnn.com/", "Big US TV networks - see both sides (fox: foxnews.com)."],
    ]],
    ["Breaking news - Germany & Europe", [
        ["tagesschau.de", "https://www.tagesschau.de/", "German public news, Eilmeldungen."],
        ["ZDFheute", "https://www.zdf.de/nachrichten", "Public TV news."],
        ["Deutsche Welle", "https://www.dw.com/de/", "German international broadcaster (also English)."],
        ["SPIEGEL", "https://www.spiegel.de/", "Politics, society, big stories."],
        ["BILD", "https://www.bild.de/", "Tabloid - viral, celebs, emotional topics in DE."],
        ["t-online", "https://www.t-online.de/", "Most read news portal in Germany."],
        ["n-tv", "https://www.n-tv.de/", "Live tickers and breaking news."],
        ["The Local Germany", "https://www.thelocal.de/", "German news explained in English."],
        ["Euronews", "https://www.euronews.com/", "Europe-wide news."],
        ["Politico Europe", "https://www.politico.eu/", "EU politics."],
        ["BBC News", "https://www.bbc.com/news", "UK, Europe, world."],
    ]],
    ["Sports", [
        ["ESPN", "https://www.espn.com/", "NFL, NBA, MLB, NHL, UFC - scores, news, schedules."],
        ["NFL.com", "https://www.nfl.com/", "Official NFL, Super Bowl."],
        ["kicker", "https://www.kicker.de/", "German football, Bundesliga."],
        ["Sportschau", "https://www.sportschau.de/", "German public sports news."],
        ["FlashScore", "https://www.flashscore.com/", "Live scores of everything."],
    ]],
    ["Movies, series, games, music", [
        ["Variety", "https://variety.com/", "Hollywood news, trailers, box office."],
        ["Deadline", "https://deadline.com/", "First to break movie and casting news."],
        ["IMDb release calendar", "https://www.imdb.com/calendar/", "Upcoming movies by date."],
        ["FlixPatrol", "https://flixpatrol.com/", "Netflix / Prime / Disney+ top 10 per country."],
        ["Netflix Top 10", "https://www.netflix.com/tudum/top10", "Official Netflix top 10 per country."],
        ["IGN", "https://www.ign.com/", "Games and pop culture news."],
        ["Spotify Charts", "https://charts.spotify.com/", "Top and viral songs per country."],
        ["YouTube Charts", "https://charts.youtube.com/", "Top songs and music videos per country."],
        ["Box Office Mojo", "https://www.boxofficemojo.com/", "Box office numbers."],
    ]],
    ["Tech, business, stocks", [
        ["Yahoo Finance trending", "https://finance.yahoo.com/markets/stocks/trending/", "Stocks everyone is looking at (Tesla, Nvidia...)."],
        ["The Verge", "https://www.theverge.com/", "Tech news, Apple / Tesla / AI."],
        ["TechCrunch", "https://techcrunch.com/", "Startups and AI."],
        ["Hacker News", "https://news.ycombinator.com/", "What tech people share right now."],
        ["Electrek", "https://electrek.co/", "Tesla and electric cars."],
    ]],
    ["Events & calendars", [
        ["timeanddate - US holidays", "https://www.timeanddate.com/holidays/us/", "All US holidays and special days."],
        ["timeanddate - DE holidays", "https://www.timeanddate.com/holidays/germany/", "German holidays and special days."],
        ["Eventim", "https://www.eventim.de/", "Concerts and shows in Germany."],
        ["Ticketmaster", "https://www.ticketmaster.com/", "Concerts and shows in the US."],
    ]],
]


def topic_json(t):
    news, seen = [], set()
    for h in sorted(t["heads"], key=lambda h: (h["kind"] != "news", not h.get("recent"), h["rank"])):
        if h["term"] in seen:
            continue
        seen.add(h["term"])
        news.append({"t": h["term"], "u": h["url"], "s": h.get("outlet") or h["source"], "c": h["country"],
                     "r": bool(h.get("recent")), "a": h["age_h"] if h.get("age_h", 9999) < 9999 else None})
        if len(news) >= 8:
            break
    rel = []
    for m in t["members"]:
        lab = m["display"]
        if lab != t["name"] and lab not in rel:
            rel.append(lab)
    return {"id": t["id"], "name": t["name"], "score": t["score"], "tier": t["tier"], "story": t["story"],
            "watch": t["watch"], "category": t["category"], "countries": t["countries"], "kinds": t["kinds"],
            "summary": summary_line(t), "context": t["context"] if not t["story"] else "", "url": t["url"],
            "pic": t["picture"], "age_h": t["age_h"], "hours_seen": t["hours_seen"], "days_seen": t["days_seen"],
            "rising": t["rising"], "theme": t["theme"], "related": rel[:10], "news": news,
            "links": research_links(t), "breaking": bool(t["breaking"]), "recent": t["recent"],
            "first_pub_h": t["first_pub_h"], "last_pub_h": t["last_pub_h"], "recent1": t["recent1"],
            "recent1_outlets": t["recent1_outlets"], "just_in": t["just_in"],
            "parts": {k: round(v, 1) for k, v in t["parts"].items() if v}}


def headlines_by_country(signals, topics):
    owner = {}
    for t in topics:
        if not t["story"]:
            for h in t["heads"]:
                owner.setdefault(id(h), t["name"])
    out = {}
    for s in signals:
        if s["kind"] != "news" or s.get("from_gt"):
            continue
        keep = ((s["source"] == "Google News" and s["rank"] <= 12) or (s.get("section") and s["rank"] <= 8)
                or (s["source"] in TOP_FEEDS and s["rank"] <= 8))
        if keep:
            out.setdefault(s["country"], []).append({
                "t": s["term"], "u": s["url"], "s": s.get("outlet") or s["source"], "src": s["source"],
                "cat": s.get("cat") or "Top stories", "r": s["rank"], "cov": s.get("coverage", 1),
                "trend": owner.get(id(s)), "b": bool(s.get("breaking")),
                "a": s["age_h"] if s.get("age_h", 9999) < 9999 else None})
    for v in out.values():
        v.sort(key=lambda h: (h["cat"] != "Top stories", h["cat"], h["src"] != "Google News", h["r"]))
    return out


def charts_json(signals):
    music = {}
    for s in sorted((s for s in signals if s["kind"] == "music"), key=lambda s: s["rank"]):
        music.setdefault(s["country"], []).append({"r": s["rank"], "song": s["song"], "artist": s["artist"],
                                                   "u": s["url"], "art": s["art"]})
    stocks = [{"r": s["rank"], "sym": s["symbol"], "name": s["display"] if s["known"] else "", "u": s["url"]}
              for s in sorted((s for s in signals if s["kind"] == "finance"), key=lambda s: s["rank"])]
    movies = [{"r": s["rank"], "t": s["term"], "u": s["url"], "art": s["art"], "g": s.get("genre", "")}
              for s in sorted((s for s in signals if s["kind"] == "movie_chart"), key=lambda s: s["rank"])]
    hn = [{"r": s["rank"], "t": s["term"], "u": s["url"], "p": s.get("points", 0)}
          for s in sorted((s for s in signals if s["source"] == "Hacker News"), key=lambda s: s["rank"])][:15]
    yt = {}
    for s in sorted((s for s in signals if s["kind"] == "youtube"), key=lambda s: s["rank"]):
        yt.setdefault(s["country"], []).append({"r": s["rank"], "t": s["term"], "u": s["url"], "ch": s["outlet"],
                                                "v": s["views"], "art": s["art"]})
    return {"music": music, "stocks": stocks, "movies": movies, "hn": hn, "youtube": yt}


def sports_json(games, now):
    out = []
    for g in games:
        h = hours_since(parse_date(g["date"]), now)
        if g["state"] == "in" or (g["state"] == "pre" and h > -24 * 4) or (g["state"] == "post" and h < 30):
            out.append({"league": g["league"], "c": g["country"], "name": g["term"], "txt": g.get("score_text", g["term"]),
                        "date": g["date"], "state": g["state"], "detail": g["detail"], "notes": g["notes"],
                        "big": g.get("big"), "u": g["url"]})
    order = {"in": 0, "pre": 1, "post": 2}
    out.sort(key=lambda g: (order.get(g["state"], 3), g["date"] if g["state"] != "post" else "", g["league"]))
    return out[:160]


def render_dashboard(topics, health, events, cfg, now, signals, watch_summary, games, state):
    tpl = (ROOT / "dashboard_template.html").read_text(encoding="utf-8")
    data = {
        "generated": now.isoformat(), "every": cfg["check_every_minutes"],
        "topics": [topic_json(t) for t in topics[:160]],
        "headlines": headlines_by_country(signals, topics), "watch": watch_summary,
        "sports": sports_json(games, now), "charts": charts_json(signals),
        "events": events, "sources": health, "sites": SITES, "alerts": list(reversed(state.get("alert_log", [])))[:60],
        "hot": cfg["hot_score"], "trend": cfg["trend_score"],
        "ntfy": "" if CLOUD else cfg.get("ntfy_topic", ""),   # the public online dashboard never shows the secret topic
        "briefing": state.get("briefing"), "cloud": CLOUD, "online_url": cfg.get("online_dashboard", ""),
        "disasters": state.get("disaster_data") or {},
        "ai": {"models": state.get("ai_data") or {}, "tools": load_json(ROOT / "ai_tools.json", {}).get("groups", [])},
        "catchup": state.get("catchup") if hours_since((state.get("catchup") or {}).get("at"), now) < 12 else None,
    }
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    tmp = DASHBOARD.with_suffix(".tmp")
    tmp.write_text(tpl.replace("/*__DATA__*/null", blob), encoding="utf-8")
    os.replace(tmp, DASHBOARD)

# --------------------------------------------------------------------------- main


SECRET_ENV = {"NTFY_TOPIC": "ntfy_topic", "TELEGRAM_BOT_TOKEN": "telegram_bot_token",
              "TELEGRAM_CHAT_ID": "telegram_chat_id", "DISCORD_WEBHOOK": "discord_webhook",
              "YOUTUBE_API_KEY": "youtube_api_key"}


def load_config():
    """config.json (shared, also on GitHub) + config.local.json (this PC only: secrets) + env (cloud secrets)."""
    cfg = load_json(ROOT / "config.json", {})
    cfg.update({k: v for k, v in load_json(ROOT / "config.local.json", {}).items() if not k.startswith("_")})
    for env, key in SECRET_ENV.items():
        if os.environ.get(env):
            cfg[key] = os.environ[env].strip()
    defaults = {"hot_score": 16, "trend_score": 9, "story_score": 9, "max_toasts_per_run": 4, "max_extra_toasts": 4,
                "renotify_hours": 4, "check_every_minutes": 15, "digest_hours": 3, "google_trends_geos": [],
                "x_trends_countries": {}, "google_news": {}}
    for k, v in defaults.items():
        cfg.setdefault(k, v)
    return cfg


def export_latest(topics, signals, watch_summary, games, events, now):
    """Small, clean snapshot of what is trending (read by the Claude briefing routine)."""
    def item(t):
        j = topic_json(t)
        return {k: j[k] for k in ("name", "category", "tier", "score", "story", "countries", "summary", "context",
                                  "url", "first_pub_h", "last_pub_h", "recent1", "just_in", "hours_seen", "days_seen",
                                  "watch", "related")} | {"news": j["news"][:5]}
    today = now.date().isoformat()
    soon = (now.date() + timedelta(days=14)).isoformat()
    heads = {c: v[:8] for c, v in headlines_by_country(signals, topics).items()}
    data = {
        "generated": now.isoformat(),
        "trends": [item(t) for t in topics if not t["story"]][:30],
        "stories": [item(t) for t in topics if t["story"]][:10],
        "headlines_by_country": heads,
        "watchlist": {k: {"today": v["n24"], "last_2h": v["n2"], "top": v["items"][:3]} for k, v in (watch_summary or {}).items()},
        "big_games": [g for g in sports_json(games, now) if g.get("big")][:20],
        "events_next_14_days": [e for e in events if today <= e.get("date", "") <= soon],
    }
    DATA.mkdir(exist_ok=True)
    LATEST_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def src_briefing(url):
    try:
        txt = fetch(url, timeout=15).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:   # Claude has not written a briefing yet
            return []
        raise
    return [{"kind": "briefing", "source": "Claude briefing", "country": "", "term": "briefing", "text": txt, "rank": 1}]


def briefing_alert(signals, state, now):
    """The Claude routine writes briefing.md twice a day; send each new one once (phone + dashboard)."""
    b = next((s for s in signals if s["kind"] == "briefing"), None)
    if not b or not b["text"].strip():
        return None
    text = b["text"].strip()
    h = sid(text)
    first = next((ln.strip("# ").strip() for ln in text.splitlines() if ln.strip()), "Briefing")
    state["briefing"] = {"text": text[:20000], "title": first, "seen": state.get("briefing", {}).get("seen") if
                         state.get("briefing", {}).get("hash") == h else now.isoformat(), "hash": h}
    if state.get("briefing_sent") == h:
        return None
    state["briefing_sent"] = h
    body = [ln.strip() for ln in text.splitlines()[1:] if ln.strip()]
    a = mk_alert("\U0001F9E0 " + first[:110], " · ".join(re.sub(r"^[#*\-\d. ]+", "", ln) for ln in body[:2])[:180],
                 "Full briefing: dashboard > Ideas", DASH_LINK, tag="brief" + h[:8], priority=3, short="briefing",
                 kind="briefing")
    # phone: plain lines (no markdown symbols)
    clean = [re.sub(r"\*\*|__|`", "", re.sub(r"^#+\s*", "", ln)) for ln in body]
    a["push_text"] = "\n".join(clean)[:3800]
    a["category"] = "Briefing"
    return a


def acquire_lock():
    DATA.mkdir(exist_ok=True)
    try:
        if LOCK_FILE.exists() and time.time() - LOCK_FILE.stat().st_mtime > 600:
            LOCK_FILE.unlink()
        fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False


def run_check(dry=False, report=False, sim_gap=None, preview=False):
    if not acquire_lock():
        log("another check is running - skip")
        return
    try:
        cfg = load_config()
        global FOCUS
        FOCUS = tuple(cfg.get("focus_countries") or FOCUS)
        state = load_json(STATE_FILE, {})
        now = datetime.now().astimezone()
        t0 = time.time()
        quiet = in_quiet_hours(cfg, now)
        # was the PC off / asleep since the last good check? -> catch-up mode
        last_ok = state.get("last_ok_run") or state.get("last_run")
        if sim_gap:  # testing only: pretend the PC was off for sim_gap hours
            last_ok = (now - timedelta(hours=sim_gap)).isoformat()
        gap_h = hours_since(last_ok, now) if last_ok else 0.0
        catchup = bool(last_ok) and gap_h >= cfg.get("catchup_after_hours", 1.5)
        since_utc = datetime.fromisoformat(last_ok).astimezone(timezone.utc).isoformat() if catchup else None
        signals, health = collect(cfg, state, gap_h if catchup else 0.0)
        n_ok = sum(h["ok"] for h in health)
        if n_ok < max(3, 0.3 * len(health)):
            # just switched on and no internet yet: send nothing, the next check does the catch-up
            log(f"no internet yet? only {n_ok}/{len(health)} sources answered - waiting for the next check")
            if not dry:
                save_json(STATE_FILE, state)
            return
        if catchup:
            log(f"PC was off or asleep for {gap_h:.1f}h -> 'while you were away' summary")
        topics = build_topics(signals, cfg, now)
        topics.sort(key=lambda t: -t["base"])
        gdelt_boost(topics, state, cfg, health)
        update_state(topics, state, now)
        topics.sort(key=lambda t: -t["score"])

        queue, also = plan_topic_alerts(topics, cfg, now)
        if preview:  # --test: show how a real notification looks (top trend right now), save nothing
            top = next((t for t in topics if not t["story"]), None)
            if top:
                a = topic_alert(top, "new")
                ok = show_toasts([a])
                pushed = push_remote([a], cfg, force=True)
                log(f"test sent: {a['title']} (PC: {'ok' if ok else 'FAILED'}, phone pushes: {pushed})")
            return
        n = cfg["max_toasts_per_run"]
        topic_alerts = fold([topic_alert(t, r, rel) for t, r, rel in queue[:n]] +
                            [mk_alert("", short=t["name"]) for t, r, rel in queue[n:]], n, "\U0001F4CA Trends")
        w_alerts, watch_summary = watch_alerts(signals, topics, state, cfg, now, quiet, since=since_utc)
        s_alerts, games = sports_alerts(signals, state, cfg, now, quiet, window_h=(gap_h + 4) if catchup else 15)
        m_alerts = music_alerts(signals, state, cfg, now, quiet)
        events = sorted(load_json(ROOT / "events.json", {}).get("events", []), key=lambda e: e.get("date", ""))
        e_alerts = event_alerts(events, state, cfg, now, quiet)
        d_alerts, dis_data = disaster_alerts(signals, state, cfg, now, quiet)
        ai_new, ai_data = ai_alerts(signals, state, cfg, now, quiet)
        e_alerts = ai_new + e_alerts
        d_alerts = fold(d_alerts, (cfg.get("disasters") or {}).get("max_toasts", 3), "\U0001F30D Disasters")
        if catchup:
            alerts = d_alerts + catchup_alerts(topics, queue, s_alerts, w_alerts, m_alerts, e_alerts, state, now, gap_h, last_ok)
            state["last_digest"] = now.isoformat()
        else:
            extras = fold(w_alerts + fold(s_alerts, cfg.get("max_sports_toasts", 2), "\U0001F3C6 Results") + m_alerts
                          + e_alerts, cfg["max_extra_toasts"], "\u2B50 Updates")
            dg = digest_alert(topics, state, cfg, now, quiet)
            alerts = d_alerts + topic_alerts + extras + (dg if dg else [])
        br = briefing_alert(signals, state, now)
        if br:
            alerts.append(br)
        deliver(alerts, state, cfg, now, dry)
        if not dry:
            mark_topics([(t, r) for t, r, _ in queue] + also, now)

        state["disaster_data"] = dis_data
        state["ai_data"] = ai_data
        render_dashboard(topics, health, events, cfg, now, signals, watch_summary, games, state)
        export_latest(topics, signals, watch_summary, games, events, now)
        state["last_run"] = state["last_ok_run"] = now.isoformat()
        if not dry:
            save_json(STATE_FILE, state)
        ok = sum(h["ok"] for h in health)
        log(f"check done in {time.time() - t0:.1f}s: {len(signals)} signals, {len(topics)} topics, "
            f"{ok}/{len(health)} sources ok, {len(alerts)} notifications")
        if report:
            bad = [h for h in health if not h["ok"]]
            if bad:
                print("FAILED SOURCES: " + "; ".join(f"{h['name']} ({h['err']})" for h in bad))
            for i, t in enumerate(topics[:40], 1):
                parts = " ".join(f"{k}={v:.1f}" for k, v in t["parts"].items() if v)
                star = " *" + t["watch"] if t["watch"] else ""
                print(f"{i:2}. [{t['score']:5.1f}] T{t['tier']} {'STORY ' if t['story'] else ''}"
                      f"{'BREAKING ' if t['breaking'] else ''}{t['name'][:70]}{star}\n      {summary_line(t)}\n      {parts}")
    finally:
        try:
            LOCK_FILE.unlink()
        except OSError:
            pass


def open_dashboard():
    if not DASHBOARD.exists():
        run_check()
    os.startfile(str(DASHBOARD))  # noqa: S606 - local file in our own folder


def make_icon():
    """Radar icon: icon.png (256), icon-512.png (phone home screen) and icon.ico (desktop)."""
    png = _radar_png(256)
    (ROOT / "icon.png").write_bytes(png)
    (ROOT / "icon-512.png").write_bytes(_radar_png(512))
    ico = struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(png), 22) + png
    (ROOT / "icon.ico").write_bytes(ico)


def _radar_png(size):
    k = 256 / size   # draw in a 256x256 space, at any size
    rows = []
    cx = cy = 128
    for py in range(size):
        row = bytearray([0])
        for px in range(size):
            x, y = (px + 0.5) * k - 0.5, (py + 0.5) * k - 0.5
            dx, dy = x - cx + 0.5, y - cy + 0.5
            r = math.hypot(dx, dy)
            a, col = 0, (0, 0, 0)
            if r < 124:
                a, col = 255, (15, 23, 42)
                sweep = ((math.degrees(math.atan2(dy, dx)) + 360) % 360 - 230) % 360
                if sweep < 70 and r < 112:
                    fade = 1 - sweep / 70
                    col = tuple(int(c0 + (c1 - c0) * fade * 0.85) for c0, c1 in zip(col, (255, 77, 77)))
                for ring in (36, 74, 112):
                    if abs(r - ring) < 3:
                        col = (255, 120, 80)
                if math.hypot(x - 170, y - 92) < 13 or math.hypot(x - 96, y - 168) < 9:
                    col = (255, 214, 102)
                if r < 9:
                    col = (255, 255, 255)
            elif r < 126:
                a, col = int(255 * (126 - r) / 2), (15, 23, 42)
            row += bytes(col) + bytes([a])
        rows.append(bytes(row))

    def chunk(tag, body):
        return struct.pack(">I", len(body)) + tag + body + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


def test_alert():
    cfg = load_config()
    icon = ROOT / "icon.png"
    a = mk_alert("\U0001F525 HOT: Trend Radar works!", "US DE · Google 20K+ · X #1 for 12h · 8 news sites",
                 "This is how a trend notification looks. Click it to open the dashboard.", DASH_LINK,
                 img=icon.as_uri() if icon.exists() else None, tag="test", priority=3, kind="test")
    ok = show_toasts([a])
    pushed = push_remote([dict(a, url="https://trends.google.com/trending?geo=US")], cfg, force=True)
    log(("test notification sent" if ok else "test notification FAILED") + f" (phone pushes: {pushed})")


def main():
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Trend Radar")
    ap.add_argument("--report", action="store_true", help="check without notifications and print ranking")
    ap.add_argument("--open", action="store_true", help="check, then open the dashboard")
    ap.add_argument("--show", action="store_true", help="open the dashboard")
    ap.add_argument("--test", action="store_true", help="send a test notification")
    ap.add_argument("--make-icon", action="store_true")
    ap.add_argument("--handle", help="trendradar:// link from a notification")
    ap.add_argument("--simulate-gap", type=float, help=argparse.SUPPRESS)
    a = ap.parse_args()
    try:
        if a.make_icon:
            make_icon()
        elif a.test:
            run_check(dry=True, preview=True)
        elif a.handle:
            if "refresh" in a.handle:
                run_check()
            open_dashboard()
        elif a.show:
            open_dashboard()
        else:
            run_check(dry=a.report or bool(a.simulate_gap), report=a.report, sim_gap=a.simulate_gap)
            if a.open:
                open_dashboard()
    except Exception:  # noqa: BLE001
        log("CRASH\n" + traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
