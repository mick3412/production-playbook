#!/usr/bin/env python3
"""Direction alignment (方向對齊): agree on a video's direction with things you can see, before any storyboard.

  index                      build the reference index from the FlexClip corpus (once; stored in the corpus folder)
  page   "需求" [--out DIR]   step 1–2 page: this-or-that pairs (one measured axis each) + a reference wall (local HTML, not published)
  samples picks.json --hook "鉤子" [--point "第二句"] [--photo img] [--out DIR]
                             picks → 3 direction cards (motion, tone, layouts, colours) → 3 short sample renders + step-3 page
  choose picks.json N        write 方向卡 direction.json from sample N

Axes, thresholds and the mapping live in data/direction_rules.json. Picks only become parameters card-check validates.
"""
from __future__ import annotations
import argparse, html, json, os, random, re, statistics, subprocess, sys, datetime as dt
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = json.loads((REPO / "data" / "direction_rules.json").read_text(encoding="utf-8"))
AXES = RULES["軸"]


def ref_dir() -> Path:
    return Path(os.environ.get(RULES["參考片"]["環境變數"]) or os.path.expanduser(RULES["參考片"]["預設"]))


def form_of(need: str) -> str:
    low = need.lower()
    return next((v for k, v in RULES["形式"].items() if k.lower() in low), "文字動態")


# ---------------------------------------------------------------- index
def flat_share(path: Path) -> float:
    """Share of 8×8 blocks that are nearly flat: graphics are large flat areas, photos almost never are."""
    from PIL import Image, ImageStat
    im = Image.open(path).convert("L").resize((136, 240))
    n = flat = 0
    for y in range(0, 240, 8):
        for x in range(0, 136, 8):
            n += 1
            flat += ImageStat.Stat(im.crop((x, y, x + 8, y + 8))).stddev[0] < 2.5
    return round(flat / n, 3)


def build_index(ref: Path) -> dict:
    notes = {}
    for f in sorted((ref / "notes").glob("*.json")):
        cls = {"text": "文字動態", "phot": "照片故事", "talk": "口播訪談", "caro": "輪播圖卡"}.get(f.name[:4])
        for k, v in json.loads(f.read_text(encoding="utf-8")).items():
            form = v.get("形式", "")
            c = cls or ("口播訪談" if re.search(r"口播|訪談|Podcast|vlog", form) else "輪播圖卡" if "輪播" in form else "照片故事" if re.search(r"照片故事|真實照片", form) else "文字動態")
            notes[k] = {"形式類": c, "形式": form, "目的": v.get("目的", ""), "節奏": v.get("節奏", ""), "配色": v.get("配色", "")}
    vids = []
    for bd in sorted((ref / "breakdown").glob("*/breakdown.json")):
        key = bd.parent.name
        d = json.loads(bd.read_text(encoding="utf-8"))
        shots = []
        for s in d.get("鏡頭", []):
            m = s.get("量測", {})
            fr = bd.parent / s.get("關鍵格", "")
            if not fr.is_file():
                continue
            txt = max((m.get(k, {}) or {}).get("文字面積%", 0) for k in ("文字（中段）", "文字（出場）"))
            shots.append({"n": s["編號"], "起": s["起"], "訖": s["訖"], "格": str(fr), "亮度": m.get("亮度", 0), "飽和": m.get("飽和", 0),
                          "變化": m.get("畫面變化", 0), "字面積": txt, "照片": round(1 - flat_share(fr), 3)})
        if not shots:
            continue
        vid = ref / "video" / f"{key}.mp4"
        sheet = ref / "sheets" / f"{key}.jpg"
        vids.append({"key": key, "片長": d.get("片長"), "每鏡秒": d.get("平均每鏡秒數"), "影片": str(vid) if vid.is_file() else "",
                     "總覽": str(sheet) if sheet.is_file() else "", **notes.get(key, {"形式類": "文字動態"}), "鏡": shots,
                     **{k: round(statistics.mean(s[k] for s in shots), 2) for k in ("亮度", "飽和", "變化", "字面積", "照片")}})
    return {"建立": dt.date.today().isoformat(), "來源": str(ref), "片": vids}


def load_index(ref: Path) -> dict:
    p = ref / "direction_index.json"
    if not p.is_file():
        sys.exit(f"沒有參考索引：先跑 `pb.py direction index`（參考片資料夾 {ref}）")
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- pairs: far apart on one axis, close on the others
def units(I: dict, level: str) -> list[dict]:
    if level == "片":
        return [{"片": v, "鏡": v["鏡"][0], **{k: v[k] for k in ("亮度", "飽和", "變化", "字面積", "照片")}, "每鏡秒": v["每鏡秒"] or 0} for v in I["片"]]
    return [{"片": v, "鏡": s, **{k: s[k] for k in ("亮度", "飽和", "變化", "字面積", "照片")}, "每鏡秒": v["每鏡秒"] or 0} for v in I["片"] for s in v["鏡"]]


def zscorer(rows: list[dict], feats: list[str]):
    st = {f: (statistics.mean(r[f] for r in rows), statistics.pstdev(r[f] for r in rows) or 1) for f in feats}
    return lambda r, f: (r[f] - st[f][0]) / st[f][1]


FEATS = ["每鏡秒", "變化", "字面積", "照片", "飽和", "亮度"]


def pick_pair(I: dict, axis: dict, form: str, rng: random.Random) -> dict:
    rows = units(I, axis["層"])
    same = [r for r in rows if r["片"].get("形式類") == form]
    pool = same if len(same) >= 40 else rows
    f = axis["特徵"]
    vals = sorted(r[f] for r in pool)
    q_lo, q_hi = RULES["挑對"]["目標軸分位"]
    lo_cut, hi_cut = vals[int(len(vals) * q_lo)], vals[int(len(vals) * q_hi)]
    lo = [r for r in pool if r[f] <= lo_cut]
    hi = [r for r in pool if r[f] >= hi_cut]
    z = zscorer(rows, FEATS)
    others = [x for x in FEATS if x != f]
    best = None
    for a in lo:
        for b in rng.sample(hi, min(len(hi), 120)):
            if a["片"]["key"] == b["片"]["key"]:
                continue
            cost = sum(abs(z(a, o) - z(b, o)) for o in others)
            if best is None or cost < best[0]:
                best = (cost, a, b)
    _, a, b = best
    off = {o: round(z(a, o) - z(b, o), 2) for o in others if abs(z(a, o) - z(b, o)) > 1.0}   # where the pair still differs
    side = lambda r, lab: {"標籤": lab, "key": r["片"]["key"], "格": r["鏡"]["格"], "影片": r["片"]["影片"], "起": r["鏡"]["起"] if axis["層"] == "鏡" else 0,
                           "訖": r["鏡"]["訖"] if axis["層"] == "鏡" else min(8, r["片"]["片長"] or 8), "值": {k: r[k] for k in FEATS}}
    L, R = side(a, axis["低"]), side(b, axis["高"])
    if rng.random() < 0.5:
        L, R = R, L
    return {"軸": axis["id"], "問": axis["問"], "看": axis["看"], "左": L, "右": R, "目標差z": round(z(b, f) - z(a, f), 2), "其他還差": off}


# ---------------------------------------------------------------- page
CSS = """
:root{--bg:#f6f4ef;--ink:#1d1d1f;--mute:#6b6b70;--line:#d9d6cf;--acc:#2f5bd3;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--ink:#ececef;--mute:#9a9aa2;--line:#33333a;--acc:#7da2ff;--card:#1d1d21}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,"PingFang TC","Noto Sans TC",sans-serif}
main{max-width:1080px;margin:0 auto;padding:24px 16px 80px}h1{font-size:24px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 8px}
.sub{color:var(--mute)}.pair{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px;margin:16px 0}
.q{font-weight:600;margin-bottom:10px}.lr{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:560px}
.opt{border:2px solid transparent;border-radius:12px;padding:6px;cursor:pointer;background:var(--bg)}.opt.on{border-color:var(--acc)}
.opt img,.opt video{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:8px;display:block;background:#000}
.meta{font-size:12px;color:var(--mute);margin-top:6px}.btns{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:6px 14px;cursor:pointer}
button.on{background:var(--acc);color:#fff;border-color:var(--acc)}.warn{font-size:12px;color:#b26a00;margin-top:6px}
.wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}.w{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px}
.w video{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:8px;background:#000}.w img.sheet{width:100%;border-radius:6px;margin-top:6px}
.aspects{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}.aspects label{font-size:13px}
.bar{position:sticky;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:12px 16px;display:flex;gap:10px;align-items:center;justify-content:center;flex-wrap:wrap}
details{margin-top:4px}pre{white-space:pre-wrap;font-size:12px}
"""

JS = r"""
const D = window.DATA, S = JSON.parse((()=>{try{return localStorage.getItem(D.store)}catch(e){return null}})() || '{"二選一":{},"參考牆":{}}');
const save = () => { try { localStorage.setItem(D.store, JSON.stringify(S)); } catch (e) {} ; window.PICKS = out(); };
const out = () => ({需求: D.need, 形式: D.form, 二選一: S.二選一, 參考牆: S.參考牆, 時間: new Date().toISOString()});
function clip(v, a, b) { v.addEventListener('loadedmetadata', () => { v.currentTime = a; }); v.addEventListener('timeupdate', () => { if (v.currentTime > b || v.currentTime < a - 0.3) v.currentTime = a; }); }
function media(x, look) {
  if (look === '片段' && x.影片) { const v = document.createElement('video'); v.src = 'file://' + x.影片; v.muted = true; v.autoplay = true; v.loop = true; v.playsInline = true; clip(v, x.起, x.訖); return v; }
  const i = document.createElement('img'); i.src = 'file://' + x.格; i.loading = 'lazy'; return i;
}
function pairs() {
  const box = document.getElementById('pairs');
  D.pairs.forEach(p => {
    const c = document.createElement('div'); c.className = 'pair';
    c.innerHTML = `<div class="q">${p.軸}｜${p.問}</div><div class="lr"></div><div class="btns"></div>` + (Object.keys(p.其他還差).length ? `<div class="warn">這一對除了「${p.軸}」，還在 ${Object.keys(p.其他還差).join('、')} 上有差（參考片限制）；請只看「${p.軸}」。</div>` : '');
    const lr = c.querySelector('.lr'), opts = [];
    [p.左, p.右].forEach(x => { const o = document.createElement('div'); o.className = 'opt'; o.appendChild(media(x, p.看));
      o.insertAdjacentHTML('beforeend', `<div class="meta"><b>${x.標籤}</b>｜${D.unit[p.軸](x.值)}<br>${x.key}</div>`); o.onclick = () => set(x.標籤); lr.appendChild(o); opts.push([o, x.標籤]); });
    const bt = c.querySelector('.btns'), bs = [];
    ['都可以', '都不要'].forEach(t => { const b = document.createElement('button'); b.textContent = t; b.onclick = () => set(t); bt.appendChild(b); bs.push([b, t]); });
    function set(v) { S.二選一[p.軸] = v; opts.forEach(([o, t]) => o.classList.toggle('on', t === v)); bs.forEach(([b, t]) => b.classList.toggle('on', t === v)); save(); wall(); }
    if (S.二選一[p.軸]) set(S.二選一[p.軸]);
    box.appendChild(c);
  });
}
function wall() {
  const box = document.getElementById('wall'); box.innerHTML = '';
  const want = D.axes.map(a => [a, S.二選一[a.id]]).filter(([a, v]) => v === a.低 || v === a.高);
  const z = f => { const xs = D.vids.map(v => v[f]); const m = xs.reduce((a, b) => a + b, 0) / xs.length; const sd = Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / xs.length) || 1; return v => (v[f] - m) / sd; };
  const zs = Object.fromEntries(D.axes.map(a => [a.特徵, z(a.特徵)]));
  const score = v => want.reduce((s, [a, val]) => s + (val === a.高 ? 1 : -1) * zs[a.特徵](v), 0) + (v.形式類 === D.form ? 1.5 : 0);
  const top = D.vids.slice().sort((a, b) => score(b) - score(a)).slice(0, 9);
  document.getElementById('wallnote').textContent = want.length ? `依你上面選的 ${want.length} 軸，加上形式「${D.form}」挑出最接近的 9 支。` : '先在上面選幾個，這裡會照你的選擇重排。';
  top.forEach(v => {
    const c = document.createElement('div'); c.className = 'w'; const r = S.參考牆[v.key] || {判: '', 點: []};
    const vid = media({影片: v.影片, 格: v.鏡[0].格, 起: 0, 訖: Math.min(10, v.片長 || 10)}, '片段'); c.appendChild(vid);
    c.insertAdjacentHTML('beforeend', `<div class="meta">${v.key}｜${v.形式 || v.形式類}｜每鏡 ${v.每鏡秒} 秒</div><div class="btns"><button data-v="要">要</button><button data-v="不要">不要</button></div>
      <div class="aspects">${D.aspects.map(x => `<label><input type="checkbox" value="${x}" ${r.點.includes(x) ? 'checked' : ''}> ${x}</label>`).join('')}</div>` +
      (v.總覽 ? `<details><summary class="meta">逐鏡總覽</summary><img class="sheet" loading="lazy" src="file://${v.總覽}"></details>` : ''));
    c.querySelectorAll('button').forEach(b => { b.classList.toggle('on', r.判 === b.dataset.v); b.onclick = () => { r.判 = b.dataset.v; S.參考牆[v.key] = r; c.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); save(); }; });
    c.querySelectorAll('input').forEach(i => i.onchange = () => { r.點 = [...c.querySelectorAll('input:checked')].map(x => x.value); S.參考牆[v.key] = r; save(); });
    box.appendChild(c);
  });
}
function samples() {
  const box = document.getElementById('samples'); if (!box || !D.samples) return;
  D.samples.forEach((s, i) => { const c = document.createElement('div'); c.className = 'w';
    c.innerHTML = `<video src="file://${s.影片}" muted autoplay loop playsinline></video><div class="q">方向 ${i + 1}：${s.名稱}</div><div class="meta">${s.差異}</div><div class="btns"><button>選這個</button></div>`;
    const b = c.querySelector('button'); b.classList.toggle('on', S.選 === i + 1); b.onclick = () => { S.選 = i + 1; document.querySelectorAll('#samples button').forEach(x => x.classList.toggle('on', x === b)); save(); };
    box.appendChild(c); });
}
function download() { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify({...out(), 選: S.選 || null}, null, 1)], {type: 'application/json'})); a.download = 'picks.json'; a.click(); }
pairs(); wall(); samples(); save();
document.getElementById('dl').onclick = download;
"""


def page(I: dict, need: str, pairs: list[dict], out: Path, samples: list[dict] | None = None, picks: dict | None = None) -> Path:
    form = form_of(need)
    vids = [{k: v[k] for k in ("key", "片長", "每鏡秒", "影片", "總覽", "形式類", "亮度", "飽和", "變化", "字面積", "照片")} | {"形式": v.get("形式", ""), "鏡": v["鏡"][:1]} for v in I["片"]]
    data = {"need": need, "form": form, "store": "dir:" + re.sub(r"\W+", "", need)[:40], "pairs": pairs, "vids": vids, "samples": samples,
            "axes": [{k: a[k] for k in ("id", "特徵", "低", "高")} for a in AXES], "aspects": ["節奏", "版面", "配色", "字的進場", "照片處理", "轉場"]}
    units_js = {"節奏": "v=>`每鏡 ${v.每鏡秒} 秒`", "動態": "v=>`畫面變化 ${v.變化}`", "字量": "v=>`字占畫面 ${v.字面積}%`", "畫面": "v=>`照片感 ${Math.round(v.照片*100)}%`",
                "色彩": "v=>`飽和 ${v.飽和}`", "亮暗": "v=>`亮度 ${v.亮度}`"}
    step3 = ('<h2>3. 用你的內容做的 3 個方向</h2><p class="sub">同一句鉤子，三個方向；選一個，下載後交回。</p><div class="wall" id="samples"></div>' if samples else
             '<h2>3. 方向樣片</h2><p class="sub">選完 1、2 後按下方「下載 picks.json」，交回後會用你的鉤子句算 3 個方向的短樣片，再回到這頁選。</p>')
    doc = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>方向對齊</title><style>{CSS}</style></head><body><main>
<h1>方向對齊</h1><div class="sub">需求：{html.escape(need)}｜形式：{form}｜參考片只供內部參考，這頁只在本機開</div>
<h2>1. 二選一</h2><p class="sub">每一題只比一件事；點比較像你要的那一邊，沒差就選「都可以」。</p><div id="pairs"></div>
<h2>2. 參考牆</h2><p class="sub" id="wallnote"></p><div class="wall" id="wall"></div>
{step3}
</main><div class="bar"><span class="sub">選擇會自動存在這個瀏覽器</span><button id="dl" class="on">下載 picks.json</button></div>
<script>window.DATA = {json.dumps(data, ensure_ascii=False)}; DATA.unit = {{{",".join(f"'{k}':{v}" for k, v in units_js.items())}}};</script><script>{JS}</script></body></html>"""
    out.mkdir(parents=True, exist_ok=True)
    p = out / ("direction_samples.html" if samples else "direction.html")
    p.write_text(doc, encoding="utf-8")
    return p


# ---------------------------------------------------------------- picks → direction cards → samples
def direction_from(picks: dict, flip: list[str] | None = None) -> dict:
    """The direction a set of picks means, in card-check parameters only. flip: axes to set to the other side (for alternatives)."""
    d = {"motion": {"preset": "crisp"}, "字量": "少字", "群組": ["文字", "數字"], "visual": {"type": "glow"}, "tone": "light",
         "色盤": AXES[4]["換算"]["收斂"]["色盤"], "每鏡秒": 2.4, "依據": {}}
    for a in AXES:
        v = picks.get("二選一", {}).get(a["id"])
        if a["id"] in (flip or []):
            if v in (a["低"], a["高"]):
                v = a["高"] if v == a["低"] else a["低"]
            else:   # never picked: take the side that actually changes the default
                v = next((s for s in (a["高"], a["低"]) if any(d.get(k) != x and not (k == "motion" and all(d["motion"].get(i) == j for i, j in x.items()))
                                                             for k, x in a["換算"][s].items())), a["高"])
        if v not in (a["低"], a["高"]):
            continue
        m = a["換算"][v]
        for k, x in m.items():
            if k == "motion":
                d["motion"] = {**d["motion"], **x}
            else:
                d[k] = x
        d["依據"][a["id"]] = v
    return d


def sample_card(d: dict, hook: str, points: list[str], photo: str | None) -> dict:
    """Two beats in the direction, written only with the user's own words (never the catalogue's sample text)."""
    sec = d["每鏡秒"]
    split = lambda t: [x.strip() for x in re.split(r"[，,。\n]", t) if x.strip()]
    lines = split(hook)[:3] or [hook]
    pts = [x.strip() for p in points for x in re.split(r"[；;]", p) if x.strip()]
    img = None
    if photo:   # the kit serves only its own folder
        dst = REPO / ".cache" / "direction" / ("photo" + Path(photo).suffix)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(Path(photo).read_bytes())
        img = "/.cache/direction/" + dst.name
    want_photo = d["visual"]["type"] == "photo"
    vis = {"type": "photo", "image": img} if want_photo and img else {"type": "word", "text": re.sub(r"<[^>]+>", "", lines[0])[:6]} if want_photo else d["visual"]
    other = "dark" if d["tone"] == "light" else "light"
    beats = [{"layout": "hook", "seconds": max(2.2, sec), "text": lines, "visual": vis, "tone": d["tone"]}]
    if want_photo and img:
        beats.append({"layout": "photo", "image": img, "text": (pts or lines)[:2], "seconds": max(2.5, sec)})
    elif d["字量"] == "多字" and len(pts) >= 2:
        beats.append({"layout": "checklist", "items": pts[:4], "seconds": max(3.0, sec + 1), "tone": other, "visual": {"type": "glow"} if want_photo else d["visual"]})
    else:
        beats.append({"layout": "statement", "text": (pts or ["（第二句：用 --point 給）"])[:3], "seconds": max(2.5, sec), "tone": other, "visual": {"type": "glow"}})
    return {"width": 1080, "height": 1920, "platform": "reels-tiktok", "motion": d["motion"], "chrome": False,
            "brand": {"colors": d["色盤"], "fonts": {"heading": "IBM Plex Sans", "body": "IBM Plex Sans"}, "handle": ""}, "beats": beats}


def describe(d: dict) -> str:
    m = d["motion"]
    return "；".join([f"節奏 {d['依據'].get('節奏', '中')}（每段約 {d['每鏡秒']} 秒）", f"動態 {m.get('preset')}" + (f"、進場 {m['enter']}" if m.get("enter") else ""),
                     f"字量 {d['字量']}", "畫面 " + ("照片" if d["visual"]["type"] == "photo" else "圖形"), f"色彩 {d['依據'].get('色彩', '收斂')}", f"{'暗' if d['tone'] == 'dark' else '亮'}底"])


def flexible_axes(picks: dict) -> list[str]:
    weak = [a["id"] for a in AXES if picks.get("二選一", {}).get(a["id"]) in (None, "都可以")]
    return weak + [x for x in ("亮暗", "色彩", "動態") if x not in weak]


def cmd_samples(a) -> int:
    picks = json.loads(Path(a.picks).read_text(encoding="utf-8"))
    out = Path(a.out or Path(a.picks).parent)
    out.mkdir(parents=True, exist_ok=True)
    flex = flexible_axes(picks)
    variants = [("照你的選擇", []), (f"改 {flex[0]}", [flex[0]]), (f"改 {flex[1]}、{flex[2]}", [flex[1], flex[2]])]
    samples, ok = [], True
    pb = [sys.executable, str(REPO / "pb.py")]
    for i, (name, flip) in enumerate(variants, 1):
        d = direction_from(picks, flip)
        card = sample_card(d, a.hook, a.point or [], a.photo)
        cp = out / f"sample{i}.json"
        cp.write_text(json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
        chk = subprocess.run(pb + ["card-check", str(cp)], capture_output=True, text=True)
        if d["visual"]["type"] == "photo" and not a.photo:
            d["說明補充"] = "沒給 --photo，照片先用大字代替"
        print(f"方向 {i}（{name}）：{describe(d)}{('（' + d['說明補充'] + '）') if d.get('說明補充') else ''}\n  card-check：{chk.stdout.splitlines()[0] if chk.stdout else chk.stderr}")
        if chk.returncode:
            ok = False
            print(chk.stdout)
            continue
        mp4 = out / f"sample{i}.mp4"
        if not a.no_render:   # the kit serves only its own folder: render from a copy inside it
            tmp = REPO / ".cache" / "direction" / f"sample{i}.json"
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(cp.read_text(encoding="utf-8"), encoding="utf-8")
            r = subprocess.run([sys.executable, str(REPO / "kits" / "storyboard" / "render.py"), str(tmp), str(mp4), "--scale", "0.5", "--fps", "24"], capture_output=True, text=True)
            if r.returncode:
                print("  算圖失敗：" + (r.stderr.strip().splitlines() or ["?"])[-1])
                ok = False
        (out / f"direction{i}.json").write_text(json.dumps({"方向": i, "名稱": name, "說明": describe(d), **d, "卡片": cp.name}, ensure_ascii=False, indent=1), encoding="utf-8")
        samples.append({"名稱": name, "差異": describe(d) + (f"（{d['說明補充']}）" if d.get("說明補充") else ""), "影片": str(mp4.resolve())})
    if samples and not a.no_render:
        ref = ref_dir()
        I = load_index(ref)
        p = page(I, picks.get("需求", ""), [], out, samples, picks)
        print(f"\n第 3 步頁面：{p}（開檔看三個方向，選一個、下載 picks.json，再跑 `pb.py direction choose picks.json N`）")
    return 0 if ok else 1


def cmd_choose(a) -> int:
    out = Path(a.out or Path(a.picks).parent)
    src = out / f"direction{a.n}.json"
    if not src.is_file():
        sys.exit(f"沒有 {src}：先跑 `pb.py direction samples`")
    picks = json.loads(Path(a.picks).read_text(encoding="utf-8"))
    d = json.loads(src.read_text(encoding="utf-8"))
    liked = {k: v for k, v in picks.get("參考牆", {}).items() if v.get("判") == "要"}
    card = {"方向卡": "v1", "日期": dt.date.today().isoformat(), "需求": picks.get("需求", ""), "形式": picks.get("形式", ""),
            "選的方向": a.n, "說明": d["說明"], "motion": d["motion"], "tone": d["tone"], "字量": d["字量"], "版型群組": d["群組"],
            "visual": d["visual"], "色盤": d["色盤"], "每鏡秒": d["每鏡秒"], "二選一": picks.get("二選一", {}),
            "參考片": {"要": {k: v.get("點", []) for k, v in liked.items()}, "不要": [k for k, v in picks.get("參考牆", {}).items() if v.get("判") == "不要"]},
            "樣片": d["卡片"]}
    p = out / "direction.json"
    p.write_text(json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已寫出方向卡 {p}\n{d['說明']}\n下一步：`pb.py storyboard --use SB-xx --emit card.json --direction {p}`（motion、明暗、色盤照方向卡）")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pb.py direction")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("index"); s.add_argument("--ref")
    s = sub.add_parser("page"); s.add_argument("need"); s.add_argument("--out", default="direction"); s.add_argument("--ref"); s.add_argument("--seed", type=int, default=7)
    s = sub.add_parser("samples"); s.add_argument("picks"); s.add_argument("--hook", required=True); s.add_argument("--point", action="append", help="the second line or points (repeatable; 「；」 also splits)"); s.add_argument("--photo"); s.add_argument("--out"); s.add_argument("--no-render", action="store_true")
    s = sub.add_parser("choose"); s.add_argument("picks"); s.add_argument("n", type=int); s.add_argument("--out")
    a = ap.parse_args(argv)
    if getattr(a, "ref", None):
        os.environ[RULES["參考片"]["環境變數"]] = a.ref
    ref = ref_dir()
    if a.cmd == "index":
        if not (ref / "breakdown").is_dir():
            sys.exit(f"找不到參考片拆解：{ref}/breakdown（用 --ref 或環境變數 {RULES['參考片']['環境變數']} 指定）")
        I = build_index(ref)
        (ref / "direction_index.json").write_text(json.dumps(I, ensure_ascii=False), encoding="utf-8")
        print(f"已建索引：{len(I['片'])} 支、{sum(len(v['鏡']) for v in I['片'])} 鏡 → {ref / 'direction_index.json'}")
        return 0
    if a.cmd == "page":
        I = load_index(ref)
        rng = random.Random(a.seed)
        pairs = [pick_pair(I, ax, form_of(a.need), rng) for ax in AXES]
        p = page(I, a.need, pairs, Path(a.out))
        for x in pairs:
            print(f"{x['軸']}：{x['左']['標籤']} vs {x['右']['標籤']}｜目標軸差 {abs(x['目標差z'])} 個標準差" + (f"｜其他還差 {x['其他還差']}" if x["其他還差"] else ""))
        print(f"\n頁面：{p.resolve()}（在本機瀏覽器開；不要發佈，參考片是別人的作品）")
        return 0
    return cmd_samples(a) if a.cmd == "samples" else cmd_choose(a)


if __name__ == "__main__":
    sys.exit(main())
