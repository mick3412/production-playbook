#!/usr/bin/env python3
"""Find where a music track's energy rises the most (its "drop" or climax).

Usage: python3 bin/music_drop.py song.mp3 [--min-rise 3]

Measures short-term loudness (EBU R128, 3 s window) with ffmpeg, averages it per
second, skips silent stretches, and reports the second where the next 4 s are
loudest compared with the 6 s before. A rise under --min-rise LU means the
track has no clear climax; pick the section by ear instead. Needs ffmpeg only.
"""
import argparse, re, subprocess

ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("--min-rise", type=float, default=3.0)
a = ap.parse_args()

out = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", a.audio, "-af",
                      "ebur128=metadata=1,ametadata=print:key=lavfi.r128.S:file=-", "-f", "null", "-"],
                     capture_output=True, text=True).stdout
t, bins = None, {}
for line in out.splitlines():
    m = re.search(r"pts_time:([\d.]+)", line)
    if m:
        t = float(m.group(1))
    m = re.search(r"lavfi.r128.S=(-?[\d.]+)", line)
    if m and t is not None:
        bins.setdefault(int(t), []).append(float(m.group(1)))
sec = [(k, sum(v) / len(v)) for k, v in sorted(bins.items())]
if len(sec) < 12:
    raise SystemExit("track too short (need 12 s or more)")

best = None
for i in range(6, len(sec) - 4):
    window = [x for _, x in sec[i - 6:i]]
    if min(window) < -45:          # silence or fade-in: not a drop
        continue
    before, after = sum(window) / 6, sum(x for _, x in sec[i:i + 4]) / 4
    if best is None or after - before > best[1]:
        best = (sec[i][0], after - before, before, after)

print(f"length {sec[-1][0]} s")
if best is None or best[1] < a.min_rise:
    rise = f"{best[1]:.1f}" if best else "n/a"
    print(f"no clear climax (largest rise {rise} LU < {a.min_rise}); choose the section by ear")
else:
    s = best[0]
    print(f"climax at {s} s: {best[2]:.1f} -> {best[3]:.1f} LUFS (+{best[1]:.1f} LU)")
    print(f"30 s cut that lands the climax at second 18: {max(0, s - 18)}-{max(0, s - 18) + 30} s")
step = max(1, len(sec) // 20)
print("curve:", " ".join(f"{k}s:{v:.0f}" for k, v in sec[::step]))
