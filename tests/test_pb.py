"""End-to-end tests for pb.py. Each test works on a copy of the repo and an empty project folder.

    python3 -m unittest discover tests
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class PlaybookTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.home = self.tmp / "playbook"
        shutil.copytree(REPO, self.home, ignore=shutil.ignore_patterns(".git", "__pycache__", "inbox"))
        self.project = self.tmp / "product"
        self.project.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def pb(self, *args, ok=True):
        env = {**os.environ, "PLAYBOOK_HOME": str(self.home), "CLAUDE_PROJECT_DIR": str(self.project)}
        p = subprocess.run([sys.executable, str(self.home / "pb.py"), *args], capture_output=True, text=True, env=env, cwd=self.project)
        if ok is True:
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        elif ok is False:
            self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        return p.stdout

    def test_check_passes_and_guide_is_current(self):
        self.assertIn("OK", self.pb("check"))

    def test_every_stage_card_has_all_sections(self):
        for stage in [str(i) for i in range(10)]:
            card = self.pb("card", stage)
            for heading in ("## 要做", "## 用什麼工具", "## 要注意", "## 讓品質更好、更獨特", "## 過關條件 → 下一步"):
                self.assertIn(heading, card, f"stage {stage} misses {heading}")

    def test_card_filters_by_asset_type(self):
        talking = self.pb("card", "5", "--type", "口播")
        web = self.pb("card", "5", "--type", "網頁")
        self.assertIn("視訊錄影放半屏", talking)
        self.assertNotIn("視訊錄影放半屏", web)

    def test_production_flow_blocks_until_gates_are_checked(self):
        self.pb("start", "demo", "--type", "影片")
        self.assertIn("目前：0 開案", self.pb("status"))
        out = self.pb("advance", ok=False)
        self.assertIn("G0.1", out)
        self.pb("check-off", "G0.1", "G0.2", "G0.3")
        self.assertIn("1 研究與參考", self.pb("advance"))
        self.assertIn("目前：0 開案", self.pb("back", "0"))
        self.pb("done")
        self.assertIn("done", self.pb("list"))

    def test_hook_is_silent_without_active_production(self):
        self.assertEqual(self.pb("hook", "prompt"), "")
        self.pb("start", "demo", "--type", "影片")
        self.assertIn("▶ 作品 demo", self.pb("hook", "prompt"))
        self.assertIn("進行中的作品", self.pb("hook", "session"))
        self.pb("pause")
        self.assertEqual(self.pb("hook", "prompt"), "")

    def test_hook_never_fails_on_broken_state(self):
        (self.project / ".production").mkdir()
        (self.project / ".production" / "active.json").write_text("{not json")
        self.assertEqual(self.pb("hook", "prompt"), "")

    def test_similar_finds_the_matching_entry(self):
        out = self.pb("similar", "轉場中間那一格會有重影")
        self.assertIn("S6-02", out.splitlines()[0])

    def test_review_suggests_upgrade_after_two_good_runs(self):
        self.pb("start", "demo", "--type", "影片")
        for _ in range(2):
            self.pb("run-log", "--entries", "S6-01", "--result", "有效")
        self.assertIn("建議升級", self.pb("review"))

    def test_inbox_strips_tracking_params(self):
        self.pb("inbox", "add", "https://example.com/post?id=7&utm_source=x&fbclid=abc", "--note", "test")
        listing = self.pb("inbox", "list")
        self.assertIn("https://example.com/post?id=7", listing)
        self.assertNotIn("fbclid", listing)

    def test_next_id_continues_numbering(self):
        self.assertRegex(self.pb("next-id", "6").strip(), r"^S6-\d{2}$")
        self.assertRegex(self.pb("next-id", "協作").strip(), r"^CO-\d{2}$")

    def test_bad_value_is_reported(self):
        path = self.home / "data" / "entries.csv"
        path.write_text(path.read_text(encoding="utf-8").replace('"S6-02","CRE-64","6","6.2","檢查"', '"S6-02","CRE-64","6","6.2","亂填"'), encoding="utf-8")
        self.assertIn("類型", self.pb("check", ok=False))


if __name__ == "__main__":
    unittest.main()
