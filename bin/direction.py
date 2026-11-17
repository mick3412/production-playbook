#!/usr/bin/env python3
"""Direction alignment (方向對齊): agree on a video's direction with things you can see, before any storyboard.

  index                      build the reference index from the FlexClip corpus (once; stored in the corpus folder)
  page   "需求" [--out DIR]   step 1–2 page: this-or-that pairs (one measured axis each) + a reference wall (local HTML, not published)
  serve  [DIR] [--port 8765] open the pages over http://127.0.0.1 (the app's built-in browser cannot read file:// media); choices save to DIR/picks.json
  samples picks.json --hook "鉤子" [--point "第二句"] [--photo img] [--out DIR]
                             picks (+ reference wall) → 3 direction cards that differ on the still frame → 3 short sample renders + step-3 page
  choose picks.json [N] [--samples DIR] [--out FILE]
                             write 方向卡 direction.json from sample N (N defaults to 選 in picks.json; DIR to 樣片資料夾 in picks.json)

Axes, thresholds and the mapping live in data/direction_rules.json. Picks only become parameters card-check validates.
"""
from __future__ import annotations
import argparse, colorsys, html, json, os, random, re, statistics, subprocess, sys, datetime as dt
import http.server, urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = json.loads((REPO / "data" / "direction_rules.json").read_text(encoding="utf-8"))
AXES = RULES["軸"]
VISIBLE = RULES["定格看得到"]["軸"]
WALL = RULES["參考牆"]
sys.path.insert(0, str(REPO))
import pb  # noqa: E402  (card-check and the text-fit estimate live there)
pb.ROOT = REPO   # this copy's layouts, not the one PLAYBOOK_HOME points at


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
:root{--bg:#f6f4ef;--ink:#1d1d1f;--mute:#6b6b70;--line:#d9d6cf;--acc:#2f5bd3;--card:#fff;--hot:#c2410c}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--ink:#ececef;--mute:#9a9aa2;--line:#33333a;--acc:#7da2ff;--card:#1d1d21;--hot:#fb923c}}
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
#dl.due{background:var(--hot);border-color:var(--hot);color:#fff;font-weight:700;padding:10px 22px;animation:due 1.2s ease-in-out infinite}
@keyframes due{50%{box-shadow:0 0 0 8px color-mix(in srgb,var(--hot) 25%,transparent)}}
@media (prefers-reduced-motion:reduce){#dl.due{animation:none}}
#state.due{color:var(--hot);font-weight:600}
details{margin-top:4px}pre{white-space:pre-wrap;font-size:12px}
"""

JS = r"""
const D = window.DATA, served = location.protocol.startsWith('http');
const read = () => { try { return JSON.parse(localStorage.getItem(D.store) || 'null'); } catch (e) { return null; } };
let S = read() || {二選一: {}, 參考牆: {}};
if (D.picks) S = {...S, 二選一: D.picks.二選一 || {}, 參考牆: D.picks.參考牆 || {}, 選: (read() || {}).選 ?? D.picks.選 ?? null};   // the samples page starts from the picks its samples were made from
const out = () => ({需求: D.need, 形式: D.form, 二選一: S.二選一, 參考牆: S.參考牆, 選: S.選 || null, ...(D.samplesDir ? {樣片資料夾: D.samplesDir} : {}), 時間: new Date().toISOString()});
let dirty = false;
// served by `pb.py direction serve`: every change is written to picks.json in the served folder; opened as a file: download it
function save(user = true) {
  try { localStorage.setItem(D.store, JSON.stringify(S)); } catch (e) {}
  window.PICKS = out(); if (!user) return status();
  dirty = true; status();
  if (served) fetch('/save', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(out(), null, 1)})
    .then(r => { if (r.ok) { dirty = false; window.SAVED = true; status(); } }).catch(() => {});
}
function status() {
  const st = document.getElementById('state'), b = document.getElementById('dl'), n = S.選;
  if (n && D.samples) { b.textContent = `下載 picks.json（方向 ${n}）`; st.textContent = dirty ? `已選方向 ${n}，還沒交回：按右邊下載，交回後跑 choose` : (window.SAVED ? `已選方向 ${n}，已存到 picks.json` : `已選方向 ${n}`); }
  else st.textContent = served && window.SAVED ? '選擇已自動存到 picks.json' : '選擇會存在這個瀏覽器；做完按右邊下載';
  b.classList.toggle('due', dirty && !!n); st.classList.toggle('due', dirty && !!n);
}
const ROOT = D.ref.replace(/\/$/, '') + '/';
const url = p => !p ? '' : served ? (p.startsWith(ROOT) ? '/ref/' + p.slice(ROOT.length).split('/').map(encodeURIComponent).join('/') : p) : (p.startsWith('/') ? 'file://' + p : p);
function clip(v, a, b) { v.addEventListener('loadedmetadata', () => { v.currentTime = a; }); v.addEventListener('timeupdate', () => { if (v.currentTime > b || v.currentTime < a - 0.3) v.currentTime = a; }); }
function media(x, look) {
  if (look === '片段' && x.影片) { const v = document.createElement('video'); v.src = url(x.影片); v.muted = true; v.autoplay = true; v.loop = true; v.playsInline = true; clip(v, x.起, x.訖); return v; }
  const i = document.createElement('img'); i.src = url(x.格); i.loading = 'lazy'; return i;
}
function pairs() {
  const box = document.getElementById('pairs'); if (!box) return;
  D.pairs.forEach(p => {
    const c = document.createElement('div'); c.className = 'pair';
    c.innerHTML = `<div class="q">${p.軸}｜${p.問}</div><div class="lr"></div><div class="btns"></div>` + (Object.keys(p.其他還差).length ? `<div class="warn">這一對除了「${p.軸}」，還在 ${Object.keys(p.其他還差).join('、')} 上有差（參考片限制）；請只看「${p.軸}」。</div>` : '');
    const lr = c.querySelector('.lr'), opts = [];
    [p.左, p.右].forEach(x => { const o = document.createElement('div'); o.className = 'opt'; o.appendChild(media(x, p.看));
      o.insertAdjacentHTML('beforeend', `<div class="meta"><b>${x.標籤}</b>｜${D.unit[p.軸](x.值)}<br>${x.key}</div>`); o.onclick = () => set(x.標籤); lr.appendChild(o); opts.push([o, x.標籤]); });
    const bt = c.querySelector('.btns'), bs = [];
    ['都可以', '都不要'].forEach(t => { const b = document.createElement('button'); b.textContent = t; b.onclick = () => set(t); bt.appendChild(b); bs.push([b, t]); });
    function set(v, user = true) { S.二選一[p.軸] = v; opts.forEach(([o, t]) => o.classList.toggle('on', t === v)); bs.forEach(([b, t]) => b.classList.toggle('on', t === v)); save(user); wall(); }
    if (S.二選一[p.軸]) set(S.二選一[p.軸], false);
    box.appendChild(c);
  });
}
function wall() {
  const box = document.getElementById('wall'); if (!box) return; box.innerHTML = '';
  const want = D.axes.map(a => [a, S.二選一[a.id]]).filter(([a, v]) => v === a.低 || v === a.高);
  const z = f => { const xs = D.vids.map(v => v[f]); const m = xs.reduce((a, b) => a + b, 0) / xs.length; const sd = Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / xs.length) || 1; return v => (v[f] - m) / sd; };
  const zs = Object.fromEntries(D.axes.map(a => [a.特徵, z(a.特徵)]));
  const score = v => want.reduce((s, [a, val]) => s + (val === a.高 ? 1 : -1) * zs[a.特徵](v), 0) + (v.形式類 === D.form ? 1.5 : 0);
  const top = D.vids.slice().sort((a, b) => score(b) - score(a)).slice(0, 9);
  document.getElementById('wallnote').textContent = (want.length ? `依你上面選的 ${want.length} 軸，加上形式「${D.form}」挑出最接近的 9 支。` : '先在上面選幾個，這裡會照你的選擇重排。') + D.wallRule;
  top.forEach(v => {
    const c = document.createElement('div'); c.className = 'w'; const r = S.參考牆[v.key] || {判: '', 點: []};
    const vid = media({影片: v.影片, 格: v.鏡[0].格, 起: 0, 訖: Math.min(10, v.片長 || 10)}, '片段'); c.appendChild(vid);
    c.insertAdjacentHTML('beforeend', `<div class="meta">${v.key}｜${v.形式 || v.形式類}｜每鏡 ${v.每鏡秒} 秒</div><div class="btns"><button data-v="要">要</button><button data-v="不要">不要</button></div>
      <div class="aspects">${D.aspects.map(x => `<label><input type="checkbox" value="${x}" ${r.點.includes(x) ? 'checked' : ''}> ${x}</label>`).join('')}</div>` +
      (v.總覽 ? `<details><summary class="meta">逐鏡總覽</summary><img class="sheet" loading="lazy" src="${url(v.總覽)}"></details>` : ''));
    const btns = [...c.querySelectorAll('button')], boxes = [...c.querySelectorAll('input')];
    const show = () => btns.forEach(x => x.classList.toggle('on', r.判 === x.dataset.v));
    show();
    // ticking a point is itself a 要 (what to borrow); 不要 clears the ticks — a tick is never silently dropped
    btns.forEach(b => { b.onclick = () => { r.判 = b.dataset.v; if (r.判 === '不要') { r.點 = []; boxes.forEach(i => i.checked = false); } S.參考牆[v.key] = r; show(); save(); }; });
    boxes.forEach(i => i.onchange = () => { r.點 = boxes.filter(x => x.checked).map(x => x.value); if (r.點.length) r.判 = '要'; S.參考牆[v.key] = r; show(); save(); });
    box.appendChild(c);
  });
}
function samples() {
  const box = document.getElementById('samples'); if (!box || !D.samples) return;
  D.samples.forEach((s, i) => { const c = document.createElement('div'); c.className = 'w';
    c.innerHTML = `<video src="${url(s.影片)}" muted autoplay loop playsinline></video><div class="q">方向 ${i + 1}：${s.名稱}</div><div class="meta">${s.差異}</div><div class="btns"><button>選這個</button></div>`;
    const b = c.querySelector('button'); b.classList.toggle('on', S.選 === i + 1); b.onclick = () => { S.選 = i + 1; document.querySelectorAll('#samples button').forEach(x => x.classList.toggle('on', x === b)); save(); };
    box.appendChild(c); });
}
function download() { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(out(), null, 1)], {type: 'application/json'})); a.download = 'picks.json'; a.click(); dirty = false; status(); }
(async () => {
  if (served && !D.picks && !read()) { try { const r = await fetch('/picks.json', {cache: 'no-store'}); if (r.ok) { const p = await r.json(); S = {二選一: p.二選一 || {}, 參考牆: p.參考牆 || {}, 選: p.選 || null}; window.SAVED = true; } } catch (e) {} }
  pairs(); wall(); samples(); save(false);
  document.getElementById('dl').onclick = download;
})();
"""


def page(I: dict | None, need: str, pairs: list[dict], out: Path, samples: list[dict] | None = None, picks: dict | None = None) -> Path:
    form = (picks or {}).get("形式") or form_of(need)
    vids = [{k: v[k] for k in ("key", "片長", "每鏡秒", "影片", "總覽", "形式類", "亮度", "飽和", "變化", "字面積", "照片")} | {"形式": v.get("形式", ""), "鏡": v["鏡"][:1]} for v in (I or {}).get("片", [])] if not samples else []
    data = {"need": need, "form": form, "store": "dir:" + re.sub(r"\W+", "", need)[:40], "pairs": pairs, "vids": vids, "samples": samples, "ref": str(ref_dir()),
            "picks": {k: picks.get(k) for k in ("二選一", "參考牆", "選")} if samples and picks else None, "samplesDir": str(out.resolve()) if samples else None,
            "wallRule": f"勾了要借的點就算「要」；按「不要」會清掉勾選。量得到的點（{'、'.join(WALL['借用'])}）會借進方向 2；{'、'.join(WALL['只記錄'])} 只記錄在方向卡，不影響樣片。",
            "axes": [{k: a[k] for k in ("id", "特徵", "低", "高")} for a in AXES], "aspects": ["節奏", "版面", "配色", "字的進場", "照片處理", "轉場"]}
    units_js = {"節奏": "v=>`每鏡 ${v.每鏡秒} 秒`", "動態": "v=>`畫面變化 ${v.變化}`", "字量": "v=>`字占畫面 ${v.字面積}%`", "畫面": "v=>`照片感 ${Math.round(v.照片*100)}%`",
                "色彩": "v=>`飽和 ${v.飽和}`", "亮暗": "v=>`亮度 ${v.亮度}`"}
    if samples:
        said = "、".join(f"{k} {v}" for k, v in (picks or {}).get("二選一", {}).items())
        steps = f"""<h2>1–2. 你選的</h2><p class="sub">{html.escape(said or '（沒有二選一）')}；參考牆標要 {len(wall_liked(picks or {}))} 支。要改就回第 1 頁。</p>
<h2>3. 用你的內容做的 3 個方向</h2><p class="sub">同一句鉤子，三個方向，每個方向在定格上都有看得出來的差別。選一個；用 <code>pb.py direction serve</code> 開的會自動存，直接開檔的要按下方按鈕下載 picks.json 交回。</p><div class="wall" id="samples"></div>"""
    else:
        steps = """<h2>1. 二選一</h2><p class="sub">每一題只比一件事；點比較像你要的那一邊，沒差就選「都可以」，兩邊都不像就選「都不要」（會用中性值）。</p><div id="pairs"></div>
<h2>2. 參考牆</h2><p class="sub" id="wallnote"></p><div class="wall" id="wall"></div>
<h2>3. 方向樣片</h2><p class="sub">選完 1、2 後交回 picks.json（serve 開的已自動存；直接開檔的按下方下載），會用你的鉤子句算 3 個方向的短樣片，再到樣片頁選。</p>"""
    doc = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>方向對齊</title><style>{CSS}</style></head><body><main>
<h1>方向對齊</h1><div class="sub">需求：{html.escape(need)}｜形式：{form}｜參考片只供內部參考，這頁只在本機開（<code>pb.py direction serve</code>）</div>
{steps}
</main><div class="bar"><span class="sub" id="state"></span><button id="dl" class="on">下載 picks.json</button></div>
<script>window.DATA = {json.dumps(data, ensure_ascii=False)}; DATA.unit = {{{",".join(f"'{k}':{v}" for k, v in units_js.items())}}};</script><script>{JS}</script></body></html>"""
    out.mkdir(parents=True, exist_ok=True)
    p = out / ("direction_samples.html" if samples else "direction.html")
    p.write_text(doc, encoding="utf-8")
    return p


# ---------------------------------------------------------------- serve: the pages over http, so the app's built-in browser can play the references
def make_server(root: Path, ref: Path, picks: Path, port: int = 8765) -> http.server.ThreadingHTTPServer:
    """127.0.0.1 only. / → root (the pages, samples, picks.json), /ref/ → the reference corpus. Range requests for video seeking; POST /save writes picks.json."""
    root, ref = root.resolve(), ref.resolve()

    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def translate_path(self, path):
            path = urllib.parse.urlsplit(path).path
            base = ref if path.startswith("/ref/") else root
            rel = path[len("/ref/"):] if base is ref else path
            parts = [x for x in urllib.parse.unquote(rel).split("/") if x not in ("", ".", "..")]
            f = base.joinpath(*parts).resolve()
            return str(f) if f == base or base in f.parents else str(base / "\0outside")

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def do_GET(self):
            rng = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
            f = Path(self.translate_path(self.path))
            if not rng or not f.is_file():
                return super().do_GET()
            size = f.stat().st_size
            a = int(rng.group(1)) if rng.group(1) else max(0, size - int(rng.group(2) or 0))
            b = min(int(rng.group(2)), size - 1) if rng.group(1) and rng.group(2) else size - 1
            if a >= size:
                self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.end_headers(); return
            self.send_response(206)
            self.send_header("Content-Type", self.guess_type(str(f)))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
            self.send_header("Content-Length", str(b - a + 1))
            self.end_headers()
            with f.open("rb") as fh:
                fh.seek(a)
                left = b - a + 1
                while left > 0:
                    chunk = fh.read(min(1 << 16, left))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        return
                    left -= len(chunk)

        def do_POST(self):
            origin = self.headers.get("Origin", "")
            host = f"http://{self.headers.get('Host', '')}"
            n = int(self.headers.get("Content-Length") or 0)
            if self.path != "/save" or (origin and origin != host) or not 0 < n <= 2_000_000:
                self.send_error(403); return
            try:
                d = json.loads(self.rfile.read(n).decode("utf-8"))
                assert isinstance(d, dict) and isinstance(d.get("二選一"), dict)
            except Exception:
                self.send_error(400); return
            picks.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            self.send_response(204); self.end_headers()

    return http.server.ThreadingHTTPServer(("127.0.0.1", port), H)


def cmd_serve(a) -> int:
    root = Path(a.dir).expanduser()
    if not root.is_dir():
        sys.exit(f"沒有資料夾 {root}：先跑 `pb.py direction page \"需求\" --out {a.dir}`")
    picks = Path(a.picks).expanduser() if a.picks else root / "picks.json"
    try:
        srv = make_server(root, ref_dir(), picks, a.port)
    except OSError:
        sys.exit(f"埠 {a.port} 被占用：換一個，例如 `pb.py direction serve {a.dir} --port {a.port + 1}`（同一個埠開，瀏覽器裡的選擇才會留著）")
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    pages = [p for p in ("direction.html", "samples/direction_samples.html", "direction_samples.html") if (root / p).is_file()]
    print("方向對齊頁（只在本機，Ctrl-C 結束）：\n" + "\n".join(f"  {base}/{p}" for p in pages or ["direction.html"]))
    print(f"選擇會自動存到 {picks}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


# ---------------------------------------------------------------- picks → direction cards → samples
def wall_liked(picks: dict) -> dict:
    """Reference-wall clips the owner wants: 判 要, or points ticked without pressing 要 or 不要 (ticking what to borrow is itself a yes)."""
    return {k: v for k, v in picks.get("參考牆", {}).items() if v.get("判") == "要" or (not v.get("判") and v.get("點"))}


def _hex(c) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(x))) for x in c)


def _lum(c) -> float:
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (f(x / 255) for x in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast(a, b) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _mix(c, to, t):
    return tuple(x + (y - x) * t for x, y in zip(c, to))


def frame_palette(frames: list[str]) -> dict | None:
    """The reference's colours in the kit's four slots: the lightest common colour is the paper, the darkest the ink, the most saturated the accent."""
    from PIL import Image
    px = []
    for f in frames[:12]:
        try:
            px += list(Image.open(f).convert("RGB").resize((36, 64)).getdata())
        except Exception:
            continue
    if not px:
        return None
    im = Image.new("RGB", (len(px), 1))
    im.putdata(px)
    q = im.quantize(colors=8, method=0)
    pal = q.getpalette()
    cols = [(n / len(px), tuple(pal[i * 3:i * 3 + 3])) for n, i in q.getcolors()]
    common = [c for share, c in cols if share >= 0.06] or [c for _, c in cols]
    paper = max(common, key=_lum)
    ink = min(common, key=_lum)
    hls = lambda c: colorsys.rgb_to_hls(*(x / 255 for x in c))
    accent = max(cols, key=lambda sc: hls(sc[1])[2] * (0.25 < hls(sc[1])[1] < 0.8) * sc[0] ** 0.3)[1]
    while _lum(paper) < 0.75:
        paper = _mix(paper, (255, 255, 255), 0.25)
    while _lum(ink) > 0.03:
        ink = _mix(ink, (0, 0, 0), 0.25)
    ink_acc = accent
    while _contrast(ink_acc, paper) < 4.5:
        ink_acc = _mix(ink_acc, (0, 0, 0), 0.15)
    return {"primary": _hex(ink), "background": _hex(paper), "accent": _hex(accent), "accent_ink": _hex(ink_acc)}


def wall_borrow(picks: dict, I: dict | None) -> dict:
    """What the liked clips lend to direction 2: only what the index measured (rhythm, colours); the rest is recorded, not applied."""
    liked = wall_liked(picks)
    vids = {v["key"]: v for v in (I or {}).get("片", [])}
    b = {"借": {}, "依據": {}, "只記錄": {}, "找不到": []}
    for k, v in liked.items():
        for pt in v.get("點", []):
            if pt not in WALL["借用"]:
                b["只記錄"].setdefault(pt, []).append(k)
    for k in liked:
        if k not in vids:
            b["找不到"].append(k)
    beat = [vids[k]["每鏡秒"] for k, v in liked.items() if "節奏" in v.get("點", []) and k in vids and vids[k].get("每鏡秒")]
    if beat:
        b["借"]["每鏡秒"] = round(min(4.0, max(1.2, statistics.median(beat))), 1)
        b["依據"]["節奏"] = [k for k, v in liked.items() if "節奏" in v.get("點", []) and k in vids]
    src = [k for k, v in liked.items() if "配色" in v.get("點", []) and k in vids]
    if src:
        pal = frame_palette([s["格"] for k in src for s in vids[k]["鏡"]] + [vids[k]["總覽"] for k in src if vids[k].get("總覽") and len(vids[k]["鏡"]) < 3])   # few shots indexed: the contact sheet covers the rest
        if pal:
            b["借"]["色盤"] = pal
            b["依據"]["配色"] = src
    return b


def direction_from(picks: dict, flip: list[str] | None = None, borrow: dict | None = None) -> dict:
    """The direction a set of picks means, in card-check parameters only. flip: axes set to the other side (for alternatives); 都不要 axes are never flipped.
    borrow: what the reference wall lends (wall_borrow)."""
    d = {"motion": {"preset": "crisp"}, "字量": "少字", "群組": ["文字", "數字"], "visual": {"type": "glow"}, "tone": "light",
         "色盤": AXES[4]["換算"]["收斂"]["色盤"], "每鏡秒": 2.4, "依據": {}}
    for a in AXES:
        v = picks.get("二選一", {}).get(a["id"])
        if v == "都不要":
            for k, x in RULES["都不要"].get(a["id"], {}).items():
                d[k] = {**d["motion"], **x} if k == "motion" else x
            d["依據"][a["id"]] = "都不要"
            continue
        if a["id"] in (flip or []):
            if v in (a["低"], a["高"]):
                v = a["高"] if v == a["低"] else a["低"]
            else:   # never picked: take the side that actually changes the default
                v = next((s for s in (a["高"], a["低"]) if any(d.get(k) != x and not (k == "motion" and all(d["motion"].get(i) == j for i, j in x.items()))
                                                             for k, x in a["換算"][s].items())), a["高"])
        if v not in (a["低"], a["高"]):
            continue
        for k, x in a["換算"][v].items():
            d[k] = {**d["motion"], **x} if k == "motion" else x
        d["依據"][a["id"]] = v
    if borrow and borrow.get("借"):
        d.update(borrow["借"])
        d["參考牆"] = {k: v for k, v in borrow["依據"].items()}
    return d


def _fit(lay_id: str, items: list[str], card: dict, size_field: bool) -> tuple[list[str], int | None]:
    """Largest font size (from the layout's own size down to its floor) at which every word fits and the wrapped lines fit the zone; one visual line per item."""
    lay = next(x for x in pb.layouts()["版型"] if x["id"] == lay_id)
    fx = lay["字框"]
    sizes = range(fx["字級"], fx["最小字級"] - 1, -4) if size_field else [fx["字級"]]
    for px in sizes:
        f = pb.text_fit(lay, {fx["欄位"]: items}, card, px)
        if f["最寬"] <= f["寬"] and f["總高"] <= f["高"]:
            break
    return [ln for r in f["行"] for ln in r], (int(px) if px != fx["字級"] else None)


def sample_card(d: dict, hook: str, points: list[str], photo: str | None) -> dict:
    """Two beats in the direction, written only with the user's own words (never the catalogue's sample text).
    Long lines are wrapped and the size lowered until they fit (card-check fails what still does not); tone and colour are made to show on the still frame."""
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
    dark = d["tone"] == "dark"
    vis = {"type": "photo", "image": img} if want_photo and img else {"type": "word", "text": re.sub(r"<[^>]+>", "", lines[0])[:6]} if want_photo else d["visual"]
    other = "light" if dark else "dark"
    card = {"width": 1080, "height": 1920, "platform": "reels-tiktok", "motion": d["motion"], "chrome": False,
            "brand": {"colors": d["色盤"], "fonts": {"heading": "IBM Plex Sans", "body": "IBM Plex Sans"}, "handle": ""}, "beats": []}
    hl, size = _fit("hook", lines, card, True)
    hl[-1] = f"<span class='accent'>{hl[-1]}</span>"     # the palette shows on the still: the last hook line in the accent colour
    hook_beat = {"layout": "hook", "seconds": max(2.2, sec), "text": hl, "visual": vis, "tone": d["tone"]}
    if size:
        hook_beat["size"] = size
    beats = [hook_beat]
    if want_photo and img:
        pl, size = _fit("photo", (pts or lines)[:2], card, True)
        b = {"layout": "photo", "image": img, "text": pl, "seconds": max(2.5, sec), "scrim": "dark" if dark else "top", "place": "mid" if dark else "top"}
        if size:
            b["size"] = size
        beats.append(b)
    elif d["字量"] == "多字" and len(pts) >= 2:
        beats.append({"layout": "checklist", "items": pts[:4], "seconds": max(3.0, sec + 1), "tone": other, "visual": {"type": "glow"} if want_photo else d["visual"]})
    else:
        sl, _ = _fit("statement", (pts or ["（第二句：用 --point 給）"])[:3], card, False)
        beats.append({"layout": "statement", "text": sl, "seconds": max(2.5, sec), "tone": other, "visual": {"type": "glow"}})
    card["beats"] = beats
    return card


def still_print(card: dict) -> list[tuple]:
    """What a still frame shows of a sample: per beat the layout, light or dark, scrim and text place, the picture layer, and the colours that are on screen."""
    c = card["brand"]["colors"]
    out = []
    for b in card["beats"]:
        v = b.get("visual") if isinstance(b.get("visual"), dict) else {}
        on_photo = b["layout"] == "photo" or v.get("type") == "photo"
        out.append((b["layout"], b.get("tone"), b.get("scrim"), b.get("place"), v.get("type"), c["accent"], None if on_photo else c["background"], None if on_photo else c["primary"]))
    return out


def label(d: dict, axis: str, default: str = "預設") -> str:
    v = d["依據"].get(axis)
    return "中性（兩邊都不要）" if v == "都不要" else v or default


def describe(d: dict) -> str:
    m, w = d["motion"], d.get("參考牆", {})
    rhythm = f"參考牆（{'、'.join(w['節奏'])}）" if "節奏" in w else label(d, "節奏", "中")
    colour = f"參考牆（{'、'.join(w['配色'])}）" if "配色" in w else label(d, "色彩", "收斂")
    return "；".join([f"節奏 {rhythm}（每段約 {d['每鏡秒']} 秒）", f"動態 {label(d, '動態', '未選')}・{m.get('preset', 'crisp')}" + (f"、進場 {m['enter']}" if m.get("enter") else ""),
                     f"字量 {d['字量']}", "畫面 " + ("照片" if d["visual"]["type"] == "photo" else "圖形"), f"色彩 {colour}", f"{'暗' if d['tone'] == 'dark' else '亮'}底"])


def variants(picks: dict, borrow: dict | None, hook: str, points: list[str], photo: str | None) -> list[tuple[str, dict, dict]]:
    """Three directions: 1 as picked; 2 and 3 each differ from every other on the still frame (tone, colours, layout, picture), never on a 都不要 axis.
    Axes picked 都可以 (or not at all) change first; the reference wall, when it lends something, goes into direction 2."""
    said = picks.get("二選一", {})
    weak = [a["id"] for a in AXES if said.get(a["id"]) in (None, "都可以")]
    vis = [x for x in weak if x in VISIBLE] + [x for x in VISIBLE if x not in weak]
    vis = [x for x in vis if said.get(x) != "都不要"]
    calm = [x for x in weak if x not in VISIBLE]       # rhythm or motion left open: changes too, though only the moving sample shows it
    lend = bool(borrow and borrow.get("借"))
    tries = [("照你的選擇＋參考牆", [], True)] if lend else []      # the wall goes into direction 2; direction 3 stays on your picks
    tries += [(f"改 {x}", [x], False) for x in vis]
    tries += [(f"改 {x}、{y}", [x, y], False) for i, x in enumerate(vis) for y in vis[i + 1:]]
    tries += [(f"照你的選擇＋參考牆，改 {x}", [x], True) for x in vis] if lend else []
    d1 = direction_from(picks)
    out = [("照你的選擇", d1, sample_card(d1, hook, points, photo))]
    for name, flip, use in tries:
        if len(out) == 3:
            break
        extra = calm[len(out) - 1:len(out)]
        d = direction_from(picks, flip + extra, borrow if use else None)
        card = sample_card(d, hook, points, photo)
        if all(still_print(card) != still_print(c) for _, _, c in out):
            out.append((name + (f"（另改 {extra[0]}）" if extra else ""), d, card))
    return out


def cmd_samples(a) -> int:
    pp = Path(a.picks)
    picks = json.loads(pp.read_text(encoding="utf-8"))
    out = Path(a.out or pp.parent)
    out.mkdir(parents=True, exist_ok=True)
    ref = ref_dir()
    I = json.loads((ref / "direction_index.json").read_text(encoding="utf-8")) if (ref / "direction_index.json").is_file() else None
    borrow = wall_borrow(picks, I)
    liked = wall_liked(picks)
    if liked:
        took = "、".join(f"{k}（{'、'.join(v)}）" for k, v in borrow["依據"].items()) or "沒有量得到的點"
        print(f"參考牆：要 {len(liked)} 支；借進方向 2：{took}" + (f"；只記錄：{'、'.join(borrow['只記錄'])}" if borrow["只記錄"] else "")
              + (f"；索引裡找不到：{'、'.join(borrow['找不到'])}" if borrow["找不到"] else "") + ("" if I else "（沒有參考索引，無法借用）"))
        pace = picks.get("二選一", {}).get("節奏")
        if "每鏡秒" in borrow["借"] and pace in ("快", "慢") and (borrow["借"]["每鏡秒"] > 2.4) == (pace == "快"):
            print(f"  注意：參考牆借的節奏（每段 {borrow['借']['每鏡秒']} 秒）和二選一的「{pace}」相反；方向 2 照參考牆，方向 1、3 照二選一，看樣片再決定")
    samples, ok = [], True
    pbx = [sys.executable, str(REPO / "pb.py")]
    for i, (name, d, card) in enumerate(variants(picks, borrow, a.hook, a.point or [], a.photo), 1):
        cp = out / f"sample{i}.json"
        cp.write_text(json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
        chk = subprocess.run(pbx + ["card-check", str(cp)], capture_output=True, text=True, env={**os.environ, "PLAYBOOK_HOME": str(REPO)})
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
        rec = {"方向": i, "名稱": name, "說明": describe(d), **d, "卡片": cp.name}
        if liked:
            rec["參考牆只記錄"] = borrow["只記錄"]
        (out / f"direction{i}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
        samples.append({"名稱": name, "差異": describe(d) + (f"（{d['說明補充']}）" if d.get("說明補充") else ""), "影片": mp4.name})
    if len(samples) < 3 and ok:
        print("只找得到 %d 個在定格上看得出差別的方向（其他軸都選了「都不要」）" % len(samples))
    picks["樣片資料夾"] = str(out.resolve())      # choose finds the samples from here, wherever --out put them
    pp.write_text(json.dumps(picks, ensure_ascii=False, indent=1), encoding="utf-8")
    if samples and not a.no_render:
        p = page(None, picks.get("需求", ""), [], out, samples, picks)
        print(f"\n第 3 步頁面：{p}\n  開法：`pb.py direction serve {out} --picks {pp}` 再開它印出的網址（app 內建瀏覽器也能播）；選一個方向會自動存回 picks.json"
              f"\n  然後：`pb.py direction choose {pp}`（方向編號和樣片資料夾都從 picks.json 讀）")
    return 0 if ok else 1


def samples_dir(a, picks: dict) -> tuple[Path | None, list[Path]]:
    pp = Path(a.picks)
    tried = [Path(a.samples)] if a.samples else []
    if picks.get("樣片資料夾"):
        tried.append(Path(picks["樣片資料夾"]))
    tried += [pp.parent, pp.parent / "samples"]
    n = a.n or picks.get("選")
    for d in tried:
        if n and (d / f"direction{n}.json").is_file():
            return d, tried
    return None, tried


def cmd_choose(a) -> int:
    pp = Path(a.picks)
    picks = json.loads(pp.read_text(encoding="utf-8"))
    if a.out and Path(a.out).is_dir() and list(Path(a.out).glob("direction[0-9].json")) and not a.samples:   # the old meaning of --out: the samples folder
        print(f"（--out 現在是方向卡的輸出檔；{a.out} 是樣片資料夾，當成 --samples {a.out}）")
        a.samples, a.out = a.out, None
    n = a.n or picks.get("選")
    if not n:
        sys.exit(f"{pp} 裡沒有「選」：在樣片頁選一個方向（serve 開的會自動存），或直接給編號：`pb.py direction choose {pp} 1`")
    folder, tried = samples_dir(a, picks)
    if not folder:
        sys.exit(f"找不到 direction{n}.json（找過：{'、'.join(str(t) for t in tried)}）。\n"
                 f"樣片在別的資料夾時：`pb.py direction choose {pp} {n} --samples <跑 samples 時 --out 的資料夾>`；還沒算樣片就先跑 `pb.py direction samples {pp} --hook \"鉤子句\"`")
    d = json.loads((folder / f"direction{n}.json").read_text(encoding="utf-8"))
    liked = wall_liked(picks)
    card = {"方向卡": "v1", "日期": dt.date.today().isoformat(), "需求": picks.get("需求", ""), "形式": picks.get("形式", ""),
            "選的方向": n, "說明": d["說明"], "motion": d["motion"], "tone": d["tone"], "字量": d["字量"], "版型群組": d["群組"],
            "visual": d["visual"], "色盤": d["色盤"], "每鏡秒": d["每鏡秒"], "二選一": picks.get("二選一", {}),
            "參考片": {"要": {k: v.get("點", []) for k, v in liked.items()}, "不要": [k for k, v in picks.get("參考牆", {}).items() if v.get("判") == "不要"],
                    "借進樣片": d.get("參考牆", {}), "只記錄": d.get("參考牆只記錄", {})},
            "樣片": str(folder / d["卡片"])}
    p = Path(a.out) if a.out else folder / "direction.json"
    p.write_text(json.dumps(card, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已寫出方向卡 {p}（方向 {n}{'，編號取自 picks.json 的「選」' if not a.n else ''}）\n{d['說明']}\n下一步：`pb.py storyboard --use SB-xx --emit card.json --direction {p}`（motion、明暗、色盤照方向卡）")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pb.py direction")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("index"); s.add_argument("--ref")
    s = sub.add_parser("page"); s.add_argument("need"); s.add_argument("--out", default="direction"); s.add_argument("--ref"); s.add_argument("--seed", type=int, default=7)
    s = sub.add_parser("samples"); s.add_argument("picks"); s.add_argument("--hook", required=True); s.add_argument("--point", action="append", help="the second line or points (repeatable; 「；」 also splits)"); s.add_argument("--photo"); s.add_argument("--out"); s.add_argument("--no-render", action="store_true")
    s = sub.add_parser("choose"); s.add_argument("picks"); s.add_argument("n", type=int, nargs="?", help="default: 選 in picks.json")
    s.add_argument("--samples", help="the folder samples wrote to (default: 樣片資料夾 in picks.json, then next to picks.json)"); s.add_argument("--out", help="the 方向卡 file (default: direction.json in the samples folder)")
    s = sub.add_parser("serve"); s.add_argument("dir", nargs="?", default="direction"); s.add_argument("--port", type=int, default=8765); s.add_argument("--picks", help="where choices are saved (default DIR/picks.json)"); s.add_argument("--ref")
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
        print(f"\n頁面：{p.resolve()}\n  開法：`pb.py direction serve {a.out}` 再開它印出的網址（app 內建瀏覽器也能播參考片，選擇自動存到 {a.out}/picks.json）；"
              f"系統瀏覽器也可以直接開檔，做完按下載。不要發佈，參考片是別人的作品")
        return 0
    return {"samples": cmd_samples, "choose": cmd_choose, "serve": cmd_serve}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
