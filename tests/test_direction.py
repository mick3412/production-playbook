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
    return subprocess.run([sys.executable, str(REPO / "pb.py"), *args], capture_output=True, text=True, cwd=REPO, env={**os.environ, "PLAYBOOK_HOME": str(REPO)})


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



# ---------------------------------------------------------------- field-test fixes (2026-11-17, intl-school × S&P 500)
LIVE = {"需求": "國際學校家長 S&P 500 英文短片，照片故事", "形式": "照片故事",
        "二選一": {"節奏": "快", "動態": "都不要", "字量": "多", "畫面": "照片", "色彩": "繽紛", "亮暗": "亮"},
        "參考牆": {"a-clip": {"判": "", "點": ["配色", "字的進場"]}, "b-clip": {"判": "要", "點": ["節奏", "轉場"]}, "c-clip": {"判": "不要", "點": []}}}
HOOK = "Paying international school fees, with university still to come?"
POINTS = ["The school invoice comes every term.", "The university one hasn't arrived yet."]


def fake_index(tmp: Path) -> dict:
    """Two liked clips: a-clip is green and yellow, b-clip cuts every 3 s."""
    from PIL import Image
    vids = []
    for key, top, bottom, sec in (("a-clip", (12, 60, 30), (240, 210, 40), 2.0), ("b-clip", (200, 200, 200), (90, 90, 90), 3.0), ("c-clip", (0, 0, 0), (255, 255, 255), 1.0)):
        im = Image.new("RGB", (136, 240), top)
        im.paste(Image.new("RGB", (136, 90), bottom), (0, 150))
        f = tmp / f"{key}.jpg"; im.save(f)
        vids.append({"key": key, "片長": 9, "每鏡秒": sec, "影片": "", "總覽": "", "形式類": "照片故事", "鏡": [{"格": str(f)}], "亮度": 100, "飽和": 50, "變化": 1, "字面積": 2, "照片": 0.5})
    return {"片": vids}


def write_card(card: dict) -> Path:
    f = Path(tempfile.mkdtemp()) / "card.json"
    f.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    return f


class LongTextFits(unittest.TestCase):          # issue 2
    def test_a_word_wider_than_the_zone_fails_card_check(self):
        card = {"width": 1080, "height": 1920, "brand": {"colors": {"primary": "#111111", "background": "#FFFFFF", "accent": "#FF0000"}, "fonts": {"heading": "IBM Plex Sans"}},
                "beats": [{"layout": "hook", "seconds": 2.2, "text": ["Paying international school fees"], "visual": {"type": "glow"}}]}
        r = pb("card-check", str(write_card(card)))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("international", r.stdout)
        self.assertIn("FAIL", r.stdout)

    def test_another_font_only_warns(self):
        card = {"width": 1080, "height": 1920, "brand": {"colors": {"primary": "#111111", "background": "#FFFFFF", "accent": "#FF0000"}, "fonts": {"heading": "Cormorant Garamond"}},
                "beats": [{"layout": "hook", "seconds": 2.2, "text": ["Paying international"], "visual": {"type": "glow"}}]}
        r = pb("card-check", str(write_card(card)))
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("算圖後看定格確認", r.stdout)

    def test_samples_shrink_and_wrap_until_the_hook_fits(self):
        for d in (D.direction_from(LIVE), D.direction_from(PICKS)):
            card = D.sample_card(d, HOOK, POINTS, None)
            hook = card["beats"][0]
            self.assertLess(hook.get("size", 160), 160)
            r = pb("card-check", str(write_card(card)))
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertNotIn("放不下", r.stdout)
            self.assertNotIn("折行", r.stdout)           # one visual line per item: the mask never cuts a wrapped half

    def test_text_that_cannot_fit_even_at_the_floor_still_fails(self):
        card = D.sample_card(D.direction_from(PICKS), "Pneumonoultramicroscopicsilicovolcanoconiosis", [], None)
        self.assertEqual(pb("card-check", str(write_card(card))).returncode, 1)


class NeitherSide(unittest.TestCase):           # issue 3
    def test_neither_is_neutral_in_every_direction(self):
        for name, d, card in D.variants(LIVE, None, HOOK, POINTS, None):
            self.assertEqual(d["依據"]["動態"], "都不要", name)
            self.assertEqual(d["motion"].get("preset"), "crisp", name)      # not punchy, not calm
            self.assertEqual(d["motion"].get("speed"), 1.0, name)
            self.assertIn("中性（兩邊都不要）", D.describe(d))

    def test_neither_colour_uses_the_neutral_palette(self):
        d = D.direction_from({"二選一": {"色彩": "都不要"}})
        self.assertEqual(d["色盤"], D.RULES["都不要"]["色彩"]["色盤"])


class WallTicks(unittest.TestCase):             # issue 4
    def test_ticked_points_count_as_wanted(self):
        liked = D.wall_liked(LIVE)
        self.assertEqual(set(liked), {"a-clip", "b-clip"})      # a-clip: points ticked, 要 never pressed
        self.assertNotIn("c-clip", liked)


class WallLends(unittest.TestCase):             # issue 5
    def test_measured_points_go_into_direction_2_the_rest_is_recorded(self):
        I = fake_index(Path(tempfile.mkdtemp()))
        b = D.wall_borrow(LIVE, I)
        self.assertEqual(b["借"]["每鏡秒"], 3.0)                 # b-clip's measured rhythm
        self.assertEqual(b["依據"]["配色"], ["a-clip"])
        pal = b["借"]["色盤"]
        self.assertNotEqual(pal, D.direction_from(LIVE)["色盤"])
        self.assertEqual(set(b["只記錄"]), {"字的進場", "轉場"})
        v = D.variants(LIVE, b, HOOK, POINTS, None)
        self.assertEqual(v[1][1]["色盤"], pal)
        self.assertNotEqual(v[0][1]["色盤"], pal)                # direction 1 stays on the picks
        self.assertIn("參考牆", D.describe(v[1][1]))

    def test_no_index_means_nothing_borrowed(self):
        self.assertEqual(D.wall_borrow(LIVE, None)["借"], {})


class StillsDiffer(unittest.TestCase):          # issue 6
    def test_every_direction_differs_on_the_still_frame(self):
        I = fake_index(Path(tempfile.mkdtemp()))
        cases = [(LIVE, None), (LIVE, D.wall_borrow(LIVE, I)), (PICKS, None), ({"二選一": {}}, None),
                 ({"二選一": {"亮暗": "都不要", "色彩": "都不要", "動態": "強"}}, None)]
        for picks, borrow in cases:
            v = D.variants(picks, borrow, HOOK, POINTS, "")
            self.assertEqual(len(v), 3, picks)
            prints = [D.still_print(c) for _, _, c in v]
            self.assertEqual(len({json.dumps(p) for p in prints}), 3, picks)

    def test_dark_photo_direction_uses_the_dark_scrim(self):
        d = D.direction_from(LIVE, ["亮暗"])
        tmp = Path(tempfile.mkdtemp()) / "p.jpg"
        from PIL import Image
        Image.new("RGB", (90, 160), (120, 100, 80)).save(tmp)
        card = D.sample_card(d, HOOK, POINTS, str(tmp))
        self.assertEqual(card["beats"][1]["scrim"], "dark")


class ChooseFindsTheSamples(unittest.TestCase): # issues 7 and 8
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.picks = self.tmp / "picks.json"
        self.picks.write_text(json.dumps(PICKS, ensure_ascii=False), encoding="utf-8")
        self.samples = self.tmp / "elsewhere" / "samples"
        r = subprocess.run([sys.executable, str(REPO / "bin" / "direction.py"), "samples", str(self.picks), "--hook", "30 年，漲 12.8 倍", "--point", "每月定額；不猜高低點",
                            "--no-render", "--out", str(self.samples)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def choose(self, *args):
        return subprocess.run([sys.executable, str(REPO / "bin" / "direction.py"), "choose", str(self.picks), *args], capture_output=True, text=True)

    def test_samples_records_its_folder_and_choose_uses_it(self):
        self.assertEqual(json.loads(self.picks.read_text(encoding="utf-8"))["樣片資料夾"], str(self.samples.resolve()))
        r = self.choose("2")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads((self.samples / "direction.json").read_text(encoding="utf-8"))["選的方向"], 2)

    def test_number_comes_from_the_file_when_left_out(self):
        p = json.loads(self.picks.read_text(encoding="utf-8")); p["選"] = 3
        self.picks.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
        out = self.tmp / "card" / "dir.json"; out.parent.mkdir()
        r = self.choose("--out", str(out))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["選的方向"], 3)

    def test_a_rerun_clears_the_old_pick(self):
        p = json.loads(self.picks.read_text(encoding="utf-8")); p["選"] = 2
        self.picks.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
        subprocess.run([sys.executable, str(REPO / "bin" / "direction.py"), "samples", str(self.picks), "--hook", "30 年，漲 12.8 倍", "--no-render", "--out", str(self.samples)], capture_output=True, text=True)
        p = json.loads(self.picks.read_text(encoding="utf-8"))
        self.assertIsNone(p["選"])
        self.assertTrue(p["樣片時間"])
        r = self.choose()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("在樣片頁選一個方向", r.stderr)

    def test_errors_name_the_command_that_works(self):
        r = self.choose()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("choose", r.stderr)
        p = json.loads(self.picks.read_text(encoding="utf-8")); p.pop("樣片資料夾")
        self.picks.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
        r = self.choose("1")
        self.assertIn("--samples", r.stderr)
        self.assertEqual(self.choose("1", "--samples", str(self.samples)).returncode, 0)


class Serve(unittest.TestCase):                 # issue 1
    def setUp(self):
        import threading
        self.root, self.ref = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        (self.root / "direction.html").write_text("<p>page</p>", encoding="utf-8")
        (self.ref / "video").mkdir()
        (self.ref / "video" / "a b.mp4").write_bytes(bytes(range(256)) * 4)
        (self.root.parent / "secret.txt").write_text("no", encoding="utf-8")
        self.picks = self.root / "picks.json"
        self.srv = D.make_server(self.root, self.ref, self.picks, 0)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def tearDown(self):
        self.srv.shutdown(); self.srv.server_close()

    def get(self, path, **h):
        import urllib.request, urllib.error
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base + path, headers=h)) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, b"", {}

    def test_pages_and_references_over_http_with_ranges(self):
        self.assertEqual(self.get("/direction.html")[0], 200)
        st, body, _ = self.get("/ref/video/a%20b.mp4")
        self.assertEqual((st, len(body)), (200, 1024))
        st, body, h = self.get("/ref/video/a%20b.mp4", Range="bytes=100-199")
        self.assertEqual((st, body, h["Content-Range"]), (206, bytes(range(100, 200)), "bytes 100-199/1024"))

    def test_nothing_outside_the_two_folders(self):
        for path in ("/../secret.txt", "/ref/../../secret.txt", "/%2e%2e/secret.txt", "/ref/%2e%2e/%2e%2e/secret.txt"):
            self.assertEqual(self.get(path)[0], 404, path)

    def test_choices_save_to_picks_json_from_this_page_only(self):
        import urllib.request, urllib.error
        body = json.dumps({"二選一": {"節奏": "快"}, "參考牆": {}, "選": 2}).encode()
        req = lambda origin: urllib.request.Request(self.base + "/save", data=body, method="POST", headers={"Content-Type": "application/json", "Origin": origin})
        with self.assertRaises(urllib.error.HTTPError):
            urllib.request.urlopen(req("http://evil.example"))
        self.assertFalse(self.picks.exists())
        urllib.request.urlopen(req(self.base))
        self.assertEqual(json.loads(self.picks.read_text(encoding="utf-8"))["選"], 2)


try:
    from playwright.sync_api import sync_playwright  # noqa: F401
    HAS_PW = True
except Exception:
    HAS_PW = False


@unittest.skipUnless(HAS_PW, "playwright not installed")
class PageBehaviour(unittest.TestCase):         # issues 4 and 7, in the page itself (opened as a file)
    def run_page(self, path: Path, script: str):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            try:
                b = p.chromium.launch(channel="chrome")
            except Exception:
                b = p.chromium.launch()
            pg = b.new_page()
            pg.goto(path.as_uri())
            pg.wait_for_timeout(400)
            out = pg.evaluate(script)
            b.close()
        return out

    def test_ticking_a_point_marks_the_clip_wanted(self):
        tmp = Path(tempfile.mkdtemp())
        I = fake_index(tmp)
        for v in I["片"]:
            v["鏡"][0].update({"n": 1, "起": 0, "訖": 2})
        f = D.page(I, "照片故事 測試", [], tmp)
        out = self.run_page(f, """() => { const c = document.querySelector('#wall .w'); c.querySelector('input').click();
            return {on: [...c.querySelectorAll('button.on')].map(b => b.textContent), saved: Object.values(window.PICKS.參考牆)[0]}; }""")
        self.assertEqual(out["on"], ["要"])
        self.assertEqual(out["saved"]["判"], "要")

    def test_after_choosing_a_direction_the_download_stands_out(self):
        tmp = Path(tempfile.mkdtemp())
        picks = {**LIVE, "選": None}
        f = D.page(None, LIVE["需求"], [], tmp, [{"名稱": f"方向{i}", "差異": "", "影片": f"sample{i}.mp4"} for i in (1, 2, 3)], picks)
        out = self.run_page(f, """() => { const before = document.getElementById('dl').classList.contains('due');
            document.querySelectorAll('#samples button')[1].click();
            const b = document.getElementById('dl');
            return {before, due: b.classList.contains('due'), text: b.textContent, state: document.getElementById('state').textContent, picks: window.PICKS}; }""")
        self.assertFalse(out["before"])
        self.assertTrue(out["due"])
        self.assertIn("方向 2", out["text"])
        self.assertIn("還沒交回", out["state"])
        self.assertEqual(out["picks"]["選"], 2)
        self.assertEqual(out["picks"]["二選一"], LIVE["二選一"])     # a fresh browser still downloads the picks the samples came from
        self.assertEqual(out["picks"]["樣片資料夾"], str(tmp.resolve()))


if __name__ == "__main__":
    unittest.main()
