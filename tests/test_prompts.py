"""Prompt skeleton (data/prompt_skeleton.json), `spec --from` for images, and `prompt-check`.

    python3 -m unittest tests.test_prompts
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EX = REPO / "data" / "prompt_examples"
POSTER = "把一張人物照片做成 3:4 直式海報，上半真實攝影、下半抽象幾何符號"


def pb(*args):
    return subprocess.run([sys.executable, str(REPO / "pb.py"), *args], capture_output=True, text=True, cwd=REPO)


class SpecFromImage(unittest.TestCase):
    def setUp(self):
        self.out = pb("spec", "圖片", "--from", POSTER).stdout

    def test_ratio_and_zones_survive(self):
        self.assertIn("3:4 直式", self.out)
        self.assertIn("上半真實攝影", self.out)

    def test_no_moving_picture_numbers_in_a_still(self):
        draft = self.out.split("沒有策略卡")[0]
        for w in ("每格", "進場秒", "停留秒", "格率"):
            self.assertNotIn(w, draft)

    def test_a_generic_word_does_not_apply_a_style(self):
        self.assertNotIn("包浩斯（風格：包浩斯）", self.out)      # 「幾何」 only: a candidate, not applied
        self.assertIn("候選 包浩斯", self.out)

    def test_a_named_style_still_applies_and_tone_style_disagreement_is_a_choice(self):
        out = pb("spec", "--from", "紀實風的包浩斯海報").stdout
        self.assertIn("包浩斯（風格：包浩斯）", out)
        self.assertIn("色彩：中性（調性：紀實）或 高飽和（風格：包浩斯）", out)

    def test_skeleton_draft_marks_what_to_write(self):
        self.assertIn("## 提示詞骨架（圖片", self.out)
        self.assertIn("**最終目標**：待補", self.out)
        self.assertIn("圖生圖", self.out)                          # a photo is the input

    def test_card_renders_and_fails_until_written(self):
        card = Path(tempfile.mkdtemp()) / "c.json"
        pb("spec", "圖片", "--from", POSTER, "--out", str(card))
        c = json.loads(card.read_text(encoding="utf-8"))
        self.assertEqual(c["素材類型"], "圖片")
        self.assertEqual(c["畫幅"], "3:4")
        r = pb("spec", str(card))
        self.assertEqual(r.returncode, 1)
        self.assertIn("prompt-check：FAIL", r.stdout)


class PromptCheck(unittest.TestCase):
    def test_owner_example_passes(self):                 # the external anchor: the owner's own prompt
        r = pb("prompt-check", str(EX / "poster_photo_to_symbol.zh.txt"))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_gold_card_passes(self):
        r = pb("prompt-check", str(EX / "poster_photo_to_symbol.card.json"))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("總評 PASS", r.stdout)

    def test_old_one_liners_fail(self):
        for f in (EX / "negative").glob("*.txt"):
            r = pb("prompt-check", str(f))
            self.assertEqual(r.returncode, 1, f"{f.name}:\n{r.stdout}")

    def test_vague_words_and_negated_contradictions(self):
        r = pb("prompt-check", "masterpiece, 8k, minimal poster")
        self.assertIn("空詞", r.stdout)
        txt = (EX / "poster_photo_to_symbol.zh.txt").read_text(encoding="utf-8")
        self.assertNotIn("矛盾", pb("prompt-check", txt).stdout)     # 「拒绝繁复」 is not asking for 繁复

    def test_template_has_every_section(self):
        t = json.loads(pb("spec", "--template", "圖片").stdout)
        sk = json.loads((REPO / "data" / "prompt_skeleton.json").read_text(encoding="utf-8"))
        self.assertEqual(set(t["提示詞"]), {x["id"] for x in sk["圖片"]})


if __name__ == "__main__":
    unittest.main()
