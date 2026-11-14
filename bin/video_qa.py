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
        "feed": (0.05, 0.04, 0.95, 0.96, 1.0, 1.0)}   # static carousel pages (1080×1350): no platform UI on top, keep a margin


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
    px = subprocess.run(["ffmpeg", "-v", "error", "-i", img, "-vf", f"crop={w}:{h}:{x}:{y},scale=48:12", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    ls = sorted(lum(tuple(px[i:i + 3])) for i in range(0, len(px) - 2, 3))
    if not ls:
        return 0.0
    lo, hi = ls[int(len(ls) * 0.03)], ls[int(len(ls) * 0.97)]
    return round((hi + 0.05) / (lo + 0.05), 1)


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
    checks, rows = [], []
    add = lambda name, ok, val, need, warn=False: checks.append({"項目": name, "結果": "PASS" if ok else ("WARN" if warn else "FAIL"), "量到": val, "標準": need})
    hook_img = vp.grab(video, NORM["hook_by"], tmp / "hook.jpg")
    hb = [x for x in vp.ocr([hook_img]).get(hook_img, []) if x["conf"] >= 0.3]
    hh = round(max([x["h"] for x in hb] or [0]) * 100, 1)
    if static:
        add("封面有大字", hh >= NORM["hook_min_h"], f"最大字高 {hh}%", f"≥ {NORM['hook_min_h']}%")
    else:
        add("鉤子：0.6 秒內有大字", hh >= NORM["hook_min_h"], f"最大字高 {hh}%", f"≥ {NORM['hook_min_h']}%")
    if not static: add("鉤子：第一段長度", beats[0]["b"] - beats[0]["a"] <= NORM["hook_max_s"], f"{beats[0]['b'] - beats[0]['a']:.1f} 秒", f"≤ {NORM['hook_max_s']} 秒")
    seen_text = ""
    # labels that repeat on most beats (series name, handle) are page furniture: checked for size and safe zone, not counted as reading
    frames = {}
    for i, bt in enumerate(beats, 1):
        span = bt["b"] - bt["a"]; img = vp.grab(video, bt["a"] + span * 0.75, tmp / f"beat{i:02d}.jpg")
        frames[i] = (img, [x for x in vp.ocr([img]).get(img, []) if x["conf"] >= 0.3 and x["text"].strip()])
    from collections import Counter
    key = lambda t: re.sub(r"[\W_]+", "", t.lower())   # OCR spacing and punctuation vary from frame to frame
    rep = Counter(k for _, bx in frames.values() for k in {key(y["text"]) for y in bx})
    chrome = {k for k, n in rep.items() if k and len(beats) >= 3 and n >= max(3, len(beats) // 2)}
    for i, bt in enumerate(beats, 1):
        span = bt["b"] - bt["a"]; img, bx = frames[i]
        text = " ".join(x["text"] for x in sorted(bx, key=lambda x: (x["y"], x["x"]))); seen_text += " " + text
        text = " ".join(x["text"] for x in sorted(bx, key=lambda x: (x["y"], x["x"])) if key(x["text"]) not in chrome)
        en, zh = words(text); hs = [x["h"] * 100 for x in bx]
        disc = bt["layout"] == "disclosure"
        rate = en / span if span else 0
        limit = NORM["wps_disclosure"] if disc else NORM["wps"]
        out = [x["text"][:24] for x in bx if unsafe(x, SAFE[platform])]
        iw, ih = 540, int(round(H * 540 / W / 2) * 2)   # vp.grab saves frames 540 px wide
        con = [box_contrast(img, x, iw, ih) for x in bx]
        row = {"段": i, "版型": bt["layout"], "起訖": f"{bt['a']:.1f}–{bt['b']:.1f}", "秒數": round(span, 1), "英文字數": en, "中文字數": zh,
               "每秒字數": round(rate, 2), "最大字高%": round(max(hs or [0]), 1), "最小字高%": round(min(hs or [0]), 1), "安全區外": out, "最低對比": min(con or [0]), "文字": text[:160]}
        rows.append(row)
        if en or zh:
            if not static: add(f"第 {i} 段閱讀速度", rate <= limit and zh / max(span, 0.1) <= NORM["cps"], f"{rate:.2f} 字／秒" + (f"、中文 {zh / span:.1f} 字／秒" if zh else ""), f"≤ {limit} 字／秒")
            add(f"第 {i} 段字級", row["最大字高%"] >= NORM["min_h"] or disc, f"最大 {row['最大字高%']}%", f"≥ {NORM['min_h']}%", warn=True)
            add(f"第 {i} 段最小字", row["最小字高%"] >= NORM["floor_h"], f"最小 {row['最小字高%']}%", f"≥ {NORM['floor_h']}%")
            add(f"第 {i} 段安全區", not out, "、".join(out) or "都在內", f"{platform} 安全區（S0-06）")
            add(f"第 {i} 段對比", row["最低對比"] >= NORM["contrast"], f"{row['最低對比']} : 1", f"≥ {NORM['contrast']} : 1", warn=True)
        lo, hi = NORM["beat"]
        if i < len(beats):
            add(f"第 {i} 段長度", lo <= span <= hi, f"{span:.1f} 秒", f"{lo}–{hi} 秒", warn=True)
    add("結尾長度", beats[-1]["b"] - beats[-1]["a"] >= NORM["last_min"], f"{beats[-1]['b'] - beats[-1]['a']:.1f} 秒", f"≥ {NORM['last_min']} 秒")
    norm = lambda s: re.sub(r"[^a-z0-9]+", "", s.lower())
    for ph in require:
        ok = norm(ph)[:40] in norm(seen_text)
        add(f"必要字句：{ph[:30]}…", ok, "畫面上找到" if ok else "沒找到", "要出現且讀得完")
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
