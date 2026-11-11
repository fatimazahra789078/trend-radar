"""Offline tests for Trend Radar (no network). Run:  python -m unittest discover -s tests -v"""
import os
import sys
import unittest
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import trend_radar as tr  # noqa: E402

UTC = timezone.utc


def cfg(**over):
    c = tr.load_config()
    c.update(over)
    return c


class Dates(unittest.TestCase):
    def test_easter(self):
        self.assertEqual(tr.easter_date(2025), date(2025, 4, 20))
        self.assertEqual(tr.easter_date(2026), date(2026, 4, 5))
        self.assertEqual(tr.easter_date(2027), date(2027, 3, 28))

    def test_rules(self):
        d = lambda r: [x.isoformat() for x in tr.season_dates(r, [2026])]
        self.assertEqual(d("fixed:12-25"), ["2026-12-25"])
        self.assertEqual(d("nth:4:3:11"), ["2026-11-26"])          # Thanksgiving
        self.assertEqual(d("nth:4:3:11:+1"), ["2026-11-27"])       # Black Friday
        self.assertEqual(d("nth:-1:0:5"), ["2026-05-25"])          # Memorial Day
        self.assertEqual(d("nth:2:6:5"), ["2026-05-10"])           # Mother's Day US
        self.assertEqual(d("easter:-47"), ["2026-02-17"])          # Mardi Gras
        self.assertEqual(d("advent"), ["2026-11-29"])
        self.assertEqual(d("dates:2026-03-20,2027-03-10"), ["2026-03-20", "2027-03-10"])

    def test_every_season_rule_parses(self):
        evs = tr.load_json(tr.ROOT / "seasons.json", {})["events"]
        self.assertGreater(len(evs), 30)
        for e in evs:
            self.assertTrue(tr.season_dates(e["rule"], [2026, 2027]), e["id"])
            self.assertTrue(e.get("wiki"), e["id"])


class QuietAndBudget(unittest.TestCase):
    # times are given already in the user's zone (quiet_tz=None): the tests do not depend on a tz database
    LOCAL = timezone(timedelta(hours=1))

    def setUp(self):
        self.c = cfg(quiet_hours=[0, 7], quiet_tz=None, alert_budget={"topic": 3})

    def test_quiet_hours(self):
        self.assertTrue(tr.in_quiet_hours(self.c, datetime(2026, 11, 12, 0, 30, tzinfo=self.LOCAL)))
        self.assertTrue(tr.in_quiet_hours(self.c, datetime(2026, 11, 12, 6, 59, tzinfo=self.LOCAL)))
        self.assertFalse(tr.in_quiet_hours(self.c, datetime(2026, 11, 12, 7, 0, tzinfo=self.LOCAL)))
        self.assertFalse(tr.in_quiet_hours(self.c, datetime(2026, 11, 11, 23, 59, tzinfo=self.LOCAL)))
        self.assertTrue(tr.in_quiet_hours(cfg(quiet_hours=[22, 6], quiet_tz=None), datetime(2026, 1, 1, 23, 0, tzinfo=self.LOCAL)))

    def test_time_zone_conversion(self):
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo("Africa/Casablanca")
        except Exception:  # noqa: BLE001
            self.skipTest("no tz database on this computer")
        local = tr.local_now(cfg(quiet_tz="Africa/Casablanca"), datetime(2026, 7, 1, 12, 0, tzinfo=UTC))
        self.assertIn(local.utcoffset(), (timedelta(0), timedelta(hours=1)))   # Morocco: UTC+0 or UTC+1

    def a(self, pr, kind="topic", title="x"):
        return tr.mk_alert(title, "l2", "l3", None, priority=pr, kind=kind)

    def test_budget(self):
        now = datetime(2026, 11, 11, 12, 0, tzinfo=self.LOCAL)
        st = {}
        out = tr.apply_budget([self.a(3, title=f"t{i}") for i in range(5)], st, self.c, now)
        self.assertEqual(len(out), 2)                        # 60 % of 3 reached -> normal ones stop
        out = tr.apply_budget([self.a(4), self.a(4)], st, self.c, now)
        self.assertEqual(len(out), 1)                        # very important until 100 %
        out = tr.apply_budget([self.a(5)], st, self.c, now)
        self.assertEqual(len(out), 1)                        # urgent always passes
        out = tr.apply_budget([self.a(3, kind="disaster")], st, self.c, now)
        self.assertEqual(len(out), 1)                        # no budget for this type

    def test_night_hold_and_morning_summary(self):
        st = {}
        night = datetime(2026, 11, 12, 0, 30, tzinfo=self.LOCAL)
        out = tr.apply_budget([self.a(3, title="A"), self.a(4, title="B"), self.a(5, title="URGENT")], st, self.c, night)
        self.assertEqual([x["title"] for x in out], ["URGENT"])
        self.assertEqual(len(st["night_held"]), 2)
        out = tr.apply_budget([], st, self.c, datetime(2026, 11, 12, 7, 30, tzinfo=self.LOCAL))
        self.assertEqual(len(out), 1)
        self.assertIn("While you slept: 2", out[0]["title"])
        self.assertEqual(st["night_held"], [])


class Channels(unittest.TestCase):
    def test_channels(self):
        c = cfg()
        a = tr.mk_alert("x", priority=4, kind="topic", countries=["US"], category="Politics")
        ch = tr.channels_for(a, c)
        self.assertIn("", ch)
        self.assertIn("-us", ch)
        self.assertIn("-all", ch)
        g = tr.mk_alert("g", priority=3, kind="game", category="Gaming")
        self.assertIn("-games", tr.channels_for(g, c))
        self.assertNotIn("", tr.channels_for(g, c))
        low = tr.mk_alert("w", priority=2, kind="watch", countries=["US"])
        self.assertEqual(tr.channels_for(low, c), ["-all"])

    def test_labels(self):
        self.assertEqual(tr.mk_alert("x", kind="season")["label"], "EVENT")
        self.assertEqual(tr.mk_alert("x", kind="game")["label"], "GAME")
        self.assertEqual(tr.mk_alert("x", kind="github")["label"], "GITHUB")

    def test_push_never_leaks_the_topic_into_links(self):
        sent = []
        orig = tr.post_json
        tr.post_json = lambda url, body, timeout=15: sent.append(body) or 200
        try:
            c = cfg(ntfy_topic="trendradar-secret123", online_dashboard="https://example.org/radar/")
            a = tr.mk_alert("Title", "l2", "l3", None, priority=4, kind="topic", countries=["US"])
            tr.push_remote([a], c, force=True)
        finally:
            tr.post_json = orig
        self.assertTrue(sent)
        for b in sent:
            self.assertTrue(b["topic"].startswith("trendradar-secret123"))
            self.assertNotIn("secret123", b.get("click", ""))
            for act in b.get("actions", []):
                self.assertNotIn("secret123", act["url"])


class GitHubAndGames(unittest.TestCase):
    def test_github_alert_once(self):
        now = datetime.now(UTC)
        c = cfg()
        sig = [{"kind": "gh_repo", "since": "daily", "id": f"o/r{i}", "rank": i, "desc": "An AI video tool", "lang": "Python",
                "stars": 5000, "stars_period": 2000 - i, "url": f"https://github.com/o/r{i}"} for i in range(1, 4)]
        st = {"gh_seen": {"o/old": now.isoformat()}}       # not the first run
        out, data = tr.github_alerts(sig, st, c, now, False)
        self.assertTrue(out)
        self.assertEqual(len(data["daily"]), 3)
        out2, _ = tr.github_alerts(sig, st, c, now, False)
        self.assertEqual(out2, [])                         # never the same repo twice

    def test_games_score_and_first_run_is_silent(self):
        now = datetime.now(UTC)
        c = cfg()
        orig = tr.game_details
        tr.game_details = lambda ids, cc, state, now: {i: {"genres": ["Puzzle"], "mb": 120, "ratings": 1000, "rating": 4.6,
                                                          "released": (now - timedelta(days=20)).strftime("%Y-%m-%d"),
                                                          "desc": "", "shots": []} for i in ids}
        try:
            sig = [{"kind": "game_chart", "cc": "us", "chart": "topfree", "id": "1", "term": "Sort It", "publisher": "Voodoo",
                    "rank": 10, "released": (now - timedelta(days=20)).strftime("%Y-%m-%d"), "icon": "", "url": "u"},
                   {"kind": "game_chart", "cc": "us", "chart": "topfree", "id": "2", "term": "Big Game", "publisher": "Supercell",
                    "rank": 5, "released": "2016-01-01", "icon": "", "url": "u"}]
            st = {}
            out, data = tr.games_alerts(sig, st, c, now, False)
        finally:
            tr.game_details = orig
        self.assertEqual(out, [])                          # first run only learns
        names = [g["name"] for g in data["clone"]]
        self.assertEqual(names[0], "Sort It")              # new + simple + hyper-casual beats a big studio


class Seasons(unittest.TestCase):
    def test_stats_from_a_fake_series(self):
        today = date(2026, 11, 11)
        ev = {"id": "x", "rule": "fixed:12-25", "wiki": "X"}
        prev = date(2025, 12, 25)

        def fake(article, start, end):
            out, d = {}, start
            while d <= end:
                days_before = (prev - d).days
                out[d] = 1000 if 0 <= days_before <= 20 else 100   # searches start 20 days before
                d += timedelta(days=1)
            return out
        orig = tr.wiki_daily
        tr.wiki_daily = fake
        try:
            st = tr.season_stats(ev, today)
        finally:
            tr.wiki_daily = orig
        self.assertEqual(st["next"], "2026-12-25")
        self.assertTrue(18 <= st["lead"] <= 24, st["lead"])
        self.assertEqual(st["peak"], 1000)
        self.assertIn(st["status"], ("prepare", "videos", "soon", "early", "searching"))
        self.assertLessEqual(st["book_by"], "2026-11-10")   # at least 45 days before


if __name__ == "__main__":
    unittest.main()
