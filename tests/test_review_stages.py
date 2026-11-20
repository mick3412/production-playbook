# -*- coding: utf-8 -*-
"""Review points and decision windows (2026-11-20): every review stage builds a pack, one-round stages refuse round 2,
attachments are listed, the decision windows A–E are written into the stages and gates. No network.

    python3 -m pytest tests/test_review_stages.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
R = json.loads((REPO / "data" / "review_checklists.json").read_text(encoding="utf-8"))
ST = json.loads((REPO / "data" / "stages.json").read_text(encoding="utf-8"))


def pb(*args):
    return subprocess.run([sys.executable, str(REPO / "pb.py"), *args], capture_output=True, text=True, cwd=REPO)


class Checklists(unittest.TestCase):
    def test_every_stage_has_round_one_and_a_name(self):
        for k in ("script", "storyboard", "design", "assets", "final", "publish"):
            self.assertIn("名稱", R[k], k)
            self.assertTrue(R[k]["1"]["看"], k)

    def test_script_and_final_have_two_rounds(self):
        for k in ("script", "final"):
            self.assertIn("第一輪每條意見", R[k]["2"]["看"][0])


class Packs(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.txt = self.tmp / "script.md"
        self.txt.write_text("Five dollars of coffee a day.", encoding="utf-8")

    def test_script_pack_lists_the_attachment(self):
        r = pb("review-pack", "--stage", "script", "--files", str(self.txt), "--brief", "test")
        self.assertEqual(r.returncode, 0, r.stderr)
        b = (self.tmp / "review" / "round1_brief.md").read_text(encoding="utf-8")
        self.assertIn(str(self.txt.resolve()), b)
        self.assertIn(R["script"]["1"]["看"][0], b)

    def test_one_round_stage_refuses_round_two(self):
        r = pb("review-pack", "--stage", "publish", "--round", "2", "--files", str(self.txt), "--prev", str(self.txt))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("只有一輪", r.stderr)

    def test_missing_attachment_fails(self):
        r = pb("review-pack", "--stage", "publish", "--files", str(self.tmp / "nope.md"))
        self.assertNotEqual(r.returncode, 0)

    def test_final_pack_uses_frames_from_the_cut(self):
        v = self.tmp / "cut.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=108x192:d=4", "-r", "10", str(v)], check=True)
        r = pb("review-pack", "--stage", "final", "--video", str(v), "--files", str(self.txt), "--out", str(self.tmp / "rv"))
        self.assertEqual(r.returncode, 0, r.stderr)
        b = (self.tmp / "rv" / "round1_brief.md").read_text(encoding="utf-8")
        self.assertIn("成片", b)
        self.assertTrue((self.tmp / "rv" / "round1" / "contact_sheet.jpg").is_file())


class DecisionWindows(unittest.TestCase):
    def test_windows_and_gates(self):
        self.assertEqual(sorted(k[0] for k in ST["decision_windows"]["窗"]), list("ABCDE"))
        gates = {g["id"]: g["text"] for s in ST["stages"] for g in s.get("gates", [])}
        for gid, w in (("G0.5", "A"), ("G2.4", "B"), ("G3.8", "D"), ("G6.7", "E")):
            self.assertIn(f"決策窗 {w}", gates[gid])
        steps = {st["id"]: st["do"] for s in ST["stages"] for st in s["steps"]}
        self.assertIn("review-pack --stage final", steps["6.8"])
        self.assertIn("決策窗 C", steps["2.4"])


if __name__ == "__main__":
    unittest.main()
