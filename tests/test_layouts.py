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
