#!/usr/bin/env python3
"""Measure a video with ffmpeg only (no Python packages), for two jobs:

  footage    an inventory of raw footage before editing: levels, pauses, exposure swing, shake hint,
             resolution headroom, problems mapped to handbook entries, and a draft spec card whose
             shots are cut at the pauses (S3-17) with the spoken words (S5-16) when --words is given.
  breakdown  a shot-by-shot breakdown of a reference video for imitation: cuts, key frames,
             contact sheet, brightness, saturation, warm/cool, motion, pacing, plus a breakdown card
             with the measurable fields filled and the vocabulary fields left for the agent to fill
             from the key frames (KEEP / CHANGE / SKIP per dimension, S1-04 / S1-08).

--words takes a JSON list of [word, start, end] from any speech recogniser.
"""
from __future__ import annotations

import argparse, colorsys, json, math, re, subprocess, sys
from pathlib import Path


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.stdout + p.stderr


def probe(path: str) -> dict:
    out = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path],
                                    capture_output=True, text=True).stdout)
    v = next((s for s in out["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in out["streams"] if s["codec_type"] == "audio"), None)
    num, den = (v.get("r_frame_rate", "30/1").split("/") + ["1"])[:2]
    return {"duration": float(out["format"]["duration"]), "width": int(v.get("width", 0)), "height": int(v.get("height", 0)),
            "fps": round(float(num) / float(den or 1), 2), "audio": a is not None}


def frame_stats(path: str, fps: float = 4, crop_top: bool = False) -> list[dict]:
    """signalstats per sampled frame: YAVG (brightness), SATAVG, UAVG/VAVG (colour cast), YDIF (change from the previous frame)."""
    vf = f"fps={fps},scale=320:-2" + (",crop=iw:ih*0.2:0:0" if crop_top else "") + ",signalstats,metadata=print:file=-"
    txt = run(["ffmpeg", "-v", "error", "-i", path, "-vf", vf, "-an", "-f", "null", "-"])
    rows, cur = [], {}
    for line in txt.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            if cur:
                rows.append(cur)
            cur = {"t": float(m[1])}
        m = re.search(r"lavfi\.signalstats\.(YAVG|SATAVG|SATHIGH|UAVG|VAVG|YDIF)=([\d.]+)", line)
        if m:
            cur[m[1]] = float(m[2])
    if cur:
        rows.append(cur)
    return rows


HUES = [(15, "紅"), (38, "橘"), (70, "黃"), (165, "綠"), (200, "青"), (260, "藍"), (320, "紫"), (360, "紅")]


def colour_stats(path: str, fps: float = 2) -> list[dict]:
    """Share of clearly coloured pixels and their main hue per sampled frame; averages hide small accent colours."""
    w, h = 36, 64
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    n = w * h * 3
    out = []
    for k in range(len(raw) // n):
        fr = raw[k * n:(k + 1) * n]
        col, hues = 0, {}
        for i in range(0, n, 3):
            r, g, b = fr[i] / 255, fr[i + 1] / 255, fr[i + 2] / 255
            hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
            if ss > 0.35 and 0.15 < ll < 0.9:
                col += 1
                name = next(nm for lim, nm in HUES if hh * 360 <= lim)
                hues[name] = hues.get(name, 0) + 1
        out.append({"t": round(k / fps, 2), "colour": col / (w * h), "hue": max(hues, key=hues.get) if hues else ""})
    return out


def loudness(path: str) -> dict:
    txt = run(["ffmpeg", "-v", "info", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"])
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", txt)
    peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", txt)
    env = envelope(path)
    lv = sorted(v for _, v in env)
    return {"lufs": float(i[-1]) if i else None, "peak": float(peak[-1]) if peak else None,
            "floor": round(lv[int(len(lv) * 0.1)], 1) if lv else None, "speech": round(lv[int(len(lv) * 0.9)], 1) if lv else None,
            "_env": env}


def envelope(path: str, win: float = 0.05) -> list[tuple[float, float]]:
    """RMS level per 50 ms window, so pauses can be judged against this recording's own noise floor (S4-12)."""
    n = int(16000 * win)
    txt = run(["ffmpeg", "-v", "error", "-i", path, "-af", f"aresample=16000,asetnsamples={n},astats=metadata=1:reset=1,"
               "ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-", "-f", "null", "-"])
    out, t = [], None
    for line in txt.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t = float(m[1])
        m = re.search(r"RMS_level=(-?[\d.]+|-inf)", line)
        if m and t is not None:
            out.append((t, -120.0 if m[1] == "-inf" else float(m[1])))
    return out


def pauses(env: list[tuple[float, float]], floor: float | None, speech: float | None, min_len: float = 0.22) -> list[tuple[float, float]]:
    """Runs of windows quieter than a third of the way from floor to speech level."""
    if not env or floor is None:
        return []
    thr = floor + max(6.0, ((speech or floor + 20) - floor) / 3)
    out, start = [], None
    step = env[1][0] - env[0][0] if len(env) > 1 else 0.05
    for t, v in env + [(env[-1][0] + step, 0.0)]:
        if v < thr and start is None:
            start = t
        elif v >= thr and start is not None:
            if t - start >= min_len:
                out.append((round(start, 2), round(t, 2)))
            start = None
    return out


def cuts(path: str, threshold: float = 10) -> list[float]:
    txt = run(["ffmpeg", "-v", "info", "-i", path, "-vf", f"scdet=threshold={threshold},metadata=print:file=-", "-an", "-f", "null", "-"])
    ts = [float(x) for x in re.findall(r"lavfi\.scd\.time=([\d.]+)", txt)]
    out = []
    for t in ts:
        if not out or t - out[-1] > 0.3:
            out.append(round(t, 2))
    return out


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def tone_hints(rows: list[dict], cs: list[dict] | None = None) -> dict:
    y, s = mean([r.get("YAVG", 0) for r in rows]), mean([r.get("SATAVG", 0) for r in rows])
    u, v = mean([r.get("UAVG", 128) for r in rows]), mean([r.get("VAVG", 128) for r in rows])
    d = mean([r.get("YDIF", 0) for r in rows])
    hints = {}
    hints["布光"] = "高調" if y > 150 else ("低調" if y < 70 else None)
    hints["色彩"] = "暖色調" if v - u > 6 else ("冷色調" if u - v > 6 else "中性")
    hi = mean([r.get("SATHIGH", 0) for r in rows])
    share = mean([c["colour"] for c in cs]) if cs else None
    accent = ""
    if cs:
        tally = {}
        for c in cs:
            if c["hue"]:
                tally[c["hue"]] = tally.get(c["hue"], 0) + 1
        accent = max(tally, key=tally.get) if tally else ""
    if share is not None and share < 0.01:
        hints["色彩"] = "黑白"
    elif share is not None and share < 0.2:
        hints["色彩"] = "單色強調" + (f"（{accent}）" if accent else "")
    elif hi < 12:
        hints["色彩"] = "黑白"
    elif s < 25 and hi > 45:
        hints["色彩"] = "單色強調"
    elif s < 25:
        hints["色彩"] = "低飽和"
    elif s > 60:
        hints["色彩"] = "高飽和"
    hints["運鏡"] = "固定" if d < 1.0 else None
    return {k: v for k, v in hints.items() if v} | {"_量測": {"亮度": round(y), "飽和": round(s), "亮部飽和": round(hi), "彩色占比": round(share, 3) if share is not None else None, "U": round(u), "V": round(v), "畫面變化": round(d, 2)}}


ASR_SNIPPET = r"""
import json, sys
from faster_whisper import WhisperModel
m = WhisperModel(sys.argv[2], device="cpu", compute_type="int8")
out = []
for wav in sys.argv[3:]:
    prompt = "以下是繁體中文的口語句子。" if sys.argv[1] == "zh" else None
    segs, _ = m.transcribe(wav, language=sys.argv[1] or None, beam_size=5, vad_filter=False, condition_on_previous_text=False, initial_prompt=prompt)
    out.append("".join(x.text for x in segs).strip())
print(json.dumps(out, ensure_ascii=False))
"""


def chunk_asr(path: str, chunks: list[tuple[float, float]], asr_python: str, model: str, lang: str, tmp: Path) -> list[str]:
    """Transcribe each speech chunk on its own, so a word can never drift across a pause (caption-sync lesson)."""
    tmp.mkdir(parents=True, exist_ok=True)
    wavs = []
    for k, (a, b) in enumerate(chunks):
        w = tmp / f"chunk{k:02d}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, a - 0.05):.3f}", "-to", f"{b + 0.05:.3f}", "-i", path,
                        "-ac", "1", "-ar", "16000", str(w)])
        wavs.append(str(w))
    p = subprocess.run([asr_python, "-c", ASR_SNIPPET, lang, model, *wavs], capture_output=True, text=True)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        sys.stderr.write(p.stderr[-800:])
        return [""] * len(chunks)


HALLUCINATION = re.compile(r"字幕|by\s*\S+|訂閱|订阅|點贊|点赞|謝謝觀看|谢谢观看|Amara|請不吝", re.I)
FILLERS = re.compile(r"^(呃|嗯|啊|欸|那個|um+|uh+|er+)[\s，,]*", re.I)


def clean_caption(txt: str, dur: float) -> tuple[str, list[str]]:
    flags = []
    if HALLUCINATION.search(txt) and dur < 1.0:
        return "", ["短片段疑似語音辨識幻覺，已清空；請聽一次確認"]
    m = FILLERS.match(txt)
    if m:
        flags.append(f"開頭有贅詞「{m[1]}」，建議剪掉")
        txt = txt[m.end():]
    return txt.strip(), flags


def speech_chunks(ps: list, dur: float) -> list[tuple[float, float]]:
    out, t = [], 0.0
    for a, b in ps:
        if a - t >= 0.15:
            out.append((round(t, 2), round(a, 2)))
        t = b
    if dur - t >= 0.15:
        out.append((round(t, 2), round(dur, 2)))
    return out


def words_between(words: list, a: float, b: float) -> str:
    return "".join(w[0] for w in words if a <= w[1] < b).strip()


def footage(path: str, words: list | None, out_dir: Path, asr: dict | None = None) -> dict:
    info = probe(path)
    lv = loudness(path) if info["audio"] else {}
    ps = pauses(lv.pop("_env", []), lv.get("floor"), lv.get("speech")) if info["audio"] else []
    rows = frame_stats(path)
    top = frame_stats(path, crop_top=True)
    ys = [r.get("YAVG", 0) for r in rows]
    shake = mean([r.get("YDIF", 0) for r in top[1:]])
    scale = max(1080 / max(1, min(info["width"], info["height"])), 1920 / max(1, max(info["width"], info["height"])))
    issues = []
    if shake > 3:
        issues.append(f"背景晃動明顯（畫面上緣每格平均變化 {shake:.1f}）：手持；做去背特效或大字在頭後會失敗（S4-32、S4-27）")
    if ys and max(ys) - min(ys) > 40:
        issues.append(f"曝光前後不一致（亮度 {min(ys):.0f}–{max(ys):.0f}）：前後鏡接起來會跳（S4-27）")
    if scale > 1.01:
        issues.append(f"輸出 1080×1920 需要放大 {scale:.2f} 倍，再推近會更軟；推近要高解析素材（S5-03、S4-23）")
    if lv.get("peak") is not None and lv["peak"] < -12:
        issues.append(f"錄音很小聲（最大 {lv['peak']} dBFS）：停頓門檻要用相對底噪，混音前先拉到約 -16 LUFS（S4-12、S7-11）")
    if lv.get("lufs") is not None and lv["lufs"] < -30:
        issues.append(f"整體響度 {lv['lufs']} LUFS，遠低於 -16")
    talk = [(a, b) for a, b in ps if b - a >= 0.22 and a > 0.05 and b < info["duration"] - 0.05]
    cut_s = sum(max(0, (b - a) - 0.1) for a, b in ps)
    # draft shots: split at pauses of 0.5 s or more, at the pause mid-point (S3-17)
    marks = [0.0] + [round((a + b) / 2, 2) for a, b in ps if b - a >= 0.5 and 0.5 < a < info["duration"] - 0.5] + [round(info["duration"], 2)]
    chunks = speech_chunks(ps, info["duration"])
    texts = chunk_asr(path, chunks, asr["python"], asr["model"], asr["lang"], out_dir / "chunks") if asr and chunks else None
    captions = []
    for k, (a, b) in enumerate(chunks):
        txt = texts[k] if texts else (words_between(words, a, b) if words else "")
        txt, flags = clean_caption(txt, b - a)
        if not txt and words and texts:
            txt = words_between(words, a, b)
        cap = {"起": a, "訖": b, "字": txt}
        if flags:
            cap["提醒"] = flags
        captions.append(cap)
    shots = []
    for i, (a, b) in enumerate(zip(marks, marks[1:]), 1):
        shot = {"編號": i, "秒數": round(b - a, 2), "內容": f"原片 {a:.2f}–{b:.2f} 秒"}
        lines = [c["字"] for c in captions if a <= (c["起"] + c["訖"]) / 2 < b and c["字"]]
        if lines:
            shot["台詞"] = " / ".join(lines)
        shots.append(shot)
    card = {"片名": Path(path).stem, "畫幅": "直式 9:16" if info["height"] >= info["width"] else "16:9", "格率": 30,
            "片長": round(info["duration"], 2), "調性": "", "全片": {}, "鏡頭": shots,
            "剪輯": {"保留段落": keep_segments(ps, info["duration"]), "說明": "剪掉超過 0.22 秒的停頓，各留 0.05 秒（S4-12）；剪後片長要重算"},
            "字幕組": captions}
    report = {"檔案": path, "規格": info, "響度": lv, "停頓": ps, "可剪掉秒數": round(cut_s, 2), "說話中的停頓數": len(talk),
              "亮度範圍": [round(min(ys)) if ys else None, round(max(ys)) if ys else None], "晃動指標": round(shake, 2),
              "需要放大": round(scale, 2), "問題": issues, "畫面風格量測": tone_hints(rows)}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "edit.sh").write_text(edit_script(path, card["剪輯"]["保留段落"], info), encoding="utf-8")
    report["剪後片長"] = round(sum(b - a for a, b in card["剪輯"]["保留段落"]), 2)
    (out_dir / "footage.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "draft_card.json").write_text(json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"report": report, "card": card}


def edit_script(path: str, keep: list, info: dict) -> str:
    """Cut the pauses and scale to the output size, then measure and set speech to -16 LUFS (two passes; one-pass loudnorm undershoots, S4-12, S7-11)."""
    sel = "+".join(f"between(t,{a},{b})" for a, b in keep)
    w, h = (1080, 1920) if info["height"] >= info["width"] else (1920, 1080)
    vf = f"select='{sel}',setpts=N/FRAME_RATE/TB,scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h}"
    af = f"aselect='{sel}',asetpts=N/SR/TB,highpass=f=80"
    return ("#!/bin/sh\n# 剪掉停頓、放大到輸出尺寸、人聲量測後拉到 -16 LUFS。輸出預設 cut.mp4；完成後用 video_probe.py footage 複查。\nset -e\n"
            'OUT="${1:-cut.mp4}"; TMP="${OUT%.mp4}.pass1.mp4"\n'
            f'ffmpeg -v error -y -i "{path}" -vf "{vf}" -af "{af}" -r 30 -c:v libx264 -crf 18 -preset medium -c:a pcm_s16le -f mov "$TMP"\n'
            'I=$(ffmpeg -v info -i "$TMP" -af ebur128 -f null - 2>&1 | grep -E "^ +I:" | tail -1 | awk \'{print $2}\')\n'
            'G=$(awk -v i="$I" \'BEGIN{printf "%.2f", -16 - i}\')\n'
            'echo "第一遍 $I LUFS，增益 $G dB"\n'
            'ffmpeg -v error -y -i "$TMP" -c:v copy -af "volume=${G}dB,alimiter=limit=0.84:level=false" -c:a aac -b:a 192k "$OUT"\n'
            'rm -f "$TMP"\n')


def keep_segments(ps: list, dur: float) -> list[list[float]]:
    keep, t = [], 0.0
    for a, b in ps:
        a2, b2 = (a + 0.05 if a > 0 else 0.0), b - 0.05
        if a2 > t:
            keep.append([round(t, 3), round(a2, 3)])
        t = max(t, b2)
    if t < dur:
        keep.append([round(t, 3), round(dur, 3)])
    return keep


# ---------------------------------------------------------------- measurement for storyboard breakdowns (text boxes, colours, motion)
def ocr_bin() -> str | None:
    """The Vision OCR helper (bin/ocr.swift), compiled once into ~/.cache/playbook/ocr. macOS only."""
    exe = Path.home() / ".cache/playbook/ocr"
    src = Path(__file__).with_name("ocr.swift")
    if not exe.exists() or exe.stat().st_mtime < src.stat().st_mtime:
        exe.parent.mkdir(parents=True, exist_ok=True)
        if subprocess.run(["swiftc", "-O", str(src), "-o", str(exe)], capture_output=True).returncode != 0:
            return None
    return str(exe)


def ocr(images: list[str]) -> dict[str, list[dict]]:
    exe = ocr_bin()
    if not exe or not images:
        return {}
    out = subprocess.run([exe, *images], capture_output=True, text=True).stdout
    return {d["file"]: d["boxes"] for d in map(json.loads, filter(None, out.splitlines()))}


def text_stats(boxes: list[dict]) -> dict:
    """Blocks, words (Latin) and characters (CJK), tallest line as a share of the frame height, area covered, and where the text sits."""
    boxes = [b for b in boxes if b.get("conf", 1) >= 0.3 and b["text"].strip()]
    if not boxes:
        return {"文字區塊": 0, "英文字數": 0, "中文字數": 0, "最大字高%": 0, "文字面積%": 0, "位置": []}
    cjk = sum(len(re.findall(r"[\u3400-\u9fff]", b["text"])) for b in boxes)
    latin = sum(len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’.%$-]*", b["text"])) for b in boxes)
    zone = lambda y: "上" if y < 0.33 else ("中" if y < 0.66 else "下")
    return {"文字區塊": len(boxes), "英文字數": latin, "中文字數": cjk, "最大字高%": round(max(b["h"] for b in boxes) * 100, 1),
            "文字面積%": round(sum(b["w"] * b["h"] for b in boxes) * 100, 1),
            "位置": [{"字": b["text"][:40], "x": round(b["x"], 3), "y": round(b["y"], 3), "w": round(b["w"], 3), "h": round(b["h"], 3), "區": zone(b["y"] + b["h"] / 2)}
                   for b in sorted(boxes, key=lambda b: (b["y"], b["x"]))]}


def raw_pixels(img: str, w: int, h: int, fmt: str) -> bytes:
    return subprocess.run(["ffmpeg", "-v", "error", "-i", img, "-vf", f"scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", fmt, "-"], capture_output=True).stdout


def palette(img: str, n: int = 4) -> list[str]:
    """Main colours: 32×56 pixels quantised to 4 levels per channel, most common first (pure Python, no numpy)."""
    px = raw_pixels(img, 32, 56, "rgb24"); counts: dict = {}
    for i in range(0, len(px) - 2, 3):
        key = tuple(v // 64 for v in px[i:i + 3])
        counts.setdefault(key, []).append(px[i:i + 3])
    top = sorted(counts.values(), key=len, reverse=True)[:n]
    return ["#%02X%02X%02X" % tuple(sum(p[c] for p in grp) // len(grp) for c in range(3)) for grp in top]


def motion(img_a: str, img_b: str) -> float:
    """Mean absolute grey difference between two frames (0–100)."""
    a, b = raw_pixels(img_a, 32, 56, "gray"), raw_pixels(img_b, 32, 56, "gray")
    return round(sum(abs(x - y) for x, y in zip(a, b)) / max(1, len(a)) / 2.55, 1) if a and b else 0.0


def grab(path: str, t: float, out: Path) -> str:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, t):.2f}", "-i", path, "-frames:v", "1", "-vf", "scale=540:-2", str(out)])
    return str(out)


def breakdown(path: str, words: list | None, out_dir: Path, threshold: float, boards: list[float] | None = None, measure: bool = False) -> dict:
    info = probe(path)
    cs = cuts(path, threshold)
    if boards:   # known shot lengths (e.g. a template's published per-scene seconds), scaled to the file's real length
        k = info["duration"] / sum(boards); acc, bounds = 0.0, [0.0]
        for d in boards:
            acc += d * k; bounds.append(round(acc, 2))
    else:
        bounds = [0.0] + cs + [round(info["duration"], 2)]
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = frame_stats(path)
    cols = colour_stats(path)
    shots, sheet = [], []
    for i, (a, b) in enumerate(zip(bounds, bounds[1:]), 1):
        if b - a < 0.1:
            continue
        seg = [r for r in rows if a <= r["t"] < b] or rows[:1]
        cseg = [c for c in cols if a <= c["t"] < b] or cols[:1]
        mid = round((a + b) / 2, 2)
        frame = out_dir / f"shot{i:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(mid), "-i", path, "-frames:v", "1", "-vf", "scale=360:-2", str(frame)])
        sheet.append(str(frame))
        shot = {"編號": i, "起": a, "訖": b, "秒數": round(b - a, 2), "關鍵格": frame.name, "量測": tone_hints(seg, cseg)["_量測"],
                "建議值": {k: v for k, v in tone_hints(seg, cseg).items() if k != "_量測"},
                "畫面類型": "（實拍／AI 生成／動態圖形）", "景別": "", "視角與機位": "", "運鏡": "", "構圖": [], "布光": [], "色彩": [], "質感": [], "氛圍": "",
                "主體動作與表演": "", "文字與字幕": [], "動態圖像": [], "過場到下一鏡": "", "聲音設計": [],
                "作用": "（這一鏡在整支片裡負責什麼：開場、證據、轉折、CTA…）", "保留或改": {}}
        if boards:
            shot["內部切點"] = [c for c in cs if a + 0.15 < c < b - 0.15]
        if measure:
            fin, fmid, fout = (grab(path, a + min(0.2, (b - a) / 4), out_dir / f"shot{i:02d}_in.jpg"), grab(path, mid, out_dir / f"shot{i:02d}_mid.jpg"),
                               grab(path, b - min(0.2, (b - a) / 4), out_dir / f"shot{i:02d}_out.jpg"))
            boxes = ocr([fin, fmid, fout])
            shot["量測"].update({"文字（進場）": text_stats(boxes.get(fin, [])), "文字（中段）": text_stats(boxes.get(fmid, [])),
                               "文字（出場）": text_stats(boxes.get(fout, [])), "主色": palette(fmid), "動態強度": motion(fin, fout)})
            if b < info["duration"] - 0.3:
                shot["交界格"] = [Path(grab(path, b - 0.25, out_dir / f"cut{i:02d}_a.jpg")).name, Path(grab(path, b + 0.25, out_dir / f"cut{i:02d}_b.jpg")).name]
            shot["版型"] = "（單一畫面：主體在哪、幾個文字區塊與層級、背景處理）"
            shot["串場"] = "（到下一鏡怎麼接：過場類型＋連接手法）"
        if words:
            shot["台詞"] = words_between(words, a, b)
        shots.append(shot)
    lens = [s["秒數"] for s in shots]
    avg = mean(lens)
    pace = "快節奏" if avg < 1.5 else ("中節奏" if avg < 2.5 else "慢節奏")
    if sheet:
        cols = min(5, len(sheet))
        inputs = sum([["-i", f] for f in sheet], [])
        rows_n = math.ceil(len(sheet) / cols)
        pad = cols * rows_n - len(sheet)
        filt = "".join(f"[{k}]scale=360:640:force_original_aspect_ratio=decrease,pad=360:640:(ow-iw)/2:(oh-ih)/2:white[v{k}];" for k in range(len(sheet)))
        filt += "".join(f"color=white:s=360x640:d=1[p{k}];" for k in range(pad))
        cells = [f"[v{k}]" for k in range(len(sheet))] + [f"[p{k}]" for k in range(pad)]
        layout = "|".join(f"{(k % cols) * 360}_{(k // cols) * 640}" for k in range(len(cells)))
        filt += "".join(cells) + f"xstack=inputs={len(cells)}:layout={layout}"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", filt, "-frames:v", "1", str(out_dir / "contact_sheet.jpg")])
    card = {"來源": path, "片長": round(info["duration"], 2), "鏡數": len(shots), "平均每鏡秒數": round(avg, 2),
            "每分鐘切點": round(len(cs) / max(info["duration"], 1) * 60, 1), "剪輯節奏": pace,
            "說明": "量測欄是程式量的；畫面類型先判斷（螢幕、介面、文字卡＝動態圖形，布光與運鏡的建議值不適用）；其餘維度請看 contact_sheet.jpg 和各鏡關鍵格，用 `pb.py vocab <維度>` 的值填；"
                    "每個維度在「保留或改」標 KEEP、CHANGE 或 SKIP，只借結構和節奏，不抄畫面和文案（S1-04、S1-07）。"
                    "填好後 `pb.py breakdown --to-spec <拆解卡>` 轉成模仿用的規格卡。",
            "結構": [], "鏡頭": shots}
    card["結構說明"] = "依鏡頭角色分段填寫 結構：[{\"段\": \"鉤子\", \"鏡\": [1], \"秒數\": 2.5, \"做什麼\": \"…\"}, …]；to_spec 會帶進規格卡的 參考結構"
    (out_dir / "breakdown.json").write_text(json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
    return card


def to_spec(card: dict) -> dict:
    """KEEP copies the reference's value; CHANGE drops it (the tone preset fills it in) and notes the original in 備註; SKIP drops it silently.
    作用 becomes the new shot's 內容; mark it CHANGE to rewrite the content and keep only the job the shot does."""
    shots = []
    skip = ("編號", "起", "訖", "秒數", "關鍵格", "量測", "建議值", "作用", "保留或改", "台詞")
    for s in card["鏡頭"]:
        rule = s.get("保留或改", {})
        job = s.get("作用", "")
        new = {"編號": s["編號"], "秒數": s["秒數"],
               "內容": f"（改寫內容，保留作用）{job}" if rule.get("作用") == "CHANGE" else job}
        notes = []
        for k, v in s.items():
            if k in skip or not v:
                continue
            r = rule.get(k, "KEEP")
            if r == "KEEP":
                new[k] = v
            elif r == "CHANGE":
                notes.append(f"{k}（參考片：{'、'.join(v) if isinstance(v, list) else v}）")
        if notes:
            new["備註"] = "要改：" + "；".join(notes)
        shots.append(new)
    return {"片名": "模仿：" + Path(card.get("來源", "")).stem, "畫幅": "直式 9:16", "格率": 30,
            "片長": round(sum(s["秒數"] for s in shots), 2), "調性": "", "全片": {}, "鏡頭": shots,
            "參考結構": card.get("結構", [])}


def main() -> int:
    ap = argparse.ArgumentParser(prog="video_probe.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("footage", "breakdown"):
        p = sub.add_parser(name)
        p.add_argument("video", nargs="?")
        p.add_argument("--words")
        p.add_argument("--out", default="probe-out")
        p.add_argument("--asr-python", help="a Python that has faster-whisper; transcribes each pause-bounded chunk on its own")
        p.add_argument("--asr-model", default="small")
        p.add_argument("--lang", default="")
        if name == "breakdown":
            p.add_argument("--threshold", type=float, default=10)
            p.add_argument("--to-spec")
            p.add_argument("--boards", help="known shot lengths in seconds, comma separated (e.g. a template's per-scene seconds)")
            p.add_argument("--measure", action="store_true", help="three frames per shot, cut frames, text boxes (macOS Vision), main colours, motion")
    a = ap.parse_args()
    words = json.loads(Path(a.words).read_text(encoding="utf-8")) if getattr(a, "words", None) else None
    out = Path(a.out)
    if a.cmd == "footage":
        asr = {"python": a.asr_python, "model": a.asr_model, "lang": a.lang} if a.asr_python else None
        res = footage(a.video, words, out, asr)
        r = res["report"]
        print(f"素材：{a.video}｜{r['規格']['width']}×{r['規格']['height']} {r['規格']['fps']} fps {r['規格']['duration']:.1f} 秒")
        print(f"響度 {r['響度'].get('lufs')} LUFS、最大 {r['響度'].get('peak')} dBFS、底噪 {r['響度'].get('floor')} dB｜停頓 {len(r['停頓'])} 段，可剪約 {r['可剪掉秒數']} 秒")
        print(f"亮度 {r['亮度範圍'][0]}–{r['亮度範圍'][1]}｜晃動指標 {r['晃動指標']}｜輸出要放大 {r['需要放大']} 倍")
        print("問題：" + ("\n- " + "\n- ".join(r["問題"]) if r["問題"] else "無"))
        print(f"\n已寫出 {out}/footage.json 和 {out}/draft_card.json（鏡頭從停頓中點切；補上調性和各鏡規格後跑 pb.py spec）")
        return 0
    if a.to_spec:
        card = json.loads(Path(a.to_spec).read_text(encoding="utf-8"))
        spec = to_spec(card)
        out.mkdir(parents=True, exist_ok=True)
        (out / "imitation_card.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"已寫出 {out}/imitation_card.json（KEEP 照抄、CHANGE 寫進備註由調性預設補；補上調性後跑 pb.py spec）")
        return 0
    boards = [float(x) for x in a.boards.split(",")] if a.boards else None
    card = breakdown(a.video, words, out, a.threshold, boards, a.measure)
    print(f"參考片：{a.video}｜{card['鏡數']} 鏡、平均每鏡 {card['平均每鏡秒數']} 秒、每分鐘 {card['每分鐘切點']} 個切點 → {card['剪輯節奏']}")
    for s in card["鏡頭"]:
        hint = "、".join(f"{k}={v}" for k, v in s["建議值"].items())
        print(f"- 第 {s['編號']} 鏡 {s['起']}–{s['訖']} 秒（{s['秒數']}）｜{hint or '—'}" + (f"｜{s['台詞']}" if s.get("台詞") else ""))
    print(f"\n已寫出 {out}/breakdown.json、contact_sheet.jpg 和各鏡關鍵格；請看圖填其餘維度")
    return 0


if __name__ == "__main__":
    sys.exit(main())
