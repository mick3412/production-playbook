"""Build kits/storyboard/gallery/index.html from layouts.json: for every layout, the finished example and its wireframe
(visual layer grey, text zone blue, safe zone red dashed), the field table and the example JSON. For people: an agent follows layouts.json.
Run: python3 kits/storyboard/build_gallery.py   (renders with kits/storyboard/render.py; port 3394 must be free)"""
import json, subprocess, sys, html
from pathlib import Path
from PIL import Image, ImageDraw

K = Path(__file__).resolve().parent; G = K / "gallery"; G.mkdir(exist_ok=True); (G / "img").mkdir(exist_ok=True)
L = json.loads((K / "layouts.json").read_text(encoding="utf-8"))
BRAND = {"colors": {"primary": "#14213D", "background": "#F4EFE6", "accent": "#C9A227", "accent_ink": "#8A6D12"}, "fonts": {"heading": "IBM Plex Sans", "body": "IBM Plex Sans"}, "handle": "@brand"}

def card_for(rows, h):
    return {"width": 1080, "height": h, "brand": BRAND, "chrome": False, "transition": "cut", "beats": [dict(r["範例"], tone=("dark" if i % 2 else "light")) for i, r in enumerate(rows)]}

def render(rows, h, tag):
    c = G / f"_{tag}.json"; c.write_text(json.dumps(card_for(rows, h), ensure_ascii=False), encoding="utf-8")
    for wire, sub in ((False, "fin"), (True, "wire")):
        out = G / f"_{tag}_{sub}"
        cmd = [sys.executable, str(K / "render.py"), str(c), str(out), "--pages"] + (["--wire"] if wire else [])
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
    for i, r in enumerate(rows):
        fin = Image.open(G / f"_{tag}_fin" / f"page{i + 1:02d}.png").convert("RGB"); wire = Image.open(G / f"_{tag}_wire" / f"page{i + 1:02d}.png").convert("RGB")
        W, H = fin.size; d = ImageDraw.Draw(wire)
        if h == 1920:   # the safe zone (S0-06): red dashed; the lower-right cut-out drawn as two rectangles
            for x0, y0, x1, y1 in ((120, 270, 960, 840), (120, 840, 780, 1248)):
                for x in range(x0, x1, 28): d.line([(x, y0), (min(x + 14, x1), y0)], fill="#d33", width=5); d.line([(x, y1), (min(x + 14, x1), y1)], fill="#d33", width=5)
                for y in range(y0, y1, 28): d.line([(x0, y), (x0, min(y + 14, y1))], fill="#d33", width=5); d.line([(x1, y), (x1, min(y + 14, y1))], fill="#d33", width=5)
        z = r["字區"]; d.rectangle([z["x"][0] / 100 * W, z["y"][0] / 100 * H, z["x"][1] / 100 * W, z["y"][1] / 100 * H], outline="#1f6feb", width=7)
        fin.resize((W // 3, H // 3)).save(G / "img" / f"{r['id']}.jpg", quality=84); wire.resize((W // 3, H // 3)).save(G / "img" / f"{r['id']}_wire.jpg", quality=84)

tall = [r for r in L["版型"] if r.get("版面", "1080×1920") == "1080×1920"]; page = [r for r in L["版型"] if r.get("版面") == "1080×1350"]
render(tall, 1920, "tall"); render(page, 1350, "page")
for p in G.glob("_*"):
    if p.is_dir(): [f.unlink() for f in p.iterdir()]; p.rmdir()
    else: p.unlink()

e = html.escape
cards = []
for r in L["版型"]:
    rows = "".join(f"<tr><td><code>{e(f['欄位'])}</code></td><td>{e(f['型別'])}</td><td>{'必填' if f['必填'] else ''}</td><td>{e(str(f.get('上限', '')))}</td><td>{e(f.get('說明', ''))}</td></tr>" for f in r["欄位"])
    cards.append(f"""<section class="lay" id="{r['id']}"><div class="shots"><figure><img src="img/{r['id']}.jpg" alt="{e(r['名稱'])} 成品"><figcaption>成品</figcaption></figure><figure><img src="img/{r['id']}_wire.jpg" alt="{e(r['名稱'])} 線框"><figcaption>線框：淺藍塊＝字層元素，灰＝畫面層，藍框＝字區，紅虛線＝安全區</figcaption></figure></div>
<div class="spec"><h2><code>{r['id']}</code> {e(r['名稱'])}</h2><p class="meta">{e(r['群組'])}群組｜角色：{e('、'.join(r['角色']))}｜{e(r.get('版面', '1080×1920'))}</p><p>{e(r['用途'])}</p>
<dl><dt>字級</dt><dd>{e(r['字級'])}</dd><dt>動態</dt><dd>{e(r['動態'])}</dd><dt>畫面層</dt><dd>{e(r['畫面層'])}</dd></dl>
<div class="wrap"><table><tr><th>欄位</th><th>型別</th><th></th><th>上限</th><th>說明</th></tr>{rows}</table></div>
<details><summary>範例 JSON（直接貼進 card.json 的 beats）</summary><pre>{e(json.dumps(r['範例'], ensure_ascii=False, indent=1))}</pre></details></div></section>""")
vis = "".join(f"<tr><td><code>{e(v['type'])}</code></td><td>{e(v['欄位'])}</td><td>{e(v['用途'])}</td></tr>" for v in L["畫面層元件"])
sw = L["換版規則"]; swrows = "".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>" for k, v in sw["群組換場"].items())
nav = "".join(f"<a href='#{r['id']}'>{r['id']}</a>" for r in L["版型"])
(G / "index.html").write_text(f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>版型圖鑑</title>
<style>:root{{--bg:#faf8f4;--ink:#1c2a39;--mute:#5f6b78;--line:#e2ddd3;--code:#f0ebe1}}
@media (prefers-color-scheme:dark){{:root{{--bg:#15191e;--ink:#e8e4dc;--mute:#9aa3ad;--line:#2c333b;--code:#20262d}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,"PingFang TC",sans-serif}} main{{max-width:1180px;margin:auto;padding:24px 16px 80px}}
h1{{font-size:28px;margin:0}} .sub{{color:var(--mute)}} nav{{display:flex;flex-wrap:wrap;gap:6px;margin:16px 0}} nav a{{font:12px monospace;padding:3px 8px;border:1px solid var(--line);border-radius:12px;color:inherit;text-decoration:none}}
.lay{{display:grid;grid-template-columns:minmax(0,420px) minmax(0,1fr);gap:24px;border-top:1px solid var(--line);padding:28px 0}} @media (max-width:760px){{.lay{{grid-template-columns:1fr}}}}
.shots{{display:grid;grid-template-columns:1fr 1fr;gap:10px}} figure{{margin:0}} figure img{{width:100%;border:1px solid var(--line);border-radius:6px;display:block}} figcaption{{font-size:12px;color:var(--mute)}}
h2{{margin:0;font-size:20px}} .meta{{color:var(--mute);margin:2px 0 8px}} dl{{display:grid;grid-template-columns:70px 1fr;gap:4px 12px}} dt{{color:var(--mute)}} dd{{margin:0}}
.wrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;font-size:13px}} th,td{{border-bottom:1px solid var(--line);padding:5px 6px;text-align:left;vertical-align:top}} th{{color:var(--mute)}}
code,pre{{background:var(--code);border-radius:4px}} code{{padding:0 4px}} pre{{padding:10px;overflow-x:auto;font-size:12px}}</style></head><body><main>
<h1>版型圖鑑</h1><p class="sub">{e(L['說明'])}</p>
<p><b>兩層：</b>字層＝{e(L['兩層']['字層'])}。畫面層＝{e(L['兩層']['畫面層'])}。</p><nav>{nav}</nav>
<h2>畫面層元件（任何版型的 <code>visual</code> 欄位；可以放一個或一串）</h2><div class="wrap"><table><tr><th>type</th><th>欄位</th><th>用途</th></tr>{vis}</table></div>
<h2 style="margin-top:20px">換版規則（{e(sw['狀態'])}）</h2><p>{e(sw['角色'])}。種類上限：{e(json.dumps(sw['種類上限'], ensure_ascii=False))}；同一版型最多連用 {sw['同版型連用上限']} 段。{e(sw['換版時機'])}。不變的錨點：{e('、'.join(sw['錨點不變']))}。</p>
<div class="wrap"><table><tr><th>從哪群換到哪群</th><th>串場</th></tr>{swrows}</table></div>
{''.join(cards)}</main></body></html>""", encoding="utf-8")
print(len(L["版型"]), "layouts →", G / "index.html")
