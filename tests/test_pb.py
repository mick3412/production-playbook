"""End-to-end tests for pb.py. Each test works on a copy of the repo and an empty project folder.

    python3 -m unittest discover tests
"""
import json
import os
import re
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
        self.assertIn("複查條件：開始經營 YouTube 頻道時", self.pb("card", "4", "--type", "影片"))

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

    def test_golden_briefs_three_steps(self):
        """need → facets (step 1) → recipe (step 2) → ids (step 3, checked above)."""
        for c in self._golden()["cases"]:
            if c.get("facets"):
                sug = self.pb("facets", "--suggest", c["need"])
                for f in c["facets"]:
                    self.assertIn(f, sug, f"「{c['need']}」推測的分面少了 {f}")
            if c.get("recipe"):
                out = self.pb("plan", c["need"], *(["--type", c["type"]] if c.get("type") else []))
                self.assertIn(f"## 方案 1：{c['recipe']} ", out, f"「{c['need']}」的第一個方案不是 {c['recipe']}")

    def test_tags_are_callable_and_latin_synonyms_match_whole_words(self):
        out = self.pb("facets", "--audit")
        rate = int(out.split("可調用率")[1].split("：")[1].split("%")[0])
        self.assertGreaterEqual(rate, 95, out[:400])
        self.assertIn("缺工作項目：0", out)
        self.assertIn("標籤自相衝突：0", out)
        self.assertNotIn("平台=IG", self.pb("facets", "--suggest", "redesign the company site"))
        self.assertIn("平台=IG", self.pb("facets", "--suggest", "發 IG 貼文"))

    def test_shared_tags_are_identical_across_books(self):
        others = [REPO.parent / f"{b}-playbook" / "data" / "shared.json" for b in ("production", "marketing", "web", "engineering")]
        for o in others:
            if o.is_file():
                self.assertEqual((REPO / "data" / "shared.json").read_bytes(), o.read_bytes(), f"copy data/shared.json to {o.parent.parent.name}")
        self.assertIn("風格=新粗獷", self.pb("facets", "--suggest", "新粗獷風的活動"))

    def test_strategy_to_work_orders_to_spec(self):
        out = self.pb("strategy", "--from", "三個月內用 IG 和網站替新服務累積 300 筆名單，權威專業", "--save")
        self.assertIn("指標：300 筆名單", out)
        self.assertIn("Q1｜受眾", out)                     # never invented
        self.assertIn("風格：瑞士國際主義", out)
        works = self.pb("strategy", "--works")
        self.assertIn("W01｜短期｜名單型 Reel", works)
        spec = self.pb("spec", "--work", "W01")
        self.assertIn("作品單 W01", spec)
        self.assertIn("| 時長ms | 150–250 | 設計屬性：俐落 |", spec)
        self.assertIn("沿用策略卡", self.pb("spec", "--from", "做一支 30 秒產品影片"))
        self.assertIn("作品單 W01", self.pb("plan", "--work", "W01"))

    def test_image_needs_land_without_motion_and_style_sheet_spans_media(self):
        out = self.pb("spec", "--from", "IG 輪播圖卡，新粗獷")
        self.assertIn("推測：媒材 圖片", out)
        for d in ("| 運鏡 ", "| 過場 ", "| 剪輯節奏 "):
            self.assertNotIn(d, out)
        sheet = self.pb("style", "新粗獷")
        for m in ("- 影片（", "- 圖片（", "- 網站（"):
            self.assertIn(m, sheet)
        self.assertIn("沒有策略卡，這一輪先問", self.pb("spec", "--from", "做一支 30 秒產品影片"))

    def test_blueprint_has_every_section_and_stage(self):
        out = self.pb("blueprint", "45 秒 IG Reels 口播，安靜高級，要留名單")
        for n in range(1, 10):
            self.assertIn(f"## {n}. ", out)
        import json as _json
        st = _json.loads((self.home / "data" / "stages.json").read_text(encoding="utf-8"))["stages"]
        for s in st:
            self.assertIn(f"- **{s['id']} {s['name']}**", out)
        self.assertIn("  - 步驟：", out)
        self.assertIn("  - 過關：", out)
        if (Path.home() / ".config" / "marketing-playbook" / "home").is_file():
            self.assertIn("行銷手冊 R-02", out)
        self.assertIn("IG Reels：尺寸 1080×1920", out)
        self.pb("blueprint", "45 秒 IG Reels 口播，安靜高級，要留名單", "--save")
        saved = list((self.project / ".strategy" / "計畫").glob("*.md"))
        self.assertEqual(len(saved), 1)

    def test_questions_come_in_rounds(self):
        out = self.pb("blueprint", "做一支產品影片")
        self.assertIn("❓ Q1｜目的", out)
        self.assertIn("沒有建議，這要你決定", out)                 # audience is never invented
        self.assertIn("下一輪（等上面的答案）：平台", out)
        out2 = self.pb("blueprint", "做一支 IG Reels 產品影片，給 30 歲上班族，要留名單")
        self.assertNotIn("｜目的：", out2)
        self.assertIn("｜篇幅：", out2)

    def test_design_values_carry_presentation_layers(self):
        # a design value prints its full recipe or the five layers; motion numbers alone only give a skeleton (C6, 2026-11-13)
        out = self.pb("spec", "影片", "--from", "產品短片，碎裂過場，數字跳動，標題卡，雙語字幕")
        self.assertIn("## 呈現層", out)
        self.assertIn("2.5 px 白邊", out)          # 碎裂: full recipe from #142
        self.assertIn("陪襯元素：", out)           # 雙語字幕: five layers only
        self.assertIn("左側向上箭頭圓", out)       # 數字跳動: full recipe from #007
        V = json.loads((REPO / "data/vocab.json").read_text(encoding="utf-8"))["維度"]
        for d in ("動態圖像", "過場", "文字與字幕"):
            for k, x in V[d].items():
                self.assertTrue(x.get("完整做法") or x.get("呈現層"), f"{d}＝{k} has no presentation layers")

    def test_terms_table_and_any_name_finds_the_value(self):
        for need, want in (("甩镜过场要快", "過場=甩鏡過場"), ("レンブラントライティング", "布光=林布蘭光"), ("dolly zoom 的效果", "運鏡=推拉變焦"),
                           ("浮世繪風的片頭", "風格=浮世繪"), ("做一個玻璃碎裂的轉場", "過場=碎裂"), ("text scramble 標題", "動態圖像=文字亂碼")):
            self.assertIn(want, self.pb("facets", "--suggest", need))
        out = self.pb("facets", "--suggest", "用 Zoom 錄的訪談")
        self.assertNotIn("運鏡=", out)                       # a bare English word inside a longer phrase or another meaning
        self.assertIn("篇幅=多張輪播", self.pb("facets", "--suggest", "IG 輪播圖卡"))
        table = self.pb("vocab", "過場", "--terms")
        self.assertIn("| 甩鏡過場 | whip pan transition", table)
        self.assertIn("#043", table)

    def test_rules_file_leaves_items_out(self):
        c = self._golden()["cases"][0]
        rules = self.tmp / "rules.txt"
        rules.write_text("# 樣本規則\nid=" + c["must"][0] + "\n", encoding="utf-8")
        out = self.pb("plan", c["need"], "--rules", str(rules))
        self.assertIn("排除：" + c["must"][0], out)

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


    def test_facets_suggest_expand_and_tone(self):
        self.assertIn("平台=IG Reels", self.pb("facets", "--suggest", "45 秒 IG Reels，質感 premium，要留名單"))
        self.assertIn("調性=安靜高級", self.pb("facets", "--suggest", "要有質感 premium 一點"))
        out = self.pb("plan", "海外投資說明", "--facets", "目的=信任建立；產業=金融保險")
        line = next(l for l in out.splitlines() if l.startswith("推測調性"))
        self.assertIn("權威專業", line)
        self.assertNotIn("可愛", line)
        self.assertIn("提醒：產業=金融保險 建議避開「可愛」", self.pb("plan", "海外投資說明", "--facets", "產業=金融保險；調性=可愛"))

    def test_spec_from_need_gives_numbers_with_their_layer(self):
        out = self.pb("spec", "--from", "45 秒訪談口播，安靜高級，IG Reels")
        self.assertIn("推測：媒材 影片；場景 訪談口播；調性 安靜高級", out)
        for row in ("| 焦段mm | 50–85 | 場景：訪談口播 |", "| 光圈 | f/2–2.8 | 場景：訪談口播 |", "| 光比 | 1:3 | 場景：訪談口播 |",
                    "| 主光水平角° | 45 | 場景：訪談口播 |", "| 色溫K | 5600 | 場景：訪談口播 |"):
            self.assertIn(row, out)
        self.assertIn("鏡頭與攝影機＝中長焦 寫 f/1.8", out)      # the general range is shown, not silently dropped
        card = self.tmp / "c.json"
        self.pb("spec", "--from", "45 秒訪談口播，安靜高級，IG Reels", "--out", str(card))
        self.assertIn("全片生效數值（場景或風格定的", self.pb("spec", str(card)))

    def test_spec_from_offers_options_when_layers_disagree(self):
        out = self.pb("spec", "--from", "活潑的訪談口播")
        self.assertIn("## 要選一個", out)
        self.assertIn("運鏡：固定（場景：訪談口播）或", out)

    def test_styles_are_a_hierarchy_and_prompts_never_name_studios(self):
        self.assertIn("風格=吉卜力式手繪", self.pb("facets", "--suggest", "吉卜力風的品牌動畫"))
        self.assertIn("風格=動漫", self.pb("facets", "--suggest", "動漫風的介紹片"))
        self.assertIn("風格=美式超英漫畫", self.pb("facets", "--suggest", "美式漫畫風的數據解說"))
        self.assertNotIn("等距", self.pb("facets", "--suggest", "三個圖示等距離排列"))
        card = self.tmp / "g.json"
        self.pb("spec", "--from", "吉卜力風的品牌動畫 30 秒", "--out", str(card))
        self.assertIn("背景用紙紋＋水彩筆刷貼圖", self.pb("spec", str(card)))       # graphic shots: the style's build notes
        self.pb("spec", "--from", "用 AI 生成吉卜力風的品牌動畫 30 秒", "--out", str(card))
        prompt = self.pb("spec", str(card)).split("## 二")[0]
        self.assertIn("hand-painted anime", prompt)
        for name in ("吉卜力", "Ghibli", "宮崎駿"):
            self.assertNotIn(name, prompt.split("（英文")[1])
        import json as _json
        p = self.home / "data" / "vocab.json"
        v = _json.loads(p.read_text(encoding="utf-8"))
        v = _json.loads((self.home / "data" / "shared.json").read_text(encoding="utf-8"))
        v["風格"]["吉卜力式手繪"]["落地"]["影片"]["寫法"]["AI 生成"] += ", Ghibli style"
        p = self.home / "data" / "shared.json"
        p.write_text(_json.dumps(v, ensure_ascii=False), encoding="utf-8")
        self.assertIn("出現專有名稱「Ghibli」", self.pb("check", ok=False))

    def test_every_vocab_value_has_numbers_or_criteria(self):
        import json as _json
        v = _json.loads((self.home / "data" / "vocab.json").read_text(encoding="utf-8"))
        missing = [f"{d}/{k}" for d, vals in v["維度"].items() for k, x in vals.items() if "數值" not in x]
        self.assertEqual(missing, [])

    def test_unknown_facet_value_fails_check(self):
        import csv as _csv
        p = self.home / "data" / "entries.csv"
        rows = list(_csv.DictReader(open(p, encoding="utf-8")))
        rows[0]["情境"] = "目的=不存在的值"
        w = _csv.DictWriter(open(p, "w", encoding="utf-8", newline=""), fieldnames=list(rows[0]), quoting=_csv.QUOTE_ALL, lineterminator="\n")
        w.writeheader(); w.writerows(rows)
        self.assertIn("不在 facets.json", self.pb("check", ok=False))


    def _card(self, **over):
        import json
        card = {"片名": "t", "畫幅": "直式 9:16", "格率": 30, "片長": 6, "調性": "安靜高級",
                "鏡頭": [{"編號": 1, "秒數": 3, "內容": "a", "景別": "近景", "運鏡": "手持", "構圖": "置中對稱", "過場到下一鏡": "溶接"},
                         {"編號": 2, "秒數": 3, "內容": "b"}]}
        card.update(over)
        p = self.tmp / "card.json"; p.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
        return str(p)

    def test_spec_renders_four_parts_with_defaults_and_conflicts(self):
        out = self.pb("spec", self._card())
        for part in ("## 一、AI 生成提示詞", "## 二、程式動畫規格", "## 三、實拍拍攝單", "## 四、審片對照表"):
            self.assertIn(part, out)
        self.assertIn("警告：第 1 鏡：運鏡=手持 和 構圖=置中對稱 衝突", out)
        self.assertIn("| 2 | 運鏡 | 固定 （位移 0、縮放 0） | 預設 |", out)
        self.assertIn("第 0–89 格（90 格）", out)
        self.assertNotIn("| 2 | 過場 |", out)          # the last shot gets no default transition

    def test_spec_graphic_shots_skip_camera_and_light(self):
        out = self.pb("spec", self._card(調性="活潑", 鏡頭=[{"編號": 1, "秒數": 3, "內容": "a", "畫面類型": "動態圖形"},
                                                        {"編號": 2, "秒數": 3, "內容": "b", "畫面類型": "實拍"}]))
        self.assertIn("第 1 鏡：動態圖形，不用 AI 生成", out)
        self.assertNotIn("| 1 | 運鏡 |", out)
        self.assertNotIn("| 1 | 布光 |", out)
        self.assertIn("| 2 | 運鏡 |", out)
        self.assertIn("要是 實拍、AI 生成、動態圖形 之一", self.pb("spec", self._card(畫面類型="螢幕"), ok=False))

    def test_spec_rejects_unknown_values_and_bad_length(self):
        self.assertIn("不在語彙裡", self.pb("spec", self._card(鏡頭=[{"編號": 1, "秒數": 6, "運鏡": "瞬移"}]), ok=False))
        self.assertIn("和片長 9 秒不符", self.pb("spec", self._card(片長=9), ok=False))

    def test_probe_footage_cuts_at_pause_and_writes_edit_script(self):
        import json, shutil, subprocess
        if not shutil.which("ffmpeg"):
            self.skipTest("no ffmpeg")
        clip = self.tmp / "c.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=180x320:d=3.2:r=30", "-f", "lavfi",
                        "-i", "aevalsrc='if(between(t,1.2,2.0),0.0003*random(0),0.3*sin(2*PI*300*t))':s=16000:d=3.2",
                        "-shortest", str(clip)], check=True)
        out = self.tmp / "probe"
        self.pb("probe", "footage", str(clip), "--out", str(out))
        rep = json.loads((out / "footage.json").read_text(encoding="utf-8"))
        self.assertTrue(any(a < 1.4 and b > 1.8 for a, b in rep["停頓"]), rep["停頓"])
        card = json.loads((out / "draft_card.json").read_text(encoding="utf-8"))
        self.assertEqual(len(card["鏡頭"]), 2)
        self.assertIn("between(t,", (out / "edit.sh").read_text(encoding="utf-8"))

    def test_vocab_lists_and_tone_presets(self):
        self.assertIn("whip pan", self.pb("vocab", "運鏡"))
        self.assertIn("運鏡：固定、慢推", self.pb("vocab", "--tone", "安靜高級"))

    def test_storyboard_dispatch_golden_cases(self):
        out = self.pb("storyboard", "Stay the Course 第 9 集，純文字 Reels")
        self.assertIn("SF-01 系列格式：Stay the Course", out)
        cases = {"純文字動態，三個重點清單教學 S1": "SB-T1", "純文字動態，A 和 B 的比較": "SB-T5",
                 "峇里島別墅的生活照片 Reels，給 S6 看一天怎麼過": "SB-P1", "照片故事：客戶家庭搬到峇里的起承轉合": "SB-P5",
                 "顧問口播介紹自己，建立信任": "SB-K6", "客戶訪談見證短片": "SB-K4",
                 "IG 輪播比較租金和長期配置 S1": "SB-C3", "輪播圖卡：迷思測驗，題目和揭曉": "SB-C8"}
        for need, tid in cases.items():
            top = re.findall(r"^### (SB-\w+)", self.pb("storyboard", need), re.M)
            self.assertIn(tid, top, need)
        full = self.pb("storyboard", "--use", "SB-T1")
        self.assertIn("這種形式的共用規則", full)
        self.assertIn("S0-06", full)
        self.assertIn("SB-", self.pb("blueprint", "純文字動態 Reels，三個重點清單教學"))

    def test_storyboard_library_rejects_old_safe_zone(self):
        p = self.home / "data" / "storyboards.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        d["模板"][0]["審片要點"].append("字幕下緣 y≤78%")
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        self.assertIn("舊安全區", self.pb("check", ok=False))

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("swift") and sys.platform == "darwin", "needs ffmpeg, swift and macOS Vision")
    def test_qa_catches_a_badly_made_video(self):
        # frames drawn with AppKit (no Pillow, no ffmpeg drawtext needed): black, then a late hook and a caption in the button area
        swift = self.tmp / "frames.swift"
        swift.write_text("""import AppKit
func frame(_ path: String, _ texts: [(String, CGFloat, CGFloat)]) {
  let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1080, pixelsHigh: 1920, bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
  NSGraphicsContext.saveGraphicsState(); NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
  NSColor.black.setFill(); NSRect(x: 0, y: 0, width: 1080, height: 1920).fill()
  for (t, size, top) in texts { (t as NSString).draw(at: NSPoint(x: 140, y: 1920 - top - size), withAttributes: [.font: NSFont.boldSystemFont(ofSize: size), .foregroundColor: NSColor.white]) }
  NSGraphicsContext.restoreGraphicsState(); try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: path))
}
let d = CommandLine.arguments[1]
frame(d + "/blank.png", [])
frame(d + "/late.png", [("LATE HOOK", 120, 600), ("tiny caption under the buttons", 34, 1700)])
""", encoding="utf-8")
        subprocess.run(["swift", str(swift), str(self.tmp)], check=True, capture_output=True)
        blank, late = self.tmp / "blank.png", self.tmp / "late.png"
        bad = self.tmp / "bad.mp4"   # 1.5 s of nothing, then a hook and a caption in the button area
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "1.5", "-i", str(blank), "-loop", "1", "-t", "2.5", "-i", str(late),
                        "-filter_complex", "[0][1]concat=n=2:v=1,fps=24,format=yuv420p", str(bad)], check=True)
        out = self.pb("qa", str(bad), "--out", str(self.tmp / "qa.json"), "--template", "SB-T1", "--require", "General information only", ok=False)
        self.assertIn("FAIL  鉤子：0.6 秒內有大字", out)
        self.assertRegex(out, r"FAIL  第 1 段安全區：.*tiny")
        self.assertIn("FAIL  必要字句", out)
        self.assertIn("SB-T1 的審片要點", out)
        # the same images as static carousel pages: feed safe zone, no timing or reading-speed checks
        out = self.pb("qa", str(late), str(blank), "--out", str(self.tmp / "pages.json"), "--template", "SB-C1", ok=None)
        self.assertIn("封面有大字", out)
        self.assertNotIn("0.6 秒內", out)
        self.assertNotIn("閱讀速度", out)
        self.assertNotRegex(out, r"FAIL  第 1 段安全區")
        self.assertIn("SB-C1 的審片要點", out)
        # with a card: words the card promises but the picture does not show (covered, clipped, dropped) fail; the planned lower block is design
        card = self.tmp / "card.json"
        card.write_text(json.dumps({"beats": [{"layout": "hook", "seconds": 4, "text": ["LATE HOOK", "hidden headline"],
                                                "lower": {"type": "panel", "text": "tiny caption under the buttons"}}]}), encoding="utf-8")
        out = self.pb("qa", str(bad), "--card", str(card), "--out", str(self.tmp / "card_qa.json"), ok=None)
        self.assertRegex(out, r"FAIL  第 1 段文字完整出現：.*沒讀到：hidden、headline")
        self.assertNotRegex(out, r"第 1 段安全區：.*tiny")
        self.assertIn("下方區塊", self.pb("storyboard", "--use", "SB-T1"))

    def test_video_qa_safe_zone_follows_handbook_s0_06(self):
        sys.path.insert(0, str(REPO / "bin"))
        import video_qa
        box = lambda x, y, w, h: {"x": x / 1080, "y": y / 1920, "w": w / 1080, "h": h / 1920}
        z = video_qa.SAFE["reels-tiktok"]
        self.assertFalse(video_qa.unsafe(box(150, 500, 700, 100), z))          # upper area, full width inside 120–960
        self.assertTrue(video_qa.unsafe(box(150, 900, 700, 100), z))           # below y 840 the right edge passes 780 (button column)
        self.assertFalse(video_qa.unsafe(box(150, 900, 500, 100), z))
        self.assertTrue(video_qa.unsafe(box(150, 1300, 300, 60), z))           # under y 1248: caption area
        self.assertTrue(video_qa.unsafe(box(150, 200, 300, 60), z))            # above y 270
        self.assertFalse(video_qa.unsafe(box(113, 500, 300, 60), z))           # a few px of OCR side bearing is tolerated
        self.assertFalse(video_qa.unsafe(box(150, 1300, 300, 60), video_qa.SAFE["shorts"]))


if __name__ == "__main__":
    unittest.main()
