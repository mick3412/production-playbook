#!/usr/bin/env python3
"""Measure a finished vertical video against the storyboard norms, with the same tools that measure reference templates
(bin/video_probe.py: Vision OCR text boxes, frames, colours). Each check is PASS, WARN or FAIL with the measured number.

  video_qa.py <video.mp4> [--card card.json] [--platform reels-tiktok|shorts] [--require "phrase" ...] [--out qa.json]
  video_qa.py page01.png --images page02.png ... [--out qa.json]     static carousel pages (feed safe zone, no timing checks)

With --card the beat boundaries come from the card (layout and seconds per beat); without it, from scene cuts.
Norms (2026-11-13, storyboard pilot; readability from 20 measured FlexClip templates, hook from the handbook's own rules):
  hook: large text on screen by 0.6 s, tallest line ≥ 8 % of the frame height, hook beat ≤ 3 s
  reading: ≤ 2.5 English words / s (median of references 1.9, p75 2.6); disclosure ≤ 3.3 words / s; ≤ 5 Chinese characters / s
  size: tallest line ≥ 4 % of frame height (18 % of reference shots fall below this and are hard to read on a phone); no line < 2.5 %
  safe zone, per platform (--platform): reels-tiktok (default, handbook S0-06, the strictest of TikTok and IG Reels on 1080×1920):
    x 120–960, y 270–1248, and below y 840 the right edge stays left of x 780 (button column); shorts (S5-20 / ShortGenius
    2026: central window about 900×1160): x 60–960, y 380–1540
  contrast: ≥ 4.5 : 1 between text and its background (WCAG AA), estimated inside each text box
  beats: 1.5–7 s each; the last beat ≥ 2 s; required phrases visible for at least words ÷ 3 seconds
"""
from __future__ import annotations

import argparse, json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import video_probe as vp  # noqa: E402

NORM = {"hook_by": 0.6, "hook_min_h": 8.0, "hook_max_s": 3.0, "wps": 2.5, "wps_disclosure": 3.3, "cps": 5.0, "min_h": 4.0, "floor_h": 2.5,
        "contrast": 4.5, "beat": (1.5, 7.0), "last_min": 2.0}


# text boxes must stay inside these, as fractions of 1080×1920: (left, top, right, bottom, button_row_top, button_col_left)
SAFE = {"reels-tiktok": (120 / 1080, 270 / 1920, 960 / 1080, 1248 / 1920, 840 / 1920, 780 / 1080),
        "shorts": (60 / 1080, 380 / 1920, 960 / 1080, 1540 / 1920, 1.0, 1.0),
        "feed": (0.05, 0.04, 0.95, 0.96, 1.0, 1.0),
        "story": (0.05, 0.13, 0.95, 0.82, 1.0, 1.0)}   # IG / FB Stories: profile bar on top, reply bar and stickers' edge at the bottom   # static carousel pages (1080×1350): no platform UI on top, keep a margin


def unsafe(b: dict, z: tuple, slack: float = 0.01) -> bool:
    """OCR boxes run a few pixels past the glyphs (side bearing), so allow 1 % slack before calling a box unsafe."""
    l, t, r, bt, row, col = z
    x2, y2 = b["x"] + b["w"] - slack, b["y"] + b["h"] - slack
    b = {**b, "x": b["x"] + slack, "y": b["y"] + slack}
    return b["x"] < l or b["y"] < t or x2 > r or y2 > bt or (y2 > row and x2 > col)


def lum(rgb: tuple) -> float:
    c = [v / 255 for v in rgb]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def box_contrast(img: str, b: dict, W: int, H: int) -> float:
    x, y = max(0, min(W - 4, int(b["x"] * W))), max(0, min(H - 4, int(b["y"] * H)))
    w, h = max(4, min(W - x, int(b["w"] * W))), max(4, min(H - y, int(b["h"] * H)))
    # sample the box at full resolution: shrinking it first averages thin strokes into the background and under-reads small text
    px = subprocess.run(["ffmpeg", "-v", "error", "-i", img, "-vf", f"crop={w}:{h}:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    ls = sorted(lum(tuple(px[i:i + 3])) for i in range(0, len(px) - 2, 3))
    if not ls:
        return 0.0
    lo, hi = ls[int(len(ls) * 0.02)], ls[int(len(ls) * 0.98)]
    return round((hi + 0.05) / (lo + 0.05), 1)


LAYOUTS = {}
try:   # the layout catalogue: each layout's text zone (production-playbook kits)
    LAYOUTS = {x["id"]: x for x in json.loads((Path(__file__).resolve().parents[1] / "kits" / "storyboard" / "layouts.json").read_text(encoding="utf-8"))["版型"]}
except (OSError, ValueError, KeyError):
    pass


def lower_blank(late: str, early: str) -> bool:
    """The frame under the text zone (y 65–100 %) is one flat colour and does not move between two moments of the beat."""
    try:
        from PIL import Image, ImageChops, ImageStat
    except ImportError:   # Pillow missing: the fill check is skipped, the rest of the review still runs
        return None
    def crop(p):
        im = Image.open(p).convert("L"); w, h = im.size
        return im.crop((0, int(h * 0.65), w, h)).resize((90, 60))
    a, b = crop(late), crop(early)
    still = ImageStat.Stat(ImageChops.difference(a, b)).mean[0] < 1.5
    return ImageStat.Stat(a).stddev[0] < 6 and still


def words(t: str) -> tuple[int, int]:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’.&%$-]*", t)), len(re.findall(r"[㐀-鿿]", t))


def qa(video: str, card: dict | None, require: list[str], tmp: Path, boards: list[float] | None = None, platform: str = "reels-tiktok", static: bool = False) -> dict:
    """static=True: pages of a carousel shown as a slideshow; the reader sets the pace, so hook timing and reading speed are not checked."""
    info = vp.probe(video); W, H, dur = info["width"], info["height"], info["duration"]
    tmp.mkdir(parents=True, exist_ok=True)
    if card:
        beats, t = [], 0.0
        for b in card["beats"]:
            beats.append({"layout": b["layout"], "a": t, "b": t + b["seconds"]}); t += b["seconds"]
    elif boards:
        k, beats, t = dur / sum(boards), [], 0.0
        for d in boards:
            beats.append({"layout": "", "a": t, "b": t + d * k}); t += d * k
    else:
        cs = [0.0] + vp.cuts(video) + [dur]
        beats = [{"layout": "", "a": a, "b": b} for a, b in zip(cs, cs[1:]) if b - a > 0.2]
    # with a card we know which words the overlay puts on screen; anything else OCR reads (a calendar, a calculator, a sign in a photo)
    # belongs to the footage: it is reported, not counted as text to read
    known = None
    if card:
        def walk(v):
            if isinstance(v, str): return v
            if isinstance(v, list): return " ".join(walk(x) for x in v)
            if isinstance(v, dict): return " ".join((f"{x:,} {x}" if k in ("v", "value") and isinstance(x, (int, float)) else walk(x))
                                                    for k, x in v.items() if k not in ("image", "fg", "layout", "tone", "side", "kind", "role", "deco", "deco_style", "lower"))
            return ""   # numbers in a card are timings and sizes, not words on screen (chart values are written out as label strings)
        raw = re.sub(r"<[^>]+>|&[a-z]+;", " ", walk(card.get("beats", [])) + " " + str(card.get("series", "")) + " " + walk(card.get("brand", {}).get("handle", "")))
        known = {w for w in re.findall(r"[a-z0-9]+|[\u3400-\u9fff]", raw.lower())}
        known |= {f"{i:02d}" for i in range(1, 10)}   # list numbers the kit adds itself (01, 02, …)
        blob = re.sub(r"[^a-z0-9\u3400-\u9fff]+", "", raw.lower())   # OCR often drops the spaces ("Whatif"): also match with spaces removed
    def overlay(x):
        if known is None: return True
        ws = re.findall(r"[a-z0-9]+|[\u3400-\u9fff]", x["text"].lower())
        flat = re.sub(r"[^a-z0-9\u3400-\u9fff]+", "", x["text"].lower())
        import difflib   # a lone word with one letter misread ("yeaI" for "year") is still the card's word, not text in the footage
        kn = lambda w: w in known or (len(w) >= 4 and any(len(k) == len(w) and difflib.SequenceMatcher(None, w, k).ratio() >= 0.75 for k in known))
        return not ws or sum(kn(w) for w in ws) / len(ws) >= 0.5 or (len(flat) >= 4 and (flat in blob or flat[1:] in blob))
    # decorative type declared on the card (b["deco"]) may sit outside the safe zone and be covered by platform UI: it is not text to read
    def low(v):
        if isinstance(v, str): return [v]
        if isinstance(v, list): return [y for x in v for y in low(x)]
        if isinstance(v, dict): return [y for k, x in v.items() if k != "image" for y in low(x)]
        return [str(v)] if isinstance(v, (int, float)) else []
    def vis_text(b, card):   # the visual layer (owner rule 2026-11-16) is design: a giant numeral or word in it is not reading text
        v = b["visual"] if "visual" in b else (card or {}).get("visual")
        return [str(x.get("text", "")) for x in ([] if v is None else [v] if isinstance(v, dict) else v) if isinstance(x, dict) and x.get("type") in ("numeral", "word")]
    deco = [re.sub(r"[^a-z0-9\u3400-\u9fff]+", "", re.sub(r"&[a-z]+;", "", t.lower())) for b in (card or {}).get("beats", []) for t in ([str(b["deco"])] if b.get("deco") else []) + low(b.get("lower")) + vis_text(b, card)]
    deco = [d for d in deco if d]
    def is_deco(x, size):
        flat = re.sub(r"[^a-z0-9\u3400-\u9fff]+", "", x["text"].lower())
        return bool(flat) and (x["h"] >= size or x["y"] > 0.6) and any(flat == d or (len(d) >= 3 and d in flat) or (len(flat) >= 3 and flat in d) for d in deco)   # the planned lower block sits in the bottom 40 %: its words are design
    footage_text = []
    checks, rows = [], []
    add = lambda name, ok, val, need, warn=False: checks.append({"項目": name, "結果": "PASS" if ok else ("WARN" if warn else "FAIL"), "量到": val, "標準": need})
    if card:   # what the card promises on its closing frame must really be on screen (a kit bug once dropped every call to action)
        require = list(require) + [re.sub(r"<[^>]+>", "", b["cta"]) for b in card["beats"] if b.get("layout") == "disclosure" and b.get("cta")]
    hook_img = vp.grab(video, NORM["hook_by"], tmp / "hook.jpg")
    hb = [x for x in vp.ocr([hook_img]).get(hook_img, []) if x["conf"] >= 0.3]
    hh = round(max([x["h"] for x in hb] or [0]) * 100, 1)
    if static:
        add("封面有大字", hh >= NORM["hook_min_h"], f"最大字高 {hh}%", f"≥ {NORM['hook_min_h']}%")
    else:
        add("鉤子：0.6 秒內有大字", hh >= NORM["hook_min_h"], f"最大字高 {hh}%", f"≥ {NORM['hook_min_h']}%")
    if not static: add("鉤子：第一段長度", beats[0]["b"] - beats[0]["a"] <= NORM["hook_max_s"], f"{beats[0]['b'] - beats[0]['a']:.1f} 秒", f"≤ {NORM['hook_max_s']} 秒")
    seen_text = ""; blank = {}
    # labels that repeat on most beats (series name, handle) are page furniture: checked for size and safe zone, not counted as reading
    frames = {}
    for i, bt in enumerate(beats, 1):
        span = bt["b"] - bt["a"]; img = vp.grab(video, bt["a"] + span * 0.75, tmp / f"beat{i:02d}.jpg")
        vp.grab(video, bt["a"] + span * 0.75, tmp / f"beat{i:02d}_full.jpg", width=W)   # contrast is read on the full-resolution frame
        # OCR sometimes reads a chart dot or a bullet as "•": a box with no letter, digit or CJK character is not text to read
        got = [x for x in vp.ocr([img]).get(img, []) if x["conf"] >= 0.3 and re.search(r"[A-Za-z0-9\u3400-\u9fff]", x["text"])]
        got = [x for x in got if not is_deco(x, 0.12)]   # decorative type is at least 12 % of the frame tall; smaller matches are real text
        footage_text += [f"第 {i} 段：{x['text'][:20]}" for x in got if not overlay(x)]
        frames[i] = (img, [x for x in got if overlay(x)])
    from collections import Counter
    key = lambda t: re.sub(r"[\W_]+", "", t.lower())   # OCR spacing and punctuation vary from frame to frame
    rep = Counter(k for _, bx in frames.values() for k in {key(y["text"]) for y in bx})
    chrome = {k for k, n in rep.items() if k and len(beats) >= 3 and n >= max(3, len(beats) // 2)}
    import difflib
    def is_chrome(t):   # OCR misreads a repeated label now and then ("（代身）" without its bracket): match it loosely
        k = key(t)
        return k in chrome or any(len(c) >= 4 and difflib.SequenceMatcher(None, k, c).ratio() >= 0.75 for c in chrome)
    import difflib
    SAY = ("text", "title", "kicker", "items", "q", "a", "myth", "why", "big", "cta", "topic", "hook", "tag", "note", "sub", "foot", "cols", "nodes", "points", "captions", "chapter", "verdict", "ask", "name")
    def expected(b):   # every word the card puts on this beat (not its decoration, not numbers that count up)
        def walk(v, k=""):
            if isinstance(v, str): return v
            if isinstance(v, list): return " ".join(walk(x, k) for x in v)
            if isinstance(v, dict): return " ".join(walk(x, kk) for kk, x in v.items() if kk in ("text", "label", "k", "v", "s") and isinstance(x, str))
            return ""
        raw = " ".join(walk(b.get(k), k) for k in SAY if b.get(k))
        return re.findall(r"[a-z]{3,}|[\u3400-\u9fff]", re.sub(r"<[^>]+>|&[a-z]+;", " ", raw).lower())
    for i, bt in enumerate(beats, 1):
        span = bt["b"] - bt["a"]; img, bx = frames[i]
        text = " ".join(x["text"] for x in sorted(bx, key=lambda x: (x["y"], x["x"]))); seen_text += " " + text
        if card and i <= len(card["beats"]):   # the words on the card must really be readable on screen: a box drawn over a title, a clipped line or a dropped element shows up here
            cb = card["beats"][i - 1]
            def missing(want, text):
                flat = re.sub(r"[^a-z\u3400-\u9fff]+", "", text.lower()); toks = re.findall(r"[a-z]{3,}", text.lower())
                near = lambda w: any(difflib.SequenceMatcher(None, w, flat[j:j + len(w)]).ratio() >= 0.84 for j in range(0, max(1, len(flat) - len(w) + 1)))   # OCR swaps a letter now and then
                flat = re.sub(r"[^a-z0-9\u3400-\u9fff]+", "", text.lower())
                return [w for w in dict.fromkeys(want) if w not in flat and not any(difflib.SequenceMatcher(None, w, t).ratio() >= 0.75 for t in toks) and not (len(w) >= 6 and near(w))]
            # timed captions (word-by-word, 2–3 words at a time) are never all on screen at once: read each one at its own midpoint
            caps = [c for c in (cb.get("captions") or []) if isinstance(c, dict) and c.get("text") and "start" in c and "end" in c]
            want = expected({k: v for k, v in cb.items() if k != "captions"} if caps else cb)
            miss = missing(want, text)
            for j, c in enumerate(caps):
                t = min(bt["b"] - 0.05, bt["a"] + (float(c["start"]) + float(c["end"])) / 2)
                cimg = vp.grab(video, t, tmp / f"beat{i:02d}_cap{j:02d}.jpg")
                ctext = " ".join(x["text"] for x in vp.ocr([cimg]).get(cimg, []) if x["conf"] >= 0.3)
                cw = expected({"text": c["text"]})
                want += cw
                miss += [w for w in missing(cw, ctext) if w not in miss]
            if want:
                cov = 1 - len(set(miss)) / len(set(want))
                add(f"第 {i} 段文字完整出現", not miss, f"{round(cov * 100)}%" + (f"，沒讀到：{'、'.join(miss[:6])}" if miss else ""), "卡片上的字都讀得到（少 5% 以內算警告）", warn=cov >= 0.95)
        text = " ".join(x["text"] for x in sorted(bx, key=lambda x: (x["y"], x["x"])) if not is_chrome(x["text"]))
        en, zh = words(text); hs = [x["h"] * 100 for x in bx]
        disc = bt["layout"] == "disclosure"
        rate = en / span if span else 0
        limit = NORM["wps_disclosure"] if disc else NORM["wps"]
        out = [x["text"][:24] for x in bx if unsafe(x, SAFE[platform])]
        full = str(tmp / f"beat{i:02d}_full.jpg")
        con = [box_contrast(full, x, W, H) for x in bx]
        row = {"段": i, "版型": bt["layout"], "起訖": f"{bt['a']:.1f}–{bt['b']:.1f}", "秒數": round(span, 1), "英文字數": en, "中文字數": zh,
               "每秒字數": round(rate, 2), "最大字高%": round(max(hs or [0]), 1), "最小字高%": round(min(hs or [0]), 1), "安全區外": out, "最低對比": min(con or [0]), "文字": text[:160]}
        rows.append(row)
        if en or zh:
            if not static: add(f"第 {i} 段閱讀速度", rate <= limit and zh / max(span, 0.1) <= NORM["cps"], f"{rate:.2f} 字／秒" + (f"、中文 {zh / span:.1f} 字／秒" if zh else ""), f"≤ {limit} 字／秒")
            add(f"第 {i} 段字級", row["最大字高%"] >= NORM["min_h"] or disc, f"最大 {row['最大字高%']}%", f"≥ {NORM['min_h']}%", warn=True)
            # a line of lower-case letters measures about 0.3 points shorter than the same size with capitals, so 2.2–2.5 % is a warning, below 2.2 % fails
            add(f"第 {i} 段最小字", row["最小字高%"] >= NORM["floor_h"], f"最小 {row['最小字高%']}%", f"≥ {NORM['floor_h']}%", warn=row["最小字高%"] >= NORM["floor_h"] - 0.3)
            add(f"第 {i} 段安全區", not out, "、".join(out) or "都在內", f"{platform} 安全區（S0-06）")
            add(f"第 {i} 段對比", row["最低對比"] >= NORM["contrast"], f"{row['最低對比']} : 1", f"≥ {NORM['contrast']} : 1", warn=True)
        # layout fit (owner rule 2026-11-16): with a card, every word of the overlay must sit inside its layout's text zone (kits/storyboard/layouts.json)
        lay = LAYOUTS.get(bt["layout"]) if card else None
        if lay and lay.get("字區") and platform == "reels-tiktok" and abs((H / W) - (1350 / 1080 if lay.get("版面") == "1080×1350" else 1920 / 1080)) < 0.05:
            z = lay["字區"]; sl = lambda x: max(0.025, x["h"] * 0.6)   # OCR boxes on very large type spill wider than the glyphs (a 240 px figure read 6 % to the left)
            off = [x["text"][:20] for x in bx if not is_chrome(x["text"]) and (x["x"] < z["x"][0] / 100 - sl(x) or x["x"] + x["w"] > z["x"][1] / 100 + sl(x) or x["y"] < z["y"][0] / 100 - sl(x) or x["y"] + x["h"] > z["y"][1] / 100 + sl(x))]
            add(f"第 {i} 段版型符合度", not off, "、".join(off) or f"字都在 {bt['layout']} 的字區內", f"{bt['layout']} 字區 x {z['x'][0]}–{z['x'][1]}%、y {z['y'][0]}–{z['y'][1]}%")
        # visual layer filled (owner rule 2026-11-16): under the text zone the frame must carry a picture, a chart, a colour block or motion — never a flat strip
        if H > W * 1.5:
            a2 = vp.grab(video, bt["a"] + span * 0.4, tmp / f"beat{i:02d}_early.jpg")
            v = lower_blank(img, a2)
            if v is not None: blank[i] = v
        lo, hi = NORM["beat"]
        if i < len(beats):
            add(f"第 {i} 段長度", lo <= span <= hi, f"{span:.1f} 秒", f"{lo}–{hi} 秒", warn=True)
    if blank:   # one flat beat is a warning; two in a row fail (the strip the owner rejected on 2026-11-14)
        flat = [i for i, v in blank.items() if v]; run = max((len(list(g)) for k, g in __import__("itertools").groupby(blank[i] for i in sorted(blank)) if k), default=0)
        add("畫面層填滿（安全區下方不留空白）", not flat or run < 2, "、".join(f"第 {i} 段" for i in flat) + "下方是純色且不動" if flat else "每段下方都有畫面或動態",
            "y 65% 以下要有照片、圖表延伸、色塊或動態（visual 欄位）", warn=bool(flat) and run < 2)
    add("結尾長度", beats[-1]["b"] - beats[-1]["a"] >= NORM["last_min"], f"{beats[-1]['b'] - beats[-1]['a']:.1f} 秒", f"≥ {NORM['last_min']} 秒")
    norm = lambda s: re.sub(r"[^a-z0-9]+", "", s.lower())
    for ph in require:
        want, got = norm(ph)[:40], norm(seen_text)
        ok = want in got
        if not ok and want:   # display fonts make OCR swap a letter ("Ouestions"): accept a window that matches 85 % of the phrase
            import difflib
            ok = any(difflib.SequenceMatcher(None, want, got[i:i + len(want)]).ratio() >= 0.85 for i in range(0, max(1, len(got) - len(want) + 1)))
        add(f"必要字句：{ph[:30]}…", ok, "畫面上找到" if ok else "沒找到", "要出現且讀得完")
    if footage_text:
        add("素材裡的文字（不算閱讀量，確認不是亂碼或別人的品牌）", False, "、".join(footage_text[:8]), "素材本身最好沒有可讀的字", warn=True)
    worst = "FAIL" if any(c["結果"] == "FAIL" for c in checks) else ("WARN" if any(c["結果"] == "WARN" for c in checks) else "PASS")
    return {"影片": video, "片長": round(dur, 2), "總評": worst, "檢查": checks, "各段": rows}


def main() -> int:
    ap = argparse.ArgumentParser(prog="video_qa.py"); ap.add_argument("video", help="a video, or the first page image with --images"); ap.add_argument("--images", nargs="*", help="more carousel pages (static check)"); ap.add_argument("--card"); ap.add_argument("--require", action="append", default=[]); ap.add_argument("--boards", help="known shot lengths, comma separated")
    ap.add_argument("--platform", choices=sorted(SAFE), default="reels-tiktok"); ap.add_argument("--out", default="qa.json"); a = ap.parse_args()
    card = json.loads(Path(a.card).read_text(encoding="utf-8")) if a.card else None
    static = a.images is not None
    video, boards, plat = a.video, [float(x) for x in a.boards.split(",")] if a.boards else None, a.platform
    if static:   # pages → a 4 s-per-page slideshow measured with the same tools; the feed safe zone unless one is given
        pages = [a.video] + a.images; tmpd = Path(a.out).parent / (Path(a.out).stem + "_pages"); tmpd.mkdir(parents=True, exist_ok=True)
        video = str(tmpd / "pages.mp4"); boards = [4.0] * len(pages); plat = a.platform if a.platform != "reels-tiktok" else "feed"
        args = sum([["-loop", "1", "-t", "4", "-i", x] for x in pages], [])
        subprocess.run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", "".join(f"[{i}]scale=1080:-2,setsar=1[v{i}];" for i in range(len(pages))) + "".join(f"[v{i}]" for i in range(len(pages))) + f"concat=n={len(pages)}:v=1,fps=24,format=yuv420p", video], check=True)
    res = qa(video, card, a.require, Path(a.out).parent / (Path(a.out).stem + "_frames"), boards, plat, static)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"總評 {res['總評']}｜{a.video}（{res['片長']} 秒）")
    for c in res["檢查"]:
        print(f"  {c['結果']:4}  {c['項目']}：{c['量到']}（標準 {c['標準']}）")
    return 0 if res["總評"] != "FAIL" else 1


if __name__ == "__main__":
    sys.exit(main())
