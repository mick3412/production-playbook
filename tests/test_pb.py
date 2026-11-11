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
        shutil.copytree(REPO, self.home, ignore=shutil.ignore_patterns(".git", "__pycache__", "inbox", "bench"))
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

    def test_card_hides_steps_and_tools_of_other_asset_types(self):
        video = self.pb("card", "4", "--type", "影片")
        talking = self.pb("card", "4", "--type", "口播")
        self.assertNotIn("4.6 口播粗剪", video)
        self.assertNotIn("auto-editor", video)
        self.assertIn("4.6 口播粗剪", talking)
        self.assertIn("auto-editor", talking)

    def test_card_shows_condition_based_rechecks(self):
        self.assertIn("複查條件：下次要配英文旁白時", self.pb("card", "4", "--type", "影片"))

    def test_condition_hint_goes_away_once_ticked_or_its_step_is_done(self):
        self.pb("start", "demo", "--type", "影片")
        self.assertIn("check-off T-60", self.pb("card", "4", "--type", "影片", "--brief"))
        self.pb("check-off", "T-60")
        self.assertNotIn("ACE-Step", self.pb("card", "4", "--type", "影片", "--brief"))
        self.pb("check-off", "T-60", "--undo")
        self.pb("check-off", "4.4")
        self.assertNotIn("ACE-Step", self.pb("card", "4", "--type", "影片", "--brief"))

    def test_check_off_skips_unknown_ids_and_accepts_later_stages(self):
        self.pb("start", "demo", "--type", "影片")
        out = self.pb("check-off", "G0.1", "NOPE", "6.2")
        self.assertIn("略過 NOPE", out)
        self.assertIn("G0.2", out)                      # G0.1 is ticked, G0.2 still open
        self.assertNotIn("G0.1 一句話", out)
        self.pb("check-off", "NOPE", ok=False)

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

    def test_hook_names_the_playbook_from_its_config(self):
        self.pb("start", "demo", "--type", "影片")
        self.assertIn("進行中的作品（production-playbook）", self.pb("hook", "session"))
        self.assertTrue((self.project / ".production" / "active.json").is_file())

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


    def _first_tool(self, status):
        import csv
        with open(self.home / "data" / "tools.csv", encoding="utf-8") as f:
            return next(t for t in csv.DictReader(f) if t["狀態"] == status)

    def test_tool_runs_drive_review(self):
        t = self._first_tool("待試")
        self.pb("run-log", "--entries", t["id"], "--result", "有效")
        self.pb("run-log", "--entries", t["id"], "--result", "有效")
        self.assertIn(t["id"], self.pb("review"))

    def test_open_items_need_test_method_and_recheck(self):
        import csv
        path = self.home / "data" / "tools.csv"
        with open(path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        tid = next(r["id"] for r in rows if r["狀態"] == "待試")
        for r in rows:
            if r["id"] == tid:
                r["測試方法"] = ""
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), quoting=csv.QUOTE_ALL, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        self.assertIn(f"{tid}: 待試 needs 測試方法", self.pb("check", ok=False))


    def test_trials_caps_each_stage_and_drops_logged_items(self):
        import json, re
        stype = next(iter(json.loads((self.home / "data" / "stages.json").read_text(encoding="utf-8"))["asset_types"]))
        self.pb("start", "trial-demo", "--type", stype)
        out = self.pb("trials")
        for block in out.split("\n## ")[1:]:
            self.assertLessEqual(block.count("- [ ] **"), 3, block)
        first = re.search(r"- \[ \] \*\*([A-Z]+-\d+)\*\*", out)
        if first:
            self.pb("run-log", "--entries", first[1], "--result", "有效", "--name", "trial-demo")
            self.assertNotIn(f"**{first[1]}**", self.pb("trials"))
        if out.count("- [ ] **") > 1:
            self.assertIn("排定要測", self.pb("done", "trial-demo"))


    def _golden(self):
        import json
        return json.loads((REPO / "tests" / "golden_briefs.json").read_text(encoding="utf-8"))

    def test_golden_briefs_pick_the_right_items(self):
        for c in self._golden()["cases"]:
            out = self.pb("plan", c["need"], *(["--type", c["type"]] if c.get("type") else []))
            first = out.split("## 方案 2")[0]
            for i in c["must"]:
                self.assertIn(i + " ", first, f"「{c['need']}」的第一個方案少了 {i}")
            self.assertNotIn("〔避開", out)
            self.assertNotIn("〔未採用", out)

    def test_rules_file_leaves_items_out(self):
        c = self._golden()["cases"][0]
        rules = self.tmp / "rules.txt"
        rules.write_text("# 樣本規則\nid=" + c["must"][0] + "\n", encoding="utf-8")
        out = self.pb("plan", c["need"], "--rules", str(rules))
        self.assertIn("專案規則排除：" + c["must"][0], out)

    def test_saved_plan_shows_in_brief_and_done(self):
        g = self._golden()
        self.pb("start", "demo", "--type", g["start_type"])
        self.assertIn("已把方案 1", self.pb("plan", g["save_need"], "--save"))
        self.assertIn("方案項目：", self.pb("card", g["brief_stage"], "--brief"))
        self.assertIn("方案裡用過、還沒記結果的項目", self.pb("done"))

    def test_bench_lists_desk_items_and_logs_them(self):
        out = self.pb("bench", "--batch", "3")
        self.assertIn("桌上試驗", out)
        first = out.split("**")[1]
        self.pb("run-log", "--bench", "--entries", first, "--result", "有效")
        self.assertNotIn("**" + first + "**", self.pb("bench", "--batch", "500"))


if __name__ == "__main__":
    unittest.main()
