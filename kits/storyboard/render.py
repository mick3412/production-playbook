"""(kit copy of playbook-bench render_card.py) Render a storyboard card with kits/storyboard/text_motion.html: seek the paused timeline frame by frame (Playwright), encode with ffmpeg.
usage: render_card.py card.json out.mp4 [--wire] [--scale 0.5] [--fps 24] [--audio voice.wav]
       render_card.py card.json out_dir --pages        carousel: one finished PNG per beat (card.height, e.g. 1350)"""
import argparse, http.server, threading, functools, subprocess, shutil, tempfile, json
from pathlib import Path
from playwright.sync_api import sync_playwright
ap = argparse.ArgumentParser(); ap.add_argument("card"); ap.add_argument("out"); ap.add_argument("--wire", action="store_true"); ap.add_argument("--scale", type=float, default=1)
ap.add_argument("--fps", type=int, default=24); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--pages", action="store_true"); ap.add_argument("--audio")
a = ap.parse_args()
REPO = Path(__file__).resolve().parents[2]   # the production-playbook folder
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(REPO)); h.log_message = lambda *x: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h); PORT = srv.server_address[1]   # a free port each run: two renders (or a preview server) never collide
threading.Thread(target=srv.serve_forever, daemon=True).start()
rel = Path(a.card).absolute()
if not str(rel).startswith(str(REPO)): raise SystemExit("card must sit under production-playbook (e.g. bench/runs/...)")
rel = rel.relative_to(REPO); C = json.loads(Path(a.card).read_text(encoding="utf-8")); H = C.get("height", 1920); W = C.get("width", 1080)
url = f"http://127.0.0.1:{PORT}/kits/storyboard/text_motion.html?card=/{rel}" + ("&wire=1" if a.wire else "")
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome"); pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=a.scale)
    if a.pages:
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        for i in range(len(C["beats"])):
            pg.goto(url + f"&page={i}"); pg.wait_for_function("window.__ready === true", timeout=30000); pg.wait_for_timeout(1500)
            pg.screenshot(path=str(out / f"page{i + 1:02d}.png")); print("page", i + 1, flush=True)
        b.close(); srv.shutdown(); raise SystemExit(0)
    tmp = Path(tempfile.mkdtemp(prefix="card_"))
    pg.goto(url); pg.wait_for_function("window.__ready === true", timeout=30000); pg.wait_for_timeout(2500)
    dur = pg.evaluate("window.__duration"); n = round(dur * a.fps)
    if a.limit: n = min(n, a.limit)
    for f in range(n):
        pg.evaluate("t => { window.__timelines.card.seek(t, false); }", f / a.fps); pg.screenshot(path=str(tmp / f"f{f:05d}.jpg"), type="jpeg", quality=92, timeout=20000)
        if f % 100 == 0: print("frame", f, "/", n, flush=True)
    b.close()
srv.shutdown()
cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(a.fps), "-i", str(tmp / "f%05d.jpg")]
if a.audio: cmd += ["-i", a.audio, "-af", "apad", "-c:a", "aac", "-b:a", "192k", "-shortest"]   # pad the voice so the picture keeps its full length
subprocess.run(cmd + ["-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", a.out], check=True)
shutil.rmtree(tmp); print(a.out, f"{dur:.1f}s", n, "frames")
