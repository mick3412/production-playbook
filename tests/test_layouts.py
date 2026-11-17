"""The layout catalogue (kits/storyboard/layouts.json), the template → layout references, card-check, and the lower-third fill check.

    python3 -m unittest tests.test_layouts
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LAY = json.loads((REPO / "kits" / "storyboard" / "layouts.json").read_text(encoding="utf-8"))
SB = json.loads((REPO / "data" / "storyboards.json").read_text(encoding="utf-8"))
KIT = (REPO / "kits" / "storyboard" / "text_motion.html").read_text(encoding="utf-8")


def pb(*args):
    return subprocess.run([sys.executable, str(REPO / "pb.py"), *args], capture_output=True, text=True, cwd=REPO)


class LayoutCatalogue(unittest.TestCase):
    def test_every_layout_is_complete_and_exists_in_the_kit(self):
        need = {"id", "名稱", "群組", "角色", "用途", "字區", "欄位", "字級", "動態", "畫面層", "範例", "字量"}
        for x in LAY["版型"]:
            self.assertFalse(need - set(x), x["id"])
            self.assertIn(f"  {x['id']}(beat, b", KIT, f"layout {x['id']} is not in the kit")
            self.assertEqual(x["範例"]["layout"], x["id"])
            z = x["字區"]
            self.assertTrue(0 <= z["x"][0] < z["x"][1] <= 100 and 0 <= z["y"][0] < z["y"][1] <= 100, x["id"])
            for f in x["欄位"]:
                if f["必填"]:
                    self.assertIn(f["欄位"], x["範例"], f"{x['id']} example lacks required {f['欄位']}")

    def test_templates_reference_known_layouts(self):
        ids = {x["id"] for x in LAY["版型"]}
        for t in SB["模板"]:
            for s in t["段落"]:
                self.assertIn(s["版型"], ids, t["id"])
                for a in s.get("可替換", []):
                    self.assertIn(a, ids, t["id"])

    def test_switching_rules_are_published(self):
        R = LAY["換版規則"]
        for k in ("種類上限", "同版型連用上限", "字量固定", "群組換場"):
            self.assertIn(k, R)


class CardCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_every_template_emits_a_card_without_fail(self):
        for t in SB["模板"]:
            card = self.tmp / "c.json"
            p = pb("storyboard", "--use", t["id"], "--emit", str(card))
            self.assertEqual(p.returncode, 0, p.stderr)
            r = pb("card-check", str(card))
            self.assertNotIn("FAIL", r.stdout.split("\n")[0], f"{t['id']}:\n{r.stdout}")

    def test_missing_visual_and_unknown_layout_fail(self):
        card = {"brand": {}, "beats": [{"layout": "statement", "seconds": 3, "text": ["One line"]}, {"layout": "nosuch", "seconds": 2}]}
        f = self.tmp / "bad.json"; f.write_text(json.dumps(card), encoding="utf-8")
        r = pb("card-check", str(f))
        self.assertEqual(r.returncode, 1)
        self.assertIn("畫面層", r.stdout)
        self.assertIn("nosuch", r.stdout)

    def test_layout_outside_the_template_list_fails(self):
        card = {"模板": "SB-T10", "beats": [{"layout": "hook", "seconds": 2, "text": ["Up 12×"], "visual": {"type": "glow"}},
                                          {"layout": "quote", "seconds": 3, "words": [{"text": "a"}, {"text": "b", "key": True}, {"text": "c"}], "visual": {"type": "glow"}}]}
        f = self.tmp / "t.json"; f.write_text(json.dumps(card), encoding="utf-8")
        r = pb("card-check", str(f))
        self.assertIn("對模板", r.stdout)


class MotionSettings(unittest.TestCase):
    def test_kit_presets_match_the_catalogue(self):
        import re
        js = KIT[KIT.index("const MOTION_PRESETS = {"):KIT.index("};", KIT.index("const MOTION_PRESETS = {"))]
        kit = {}
        for name, body in re.findall(r"(\w+):\s*\{([^}]*)\}", js):
            kv = dict(re.findall(r"(\w+):\s*('[^']*'|null|[\d.]+)", body))
            kit[name] = {k: None if v == "null" else v.strip("'") if v.startswith("'") else float(v) for k, v in kv.items()}
        cat = {n: {k: v for k, v in p.items() if k != "適合"} for n, p in LAY["動態設定"]["預設"].items()}
        self.assertEqual(set(kit), set(cat))
        for n in cat:
            for k, v in cat[n].items():
                self.assertEqual(kit[n][k], float(v) if isinstance(v, (int, float)) else v, f"{n}.{k}")

    def test_unknown_preset_and_out_of_range_fail(self):
        tmp = Path(tempfile.mkdtemp())
        card = {"motion": {"preset": "wobbly", "speed": 3}, "beats": [{"layout": "hook", "seconds": 2, "text": ["Up 12×"], "visual": {"type": "glow"},
                                                                        "motion": {"enter": "spin", "transition": "fade"}}]}
        f = tmp / "m.json"; f.write_text(json.dumps(card), encoding="utf-8")
        r = pb("card-check", str(f))
        self.assertEqual(r.returncode, 1)
        for s in ("wobbly", "speed", "spin", "transition 只能寫在整支片"):
            self.assertIn(s, r.stdout)

    def test_valid_motion_passes(self):
        tmp = Path(tempfile.mkdtemp())
        card = {"motion": {"preset": "calm", "speed": 0.9}, "beats": [{"layout": "hook", "seconds": 2, "text": ["Up 12×"], "visual": {"type": "glow"}, "motion": {"preset": "punchy"}}]}
        f = tmp / "m.json"; f.write_text(json.dumps(card), encoding="utf-8")
        r = pb("card-check", str(f))
        self.assertIn("PASS  動態", r.stdout)
        self.assertNotIn("FAIL", r.stdout)


class ReviewPack(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_fail_card_is_not_sent_for_review(self):
        f = self.tmp / "bad.json"; f.write_text(json.dumps({"beats": [{"layout": "nosuch", "seconds": 2}]}), encoding="utf-8")
        r = pb("review-pack", "--card", str(f), "--stills", str(f))
        self.assertEqual(r.returncode, 1)
        self.assertIn("先修好再送審", r.stdout)

    def test_rounds_write_a_brief_and_round_two_needs_round_one(self):
        im = self.tmp / "frame.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=white:s=108x192", "-frames:v", "1", str(im)], check=True)
        r = pb("review-pack", "--stage", "design", "--stills", str(im), "--brief", "test", "--out", str(self.tmp / "rv"))
        self.assertEqual(r.returncode, 0, r.stderr)
        brief = (self.tmp / "rv" / "round1_brief.md").read_text(encoding="utf-8")
        R = json.loads((REPO / "data" / "review_checklists.json").read_text(encoding="utf-8"))
        self.assertIn(R["design"]["1"]["看"][0], brief)
        self.assertIn("round1_report.md", brief)
        r = pb("review-pack", "--stage", "design", "--round", "2", "--stills", str(im), "--out", str(self.tmp / "rv"))
        self.assertNotEqual(r.returncode, 0)
        (self.tmp / "rv" / "round1_report.md").write_text("總評 改了再看\n| 必改 | 第 1 張 | 字太小 |", encoding="utf-8")
        r = pb("review-pack", "--stage", "design", "--round", "2", "--stills", str(im), "--prev", str(self.tmp / "rv" / "round1_report.md"), "--out", str(self.tmp / "rv"))
        self.assertEqual(r.returncode, 0, r.stderr)
        b2 = (self.tmp / "rv" / "round2_brief.md").read_text(encoding="utf-8")
        self.assertIn("字太小", b2)
        self.assertIn(R["design"]["2"]["看"][0], b2)

    def test_reviewer_agent_is_shipped(self):
        a = (REPO / "agents" / "video-reviewer.md").read_text(encoding="utf-8")
        self.assertIn("name: video-reviewer", a)
        self.assertNotIn("Edit", a.split("---")[1])


try:
    import PIL  # noqa: F401  (video_qa needs Pillow; skip where it is not installed)
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


@unittest.skipUnless(HAS_PIL, "Pillow not installed")
class LowerThirdFill(unittest.TestCase):
    def test_flat_lower_third_is_blank_and_a_photo_is_not(self):
        sys.path.insert(0, str(REPO / "bin"))
        from video_qa import lower_blank
        from PIL import Image, ImageDraw
        d = Path(tempfile.mkdtemp())
        flat = Image.new("RGB", (540, 960), "#F4EFE6"); ImageDraw.Draw(flat).text((80, 300), "Title", fill="black"); flat.save(d / "a.png"); flat.save(d / "b.png")
        self.assertTrue(lower_blank(str(d / "a.png"), str(d / "b.png")))
        busy = Image.new("RGB", (540, 960), "#F4EFE6"); dr = ImageDraw.Draw(busy)
        for i in range(0, 540, 40): dr.rectangle([i, 700, i + 20, 960], fill="#C9A227")
        busy.save(d / "c.png")
        self.assertFalse(lower_blank(str(d / "c.png"), str(d / "c.png")))


if __name__ == "__main__":
    unittest.main()
