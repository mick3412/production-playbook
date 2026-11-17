"""Direction alignment (bin/direction.py): one-axis pairs, picks → card-check parameters, samples pass card-check, 方向卡 feeds storyboard.

    python3 -m unittest tests.test_direction
Skips where the reference corpus (PB_REF_DIR) or its index is missing.
"""
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "bin"))
import direction as D  # noqa: E402

REF = D.ref_dir()
HAS_INDEX = (REF / "direction_index.json").is_file()
PICKS = {"需求": "30 秒數字圖表 Reels", "形式": "文字動態", "二選一": {"節奏": "慢", "動態": "強", "字量": "多", "畫面": "都可以"}, "參考牆": {}}


def pb(*args):
    return subprocess.run([sys.executable, str(REPO / "pb.py"), *args], capture_output=True, text=True, cwd=REPO)


class Mapping(unittest.TestCase):
    def test_rules_only_use_card_check_parameters(self):
        allowed = {"motion", "每鏡秒", "字量", "群組", "visual", "色盤", "tone"}
        for a in D.AXES:
            self.assertEqual(set(a["換算"]), {a["低"], a["高"]}, a["id"])
            for side in a["換算"].values():
                self.assertFalse(set(side) - allowed, a["id"])

    def test_picks_give_the_same_direction_every_time(self):
        self.assertEqual(D.direction_from(PICKS), D.direction_from(json.loads(json.dumps(PICKS))))
        d = D.direction_from(PICKS)
        self.assertEqual(d["motion"]["preset"], "calm")     # 慢
        self.assertEqual(d["motion"]["enter"], "mask")      # 強
        self.assertEqual(d["字量"], "多字")

    def test_an_alternative_changes_what_it_says(self):
        base, alt = D.direction_from(PICKS), D.direction_from(PICKS, ["亮暗"])
        self.assertNotEqual(base["tone"], alt["tone"])       # never picked: the flip must still change something

    def test_sample_cards_pass_card_check(self):
        tmp = Path(tempfile.mkdtemp())
        for i, flip in enumerate([[], ["畫面"], ["色彩", "亮暗"]]):
            card = D.sample_card(D.direction_from(PICKS, flip), "30 年，漲 12.8 倍", ["每月定額；不猜高低點；放 30 年"], None)
            self.assertNotIn("Tickets", json.dumps(card))     # only the user's own words
            f = tmp / f"s{i}.json"; f.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
            r = pb("card-check", str(f))
            self.assertEqual(r.returncode, 0, r.stdout)


@unittest.skipUnless(HAS_INDEX, "reference index not built (pb.py direction index)")
class Pairs(unittest.TestCase):
    def test_each_pair_differs_on_its_axis_and_little_else(self):
        I = D.load_index(REF)
        rng = random.Random(7)
        for ax in D.AXES:
            p = D.pick_pair(I, ax, "文字動態", rng)
            self.assertGreaterEqual(abs(p["目標差z"]), 1.0, ax["id"])
            self.assertLessEqual(len(p["其他還差"]), 2, f"{ax['id']} differs on {p['其他還差']}")
            self.assertEqual({p["左"]["標籤"], p["右"]["標籤"]}, {ax["低"], ax["高"]})

    def test_page_is_local_and_complete(self):
        out = Path(tempfile.mkdtemp())
        r = pb("direction", "page", "30 秒數字圖表 Reels", "--out", str(out))
        self.assertEqual(r.returncode, 0, r.stderr)
        doc = (out / "direction.html").read_text(encoding="utf-8")
        self.assertIn("只在本機開", doc)
        self.assertEqual(doc.count('"軸": '), len(D.AXES))


class DirectionCard(unittest.TestCase):
    def test_choose_writes_a_card_that_storyboard_applies(self):
        out = Path(tempfile.mkdtemp())
        picks = out / "picks.json"; picks.write_text(json.dumps(PICKS, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, str(REPO / "bin" / "direction.py"), "samples", str(picks), "--hook", "30 年，漲 12.8 倍", "--point", "每月定額；不猜高低點", "--no-render"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(pb("direction", "choose", str(picks), "1").returncode, 0)
        d = json.loads((out / "direction.json").read_text(encoding="utf-8"))
        self.assertEqual(d["motion"]["preset"], "calm")
        card = out / "card.json"
        pb("storyboard", "--use", "SB-T10", "--emit", str(card), "--direction", str(out / "direction.json"))
        c = json.loads(card.read_text(encoding="utf-8"))
        self.assertEqual(c["motion"], d["motion"])
        self.assertEqual(c["brand"]["colors"], d["色盤"])
        self.assertEqual(pb("card-check", str(card)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
