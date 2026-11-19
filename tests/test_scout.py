# -*- coding: utf-8 -*-
"""External same-type references (bin/scout.py): search terms, hashtags, same-type reasons, filters and relaxing, scoring,
de-dup, the cache never keeping an empty answer, purge deleting media only, the similarity check. No network: yt-dlp is stubbed.

    python3 -m unittest tests.test_scout
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "bin"))
import scout as S  # noqa: E402


def cand(i, title, views=50000, subs=20000, dur=45, vertical=True, chan=None, date="20260901", tags=()):
    return {"id": f"yt:{i}", "來源": "test", "網址": f"https://www.youtube.com/shorts/{i:011d}", "平台": "YouTube", "標題": title, "頻道": chan or f"ch{i}",
            "頻道網址": f"https://www.youtube.com/@ch{i}", "片長": dur, "發佈日": date, "觀看": views, "訂閱": subs, "直式": vertical, "縮圖": "",
            "描述": "", "標籤": list(tags), "搜尋詞": ["q"], "狀態": "未看"}


class Terms(unittest.TestCase):
    def test_platform_words_dropped_and_shorts_added(self):
        q = S.make_queries("S&P 500 index fund explained Reels", "reels", None)
        self.assertEqual(len(q), 1)
        self.assertNotIn("Reels", q[0])
        self.assertTrue(q[0].endswith("shorts"))

    def test_hashtags_from_queries(self):
        tags = S.hashtags(["index fund explained", "bali villa tour"], ["investing"])
        self.assertIn("investing", tags)
        self.assertIn("indexfund", tags)
        self.assertIn("balivillatour", tags)
        self.assertNotIn("explained", "".join(t for t in tags if t == "explained"))

    def test_platform_guess(self):
        self.assertEqual(S.platform_of("峇里島 Reels 宣傳", None), "reels")
        self.assertEqual(S.platform_of("anything", "long"), "long")


class SameType(unittest.TestCase):
    def test_topic_is_required(self):
        topic = S.tokens("index fund compound interest") - S.GENERIC
        meme = cand(1, "Only real traders feel this one #animation", tags=["animation"])
        good = cand(2, "Index fund explained with compound interest #animation", tags=["animation"])
        self.assertFalse(any(w.startswith("主題相近") for w in S.same_type(meme, "index fund", "文字動態", "reels", topic)))
        why = S.same_type(good, "index fund", "文字動態", "reels", topic)
        self.assertTrue(any(w.startswith("主題相近") for w in why))
        self.assertGreaterEqual(len(why), 2)

    def test_no_form_word_is_not_evidence(self):
        c = cand(3, "index fund money", tags=[])
        self.assertFalse(any(w.startswith("形式相近") for w in S.same_type(c, "index fund", "文字動態", "reels", {"index", "fund"})))


class Filters(unittest.TestCase):
    level = {"長度倍數": [0.4, 1.6], "最舊月數": 18, "直式": True, "最低觀看": None}

    def test_hard_filter(self):
        self.assertTrue(S.hard_ok(cand(1, "x"), "reels", self.level))
        self.assertFalse(S.hard_ok(cand(2, "x", dur=600), "reels", self.level))
        self.assertFalse(S.hard_ok(cand(3, "x", vertical=False), "reels", self.level))
        self.assertFalse(S.hard_ok(cand(4, "x", views=10), "reels", self.level))
        self.assertTrue(S.hard_ok(cand(5, "x", views=2000), "reels", {**self.level, "最低觀看": 1000}))

    def test_feasibility(self):
        self.assertEqual(S.feasibility(cand(1, "Official Music Video")), "做不到")
        self.assertEqual(S.feasibility(cand(2, "Cinematic drone tour")), "勉強")
        self.assertEqual(S.feasibility(cand(3, "Index funds in 40 seconds")), "可行")


class Scoring(unittest.TestCase):
    def test_outlier_beats_raw_views(self):
        big = cand(1, "x", views=2_000_000, subs=5_000_000); big["離群倍數"] = 0.8
        small = cand(2, "x", views=30_000, subs=5_000); small["離群倍數"] = 6.0
        self.assertGreater(S.effectiveness(small), S.effectiveness(big))

    def test_tiny_channel_ratio_ignored(self):
        tiny = cand(3, "x", views=5000, subs=20)   # views/subs 250 but the channel is too small to mean anything
        self.assertLess(S.effectiveness(tiny), 0.5)

    def test_ad_run_days(self):
        ad = cand(4, "x"); ad["投放天數"] = 45
        self.assertEqual(S.effectiveness(ad), 1.0)

    def test_score_range(self):
        c = cand(5, "x"); c["同類理由"] = ["a", "b", "c"]; c["可行性"] = "可行"; c["離群倍數"] = 5
        self.assertTrue(0 <= S.score(c) <= 100)


class Cache(unittest.TestCase):
    def test_empty_answer_not_cached(self):
        with tempfile.TemporaryDirectory() as d:
            old = os.environ.get("PB_SCOUT_DIR"); os.environ["PB_SCOUT_DIR"] = d
            try:
                calls = []
                S.cached("t:empty", lambda: calls.append(1) or [])
                S.cached("t:empty", lambda: calls.append(1) or [])
                self.assertEqual(len(calls), 2)
                S.cached("t:full", lambda: calls.append(1) or [1])
                S.cached("t:full", lambda: calls.append(1) or [1])
                self.assertEqual(len(calls), 3)
            finally:
                os.environ.pop("PB_SCOUT_DIR") if old is None else os.environ.__setitem__("PB_SCOUT_DIR", old)


class Purge(unittest.TestCase):
    def test_media_deleted_json_kept(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d); st = out / "study" / "x" / "probe"; st.mkdir(parents=True)
            for f in ["../ref.mp4", "../audio.wav", "shot01.jpg", "shot01_mid.jpg", "cut01_a.jpg", "contact_sheet.jpg", "breakdown.json", "../summary.json"]:
                (st / f).write_text("x")
            th = out / "wall" / "thumbs"; th.mkdir(parents=True); (th / "a.jpg").write_text("x")
            S.purge(out)
            left = sorted(str(p.relative_to(out)) for p in out.rglob("*") if p.is_file())
            self.assertEqual(left, ["purge.log", "study/x/probe/breakdown.json", "study/x/summary.json"])


class Similar(unittest.TestCase):
    def test_ngrams_ignore_ocr_noise(self):
        self.assertEqual(S.ngrams("10 101 1011 1n9e uie see", 6, False), set())
        self.assertTrue(S.ngrams("want to make your own website today", 6, False))

    def test_dhash_and_hamming(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("no PIL")
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.png", Path(d) / "b.png"
            im = Image.new("L", (90, 80)); im.putdata([(x * 3) % 256 for x in range(90 * 80)]); im.save(a); im.save(b)
            self.assertEqual(S.hamming(S.dhash(a), S.dhash(b)), 0)

    def test_corr(self):
        self.assertAlmostEqual(S.corr([1, 2, 3, 4], [2, 4, 6, 8]), 1.0)
        self.assertIsNone(S.corr([1, 2], [1, 2]))
        self.assertIsNone(S.corr([1, 2, 3], [1, 2]))


class Rules(unittest.TestCase):
    def test_rules_complete(self):
        R = S.RULES
        for k in ("平台", "搜尋", "硬過濾", "有效性", "可行性", "同類", "打分", "去重", "半自動來源", "下載", "刪檔", "相似度", "選用工具", "存放"):
            self.assertIn(k, R)
        self.assertAlmostEqual(sum(R["打分"].values()), 1.0)
        self.assertTrue(any("Meta" in s["名稱"] and "負責人" in s["誰看"] for s in R["半自動來源"]))   # Meta is never automated

    def test_pb_has_scout(self):
        import subprocess
        p = subprocess.run([sys.executable, str(REPO / "pb.py"), "--help"], capture_output=True, text=True)
        self.assertIn("scout", p.stdout)


if __name__ == "__main__":
    unittest.main()
