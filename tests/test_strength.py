# -*- coding: utf-8 -*-
"""Strong-template grading (bin/scout.py strength): the four signals, the two gates and the grades, on fixed public numbers
measured 2026-11-20 from the owner's reference batch. No network.

    python3 -m pytest tests/test_strength.py
"""
import datetime as dt
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "bin"))
import scout as S  # noqa: E402


def ago(days):
    return (dt.date.today() - dt.timedelta(days=days)).strftime("%Y%m%d")


def vid(title, views, likes, dur=30, days=60, desc="", url="https://www.youtube.com/shorts/x", comments=None):
    return {"title": title, "view_count": views, "like_count": likes, "comment_count": comments, "duration": dur, "upload_date": ago(days),
            "description": desc, "tags": [], "channel": "c", "webpage_url": url}


def prof(n, med, p25, per_day, like_med):
    return {"支數": n, "中位數": med, "P25": p25, "每日中位數": per_day, "讚率中位數": like_med}


class Grades(unittest.TestCase):
    def g(self, v, p):
        return S.grade(v, p, S.signals(v, p))[0]

    def test_stable_channel_is_S(self):   # Zack D. Films: median 6.4M, steady
        self.assertEqual(self.g(vid("The CIA Built A Dragonfly Spy", 11_533_159, 462_220, days=470), prof(30, 6_400_000, 4_000_000, 60_000, 0.03)), "S")

    def test_outlier_with_speed_is_A(self):   # small channel, one idea broke out
        self.assertEqual(self.g(vid("How this Youtuber helped a founder", 5_212_366, 82_487, 24, 44), prof(30, 36_000, 12_000, 800, 0.02)), "A")

    def test_old_outlier_is_A_marked_old(self):   # SMB Capital 2023, 10.7x
        v = vid("How I Made $1,015 in One Day Trading", 150_128, 3_611, 60, 960)
        g, why = S.grade(v, prof(30, 14_000, 7_000, 300, 0.02), S.signals(v, prof(30, 14_000, 7_000, 300, 0.02)))
        self.assertEqual(g, "A"); self.assertIn("舊片", why[0])

    def test_engagement_only_is_B(self):   # Humphrey Yang: like rate 4.9%, not an outlier
        self.assertEqual(self.g(vid("How a REIT Works! Explained.", 379_516, 18_718, 28, 1785), prof(30, 79_000, 40_000, 150, 0.03)), "B")

    def test_repost_excluded(self):
        v = vid("Ricky Gervais Destroyed Hollywood in 30 seconds", 56_292_638, 1_534_242, 28, 70, desc="Credit: @ We respect copyright laws")
        self.assertEqual(self.g(v, prof(30, 78_500, 20_000, 2000, 0.03)), "排除")

    def test_entertainment_clip_excluded(self):
        self.assertEqual(self.g(vid("欧美歌手唱功多恐怖？A妹清唱一开口", 1_012_337, 14_900, 75, 42), prof(30, 8_700, 3_000, 200, 0.015)), "排除")

    def test_long_short_is_graded_and_tagged(self):   # @foxh 107 s news explainer: 9.2x, 5.1x speed
        v = vid("衛星每天看中國港口油桶，再用 AI 判讀", 101_352, 2_331, 107, 15)
        g, why = S.grade(v, prof(30, 11_000, 6_000, 1_300, 0.022), S.signals(v, prof(30, 11_000, 6_000, 1_300, 0.022)))
        self.assertEqual(g, "A"); self.assertIn("長版", why[0])

    def test_over_three_minutes_excluded(self):
        self.assertEqual(self.g(vid("full podcast cut", 2_206_177, 63_587, 240, 195), prof(30, 32_500, 15_000, 300, 0.03)), "排除")

    def test_new_tiny_channel_is_method_reference(self):   # Explain Like I'm Broke: 18 Shorts, 2 days old
        self.assertEqual(self.g(vid("What Is the S&P 500?", 258, 2, 57, 2), prof(18, 1_100, 900, 100, 0.01)), "做法參考")

    def test_instagram_never_S(self):
        v = vid("Video by aiposthub", None, 265, 40, 1, url="https://www.instagram.com/reel/Df60V0HkyQc/")
        self.assertIn(self.g(v, None), ("做法參考", "B"))

    def test_name_colon_title_needs_confirming(self):
        g = self.g(vid("Elon Musk: Money won't Matter in 2036", 5_212_366, 82_487, 24, 44), prof(30, 36_000, 12_000, 800, 0.02))
        self.assertEqual(g, "A（待確認）")

    def test_nothing_reached_is_not_strong(self):
        self.assertEqual(self.g(vid("a normal short", 2_000, 30, 40, 100), prof(30, 1_850, 900, 30, 0.02)), "未達")


class Signals(unittest.TestCase):
    def test_speed_uses_days(self):
        s = S.signals(vid("x", 300_000, 3_000, 30, 30), prof(30, 50_000, 20_000, 1_000, 0.02))
        self.assertEqual(s["每日觀看"], 10_000)
        self.assertEqual(s["速度倍數"], 10.0)
        self.assertTrue(s["C 時間校正速度"])

    def test_percentile(self):
        self.assertEqual(S.pct([1, 2, 3, 4, 5], 0.5), 3)
        self.assertEqual(S.pct([10, 20, 30, 40], 0.25), 17.5)
        self.assertIsNone(S.pct([], 0.5))

    def test_rules_have_strength(self):
        R = S.RULES["強度"]
        for k in ("證據量", "長度", "A 頻道穩定", "B 單支離群", "C 時間校正速度", "D 互動深度", "分級", "搬運"):
            self.assertIn(k, R)


class Library(unittest.TestCase):
    def test_library_cards_valid(self):
        import json
        L = json.loads(S.LIB.read_text(encoding="utf-8"))
        self.assertEqual(S.library_check(L), [])
        self.assertGreaterEqual(len(L["範本"]), 5)

    def test_check_catches_bad_cards(self):
        bad = {"範本": [{"id": "SL-99", "名稱": "x", "家族": "x", "分級": "做法參考", "狀態": "採用", "來源": [], "鉤子": {}, "骨架": [{"段": 1, "作用": "x", "秒數": 3, "版型": "nope"}],
                          "字幕": {}, "動態": [], "聲音": {}, "製作配方": {}, "借": [], "不借": [], "驗證": {}}]}
        errs = " ".join(S.library_check(bad))
        for want in ("分級", "來源", "版型「nope」", "不借", "試做片"):
            self.assertIn(want, errs)


if __name__ == "__main__":
    unittest.main()
