#!/usr/bin/env python3
"""External same-type references (外找同類範本): step 0.5 shortlist with no downloads, step 1.2 study, step 6 similarity.

  find "需求" [--platform shorts|reels|tiktok|long] [--q 搜尋詞 …] [--region US] [--max 10] [--out DIR] [--no-local]
        search terms → local reference index first → YouTube/Shorts via yt-dlp metadata (no download) → hard filters,
        effectiveness (outlier ×, views/subs), feasibility, same-type reasons, score, de-dup → candidates.json,
        a local wall page (wall/index.html) and ad_links.md for the semi-automatic sources (ad libraries).
  serve DIR [--port 8766]        open the wall; picks and the download approval save to DIR/scout_picks.json
  add DIR <網址> …                add links the owner found (Meta Ad Library, TikTok, anything); public metadata only
  study DIR [--keep]             approved picks: download → probe breakdown --measure --words → transcript → beats → dHash
                                 → report.html, proposals.json, refs.md (rows for the L1–L4 table); purge at the end unless --keep
  purge DIR                      delete videos, audio and full-size frames; keep json, text and hashes (owner rule 2026-11-19)
  similar <成品.mp4> --refs DIR   finished video vs the studied references: structure, verbatim lines, frame hashes (S4-35)
  learn DIR                      add the studied references' numbers (no media) to the reference index, section 外部

Rules (thresholds, sources, weights) live in data/scout_rules.json. Nothing here downloads during find.
"""
from __future__ import annotations
import argparse, datetime as dt, hashlib, html, json, os, re, shutil, statistics, subprocess, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RULES = json.loads((REPO / "data" / "scout_rules.json").read_text(encoding="utf-8"))
STOP = set("a an the and or of for to in on with how what why is are your you my our this that it be by from at as 的 和 與 了 是 在".split())


def store() -> Path:
    s = RULES["存放"]
    return Path(os.environ.get(s["環境變數"]) or os.path.expanduser(s["預設"]))


def slug(s: str) -> str:
    t = re.sub(r"[^\w㐀-鿿]+", "-", s.lower()).strip("-")
    return (t[:40] or "need") + "-" + hashlib.sha1(s.encode()).hexdigest()[:6]


def tokens(s: str) -> set[str]:
    s = s.lower()
    en = {w for w in re.findall(r"[a-z0-9&]{3,}", s) if w not in STOP}
    zh = re.findall(r"[㐀-鿿]+", s)
    bi = {w[i:i + 2] for w in zh for i in range(max(1, len(w) - 1))}
    return en | {b for b in bi if b not in STOP}


# ---------------------------------------------------------------- the need → form, platform, search terms
def form_of(need: str) -> str:
    low = need.lower()
    try:
        forms = json.loads((REPO / "data" / "storyboards.json").read_text(encoding="utf-8"))["形式"]
        hits = {f: sum(1 for w in v.get("同義詞", []) if w.lower() in low) for f, v in forms.items()}
        best = max(hits, key=hits.get)
        if hits[best]:
            return best
    except Exception:
        pass
    words = RULES["同類"]["形式詞"]
    hits = {f: sum(1 for w in ws if w in low) for f, ws in words.items()}
    best = max(hits, key=hits.get)
    return best if hits[best] else "文字動態"


def platform_of(need: str, given: str | None) -> str:
    if given:
        return given
    low = need.lower()
    for k, words in {"reels": ["reels", "reel", "ig", "instagram"], "tiktok": ["tiktok", "抖音"], "shorts": ["shorts", "short"],
                     "long": ["youtube 長片", "long", "長片", "16:9", "橫式"]}.items():
        if any(w in low for w in words):
            return k
    return "shorts"


def make_queries(need: str, plat: str, extra: list[str] | None) -> list[str]:
    add = RULES["平台"][plat]["搜尋加詞"]
    base = extra or [re.sub(r"\b(reels?|shorts?|tiktok|ig|instagram)\b", "", need, flags=re.I).strip(" ：:,，")]
    out = []
    for q in base[: RULES["搜尋"]["最多組數"]]:
        out.append(f"{q} {add}".strip() if add and add not in q.lower() else q)
    return out


# ---------------------------------------------------------------- yt-dlp metadata (never downloads in find)
def cache_dir() -> Path:
    d = store() / "_cache"; d.mkdir(parents=True, exist_ok=True); return d


BLOCKED = {"yes": False, "why": ""}   # once YouTube says 429 / "not a bot", stop calling it for this run and keep what we have


def cached(key: str, fn):
    p = cache_dir() / (hashlib.sha1(key.encode()).hexdigest() + ".json")
    if p.is_file() and time.time() - p.stat().st_mtime < RULES["搜尋"]["快取天數"] * 86400:
        return json.loads(p.read_text(encoding="utf-8"))
    if BLOCKED["yes"]:
        return [] if not key.startswith("med:") else None
    v = fn()
    if v not in ([], None) and not BLOCKED["yes"]:   # never cache an empty answer: it may be a block, and a rerun should try again
        p.write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")
    time.sleep(RULES["搜尋"]["請求間隔秒"])
    return v


def ytdlp(args: list[str], timeout: int = 240) -> list[dict]:
    if not shutil.which("yt-dlp"):
        sys.exit("找不到 yt-dlp（T-34）：brew install yt-dlp")
    if BLOCKED["yes"]:
        return []
    try:
        p = subprocess.run(["yt-dlp", "--no-warnings", "--ignore-errors", "--skip-download", "--dump-json", *args],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return []
    if re.search(r"HTTP Error 429|confirm you.re not a bot", p.stderr):
        BLOCKED.update(yes=True, why="YouTube 暫時擋下（429／要求證明不是機器人）")
    out = []
    for line in p.stdout.splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return out


KEEP = ("id", "webpage_url", "title", "channel", "channel_url", "uploader_url", "duration", "view_count", "like_count", "channel_follower_count",
        "upload_date", "thumbnail", "width", "height", "description", "tags", "language", "extractor_key")


def slim(r: dict) -> dict:
    d = {k: r.get(k) for k in KEEP}
    d["description"] = (d.get("description") or "")[:400]
    d["tags"] = (d.get("tags") or [])[:20]
    return d


def yt_search(q: str, n: int) -> list[dict]:
    return cached(f"yt:{n}:{q}", lambda: [slim(r) for r in ytdlp([f"ytsearch{n}:{q}"])])


def yt_api(path: str, key: str, **q) -> dict:
    import urllib.request
    url = f"https://www.googleapis.com/youtube/v3/{path}?" + urllib.parse.urlencode({**q, "key": key})
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def iso_dur(s: str) -> float:
    m = re.fullmatch(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    return (int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)) if m else 0


def yt_api_search(q: str, key: str, short: bool) -> list[dict]:
    """YouTube Data API v3: search by view count, then video and channel statistics; same fields as the yt-dlp path."""
    def get():
        s = yt_api("search", key, part="snippet", q=q, type="video", order="viewCount", maxResults=25, **({"videoDuration": "short"} if short else {}))
        ids = [i["id"]["videoId"] for i in s.get("items", [])]
        if not ids:
            return []
        v = yt_api("videos", key, part="snippet,statistics,contentDetails", id=",".join(ids))
        chans = list({i["snippet"]["channelId"] for i in v.get("items", [])})
        c = yt_api("channels", key, part="statistics", id=",".join(chans[:50]))
        subs = {i["id"]: int(i["statistics"].get("subscriberCount", 0) or 0) for i in c.get("items", [])}
        out = []
        for i in v.get("items", []):
            sn, st = i["snippet"], i["statistics"]
            out.append({"id": i["id"], "webpage_url": f"https://www.youtube.com/watch?v={i['id']}", "title": sn.get("title"), "channel": sn.get("channelTitle"),
                        "channel_url": f"https://www.youtube.com/channel/{sn.get('channelId')}", "duration": iso_dur(i["contentDetails"].get("duration")),
                        "view_count": int(st.get("viewCount", 0) or 0), "like_count": int(st.get("likeCount", 0) or 0), "channel_follower_count": subs.get(sn.get("channelId")),
                        "upload_date": (sn.get("publishedAt") or "")[:10].replace("-", ""), "thumbnail": (sn.get("thumbnails", {}).get("high") or {}).get("url"),
                        "width": None, "height": None, "description": (sn.get("description") or "")[:400], "tags": (sn.get("tags") or [])[:20], "language": sn.get("defaultAudioLanguage")})
            if short and out[-1]["duration"] <= 60:
                out[-1]["width"], out[-1]["height"] = 1080, 1920   # the API has no frame size; a ≤60 s result of a Shorts search is treated as vertical
        return out
    return cached(f"api:{short}:{q}", get)


GENERIC = {"reels", "reel", "shorts", "short", "tiktok", "video", "videos", "ig", "instagram", "youtube", "explained", "explainer", "for", "beginners"}


def hashtags(queries: list[str], extra: list[str] | None = None) -> list[str]:
    """ytsearch hardly returns Shorts (tested 2026-11-19: 0 vertical in 45); the hashtag Shorts tab does. Tags: each query squashed, and its keyword pairs."""
    tags = list(extra or [])
    for q in queries:
        ws = [w for w in re.findall(r"[a-z0-9]+", q.lower().replace("&", "")) if w not in GENERIC and w not in STOP]
        if ws:
            tags.append("".join(ws))
        tags += ["".join(ws[i:i + 2]) for i in range(len(ws) - 1)]
    return list(dict.fromkeys(t for t in tags if 4 <= len(t) <= 30))[: RULES["搜尋"]["最多組數"] * 2]


def yt_shorts(tag: str, n: int) -> list[dict]:
    """Flat list of a hashtag's Shorts (url + views only, fast), then full metadata for the most viewed (channel, followers, date, size)."""
    flat = cached(f"tag:{n}:{tag}", lambda: [{"url": r.get("url"), "view_count": r.get("view_count")}
                                           for r in ytdlp(["--flat-playlist", "--playlist-end", str(n * 2), f"https://www.youtube.com/hashtag/{tag}/shorts"], timeout=90)])
    top = sorted([r for r in flat if r.get("url")], key=lambda r: -(r.get("view_count") or 0))[: RULES["搜尋"]["每個標籤細查"]]
    out = []
    for r in top:   # one at a time: many parallel page loads is what trips YouTube's bot check
        rows = cached(f"meta:{r['url']}", lambda: [slim(x) for x in ytdlp([r["url"]], timeout=60)])
        if rows:
            out.append(rows[0])
    return out


def channel_median(url: str | None, short: bool) -> float | None:
    if not url:
        return None
    n = RULES["搜尋"]["頻道取樣支數"]
    def get():
        for tab in (["/shorts", "/videos"] if short else ["/videos", "/shorts"]):
            rows = ytdlp(["--flat-playlist", "--playlist-end", str(n), url.rstrip("/") + tab], timeout=90)
            views = [r.get("view_count") for r in rows if isinstance(r.get("view_count"), (int, float))]
            if len(views) >= 4:
                return statistics.median(views)
        return None
    return cached(f"med:{short}:{url}", get)


# ---------------------------------------------------------------- local reference index first
def local_candidates(need: str, form: str, n: int) -> list[dict]:
    rules = json.loads((REPO / "data" / "direction_rules.json").read_text(encoding="utf-8"))["參考片"]
    ref = Path(os.environ.get(rules["環境變數"]) or os.path.expanduser(rules["預設"]))
    p = ref / "direction_index.json"
    if not p.is_file():
        return []
    I = json.loads(p.read_text(encoding="utf-8"))
    want = tokens(need) - GENERIC
    rows = []
    for v in I.get("外部", []) + I.get("片", []):
        if v.get("形式類") != form:
            continue
        text = " ".join(str(v.get(k, "")) for k in ("key", "標題", "形式", "目的", "節奏", "配色"))
        overlap = len(want & (tokens(text) - GENERIC))
        if overlap:   # same form alone is not enough: the topic must share a real word (platform words like "reels" don't count)
            rows.append((overlap, v))
    rows.sort(key=lambda x: -x[0])
    out = []
    for ov, v in rows[:n]:
        out.append({"id": "local:" + v.get("key", ""), "來源": "本地參考庫" + ("（外部，已研究）" if v.get("網址") else "（FlexClip）"),
                    "網址": v.get("網址") or "", "標題": v.get("標題") or v.get("key", ""), "頻道": "", "片長": v.get("片長"),
                    "形式": v.get("形式", ""), "目的": v.get("目的", ""), "每鏡秒": v.get("每鏡秒"), "縮圖": v.get("總覽") or "",
                    "同類理由": [f"形式相同（{form}）"] + ([f"主題字重疊 {ov} 個"] if ov else []), "可行性": "可行", "本地": True, "狀態": "未看"})
    return out


# ---------------------------------------------------------------- classify, filter, score
def age_months(d: str | None) -> float | None:
    if not d or not re.fullmatch(r"\d{8}", str(d)):
        return None
    t = dt.date(int(d[:4]), int(d[4:6]), int(d[6:]))
    return (dt.date.today() - t).days / 30.4


def feasibility(c: dict) -> str:
    text = " ".join([c.get("標題", ""), c.get("描述", ""), " ".join(c.get("標籤", []))]).lower()
    f = RULES["可行性"]
    if any(w in text for w in f["做不到"]):
        return "做不到"
    if any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in f["勉強"]):
        return "勉強"
    return "可行"


def same_type(c: dict, need: str, form: str, plat: str, topic_words: set | None = None) -> list[str]:
    P = RULES["平台"][plat]
    text = " ".join([c.get("標題", ""), c.get("描述", ""), " ".join(c.get("標籤", []))]).lower()
    why = []
    fw = [w for w in RULES["同類"]["形式詞"].get(form, []) if w in text]
    vertical = c.get("直式")
    if fw:   # a form word must actually appear; "no other form word" is not evidence
        why.append(f"形式相近（{form}：{'、'.join(fw[:3])}）")
    topic = topic_words or (tokens(need) - GENERIC)
    ov = topic & (tokens(text) - GENERIC)
    if len(ov) >= 2 or (len(ov) == 1 and len(topic) <= 3):
        why.append("主題相近（" + "、".join(sorted(ov)[:5]) + "）")
    d = c.get("片長") or 0
    lo, hi = RULES["硬過濾"]["長度倍數"]
    if vertical == P["直式"] and lo * P["長度上限"] <= d <= hi * P["長度上限"]:
        why.append(f"平台與長度相近（{'直式' if vertical else '橫式'}、{round(d)} 秒）")
    return why


def to_candidate(r: dict, q: str) -> dict:
    w, h = r.get("width"), r.get("height")
    return {"id": "yt:" + str(r.get("id")), "來源": "YouTube（yt-dlp 公開資料）", "網址": r.get("webpage_url") or f"https://www.youtube.com/watch?v={r.get('id')}",
            "平台": "YouTube", "標題": r.get("title") or "", "頻道": r.get("channel") or "", "頻道網址": r.get("channel_url") or r.get("uploader_url"),
            "片長": r.get("duration"), "發佈日": r.get("upload_date"), "觀看": r.get("view_count"), "讚": r.get("like_count"),
            "訂閱": r.get("channel_follower_count"), "直式": (h > w) if (w and h) else None, "縮圖": r.get("thumbnail") or "",
            "描述": r.get("description") or "", "標籤": r.get("tags") or [], "語言": r.get("language"), "搜尋詞": [q], "狀態": "未看"}


def hard_ok(c: dict, plat: str, level: dict) -> bool:
    P = RULES["平台"][plat]
    d = c.get("片長") or 0
    lo, hi = level["長度倍數"]
    if not (lo * P["長度上限"] <= d <= hi * P["長度上限"]):
        return False
    if level.get("直式", True) and c.get("直式") is not None and c["直式"] != P["直式"]:
        return False
    m = age_months(c.get("發佈日"))
    if m is not None and m > level["最舊月數"]:
        return False
    floor = level.get("最低觀看") or RULES["有效性"]["最低觀看"]["直式" if P["直式"] else "橫式"]
    return (c.get("觀看") or 0) >= floor


def effectiveness(c: dict) -> float:
    E = RULES["有效性"]
    import math
    def grade(x, good, great):   # log scale: 1 → 0, good → 0.6, great → 1
        if not x or x <= 1:
            return 0.0
        return min(1.0, 0.6 * math.log(x) / math.log(good)) if x < good else min(1.0, 0.6 + 0.4 * math.log(x / good) / math.log(great / good))
    if c.get("觀看") and c.get("訂閱"):
        c["觀看訂閱比"] = round(c["觀看"] / max(1, c["訂閱"]), 2)
    if c.get("投放天數"):   # ads: days still running
        x = c["投放天數"]; return 1.0 if x >= E["廣告投放天數"]["很好"] else 0.7 if x >= E["廣告投放天數"]["好"] else 0.3
    if c.get("離群倍數") is not None:   # the main signal: beats its own channel's median (S1-09)
        s = grade(c["離群倍數"], E["離群倍數"]["好"], E["離群倍數"]["很好"])
    elif c.get("觀看訂閱比") and (c.get("訂閱") or 0) >= E["觀看訂閱比最少訂閱"]:   # tiny channels make views/subs meaningless
        s = 0.8 * grade(c["觀看訂閱比"], E["觀看訂閱比"]["好"], E["觀看訂閱比"]["很好"])
    else:
        s = 0.2
    reach = min(1.0, math.log10(max(1, c.get("觀看") or 1)) / 6)   # a little weight for sheer reach (1M views = 1)
    return round(0.85 * s + 0.15 * reach, 3)


def score(c: dict) -> float:
    W = RULES["打分"]
    same = min(1.0, len(c.get("同類理由", [])) / 3)
    m = age_months(c.get("發佈日"))
    new = 0.5 if m is None else max(0.0, 1 - m / RULES["硬過濾"]["放寬"]["最舊月數"])
    feas = {"可行": 1.0, "勉強": 0.5, "做不到": 0.0}[c.get("可行性", "可行")]
    eff = effectiveness(c) if not c.get("本地") else 0.5
    c["分項"] = {"同類": round(same, 2), "有效性": round(eff, 2), "新近": round(new, 2), "可行": feas}
    return round(100 * (W["同類"] * same + W["有效性"] * eff + W["新近"] * new + W["可行"] * feas), 1)


def find(need: str, plat: str | None, qs: list[str] | None, region: str, mx: int, out: Path | None, local: bool, tags_extra: list[str] | None = None) -> Path:
    S = RULES["搜尋"]
    plat = platform_of(need, plat)
    form = form_of(need)
    out = out or store() / slug(need)
    out.mkdir(parents=True, exist_ok=True)
    queries = make_queries(need, plat, qs)
    t0 = time.time()
    vertical = RULES["平台"][plat]["直式"]
    key = os.environ.get(RULES["選用工具"]["YouTube API"]["環境變數"])
    if key:   # official API: sorted by views, no bot checks (search.list 100 units, videos/channels 1 unit each)
        results = [(q, yt_api_search(q, key, vertical)) for q in queries]
    else:
        results = [(q, yt_search(q, S["每組筆數"])) for q in queries]
        if vertical:   # Shorts come from hashtag Shorts tabs (ytsearch hardly returns them)
            results += [(f"#{t}", yt_shorts(t, S["每組筆數"])) for t in hashtags(queries, tags_extra)]
    seen, cands = {}, []
    for q, rows in results:
        for r in rows:
            c = to_candidate(r, q)
            if c["id"] in seen:
                seen[c["id"]]["搜尋詞"].append(q); continue
            seen[c["id"]] = c; cands.append(c)
    short = RULES["平台"][plat]["直式"]
    topic = set().union(*[tokens(x) for x in [need, *queries, *(tags_extra or [])]]) - GENERIC
    must = RULES["同類"].get("必要", "主題相近")
    for c in cands:   # cheap checks first (no network): same type and feasibility
        c["同類理由"] = same_type(c, need, form, plat, topic)
        c["可行性"] = feasibility(c)
    same = [c for c in cands if len(c["同類理由"]) >= RULES["同類"]["最少條件"] and any(w.startswith(must) for w in c["同類理由"]) and c["可行性"] != "做不到"]
    base = dict(RULES["硬過濾"]); level, relaxed = {"長度倍數": base["長度倍數"], "最舊月數": base["最舊月數"], "直式": True, "最低觀看": None}, []
    ok = [c for c in same if hard_ok(c, plat, level)]
    R = RULES["硬過濾"]["放寬"]
    for k in R["順序"]:   # relax one level at a time until enough same-type candidates remain
        if len(ok) >= R["最少支數"]:
            break
        level[k] = False if k == "直式" else R[k]; relaxed.append(k)
        ok = [c for c in same if hard_ok(c, plat, level)]
    with ThreadPoolExecutor(S["平行"]) as ex:   # channel medians only for the survivors
        meds = list(ex.map(lambda c: channel_median(c.get("頻道網址"), short), ok))
    for c, med in zip(ok, meds):
        c["頻道中位數"] = med
        if med and c.get("觀看"):
            c["離群倍數"] = round(c["觀看"] / max(1, med), 2)
        if relaxed:
            c["已放寬"] = relaxed[:]
    for c in ok:
        c["分數"] = score(c)
    ok.sort(key=lambda c: -c["分數"])
    per, picked = {}, []
    for c in ok:
        k = c.get("頻道") or c["id"]
        if per.get(k, 0) >= RULES["去重"]["同頻道最多"]:
            continue
        per[k] = per.get(k, 0) + 1; picked.append(c)
    loc = local_candidates(need, form, S["本地先比對上限"]) if local else []
    for c in loc:
        c["分數"] = score(c)
    final = loc + picked[: max(0, mx - len(loc))]
    meta = {"需求": need, "形式": form, "平台": plat, "地區": region, "搜尋詞": queries, "hashtag": hashtags(queries, tags_extra) if vertical else [], "已放寬": relaxed, "建立": dt.datetime.now().isoformat(timespec="seconds"),
            "搜尋結果": len(cands), "同類": len(same), "過硬過濾": len(ok), "耗時秒": round(time.time() - t0, 1), "資料來源": "YouTube Data API" if key else "yt-dlp 公開資料", "被擋": BLOCKED["why"],
            "說明": "零下載：只讀公開資料。同類理由與可行性由規則初判，代理看縮圖後可改寫或剔除。"}
    (out / "queries.json").write_text(json.dumps({"搜尋詞": queries, "說明": "可改寫後用 --q 重跑"}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "candidates.json").write_text(json.dumps({"meta": meta, "候選": final}, ensure_ascii=False, indent=1), encoding="utf-8")
    ad_links(out, need, queries, region)
    wall(out)
    print(f"候選 {len(final)} 支（本地 {len(loc)}、外部 {len(final) - len(loc)}；搜尋 {len(cands)} 支、耗時 {meta['耗時秒']} 秒"
          + (f"；已放寬：{'、'.join(relaxed)}" if relaxed else "") + f"）→ {out}")
    if BLOCKED["yes"]:
        print(f"注意：{BLOCKED['why']}。已查到的照用；過一段時間重跑會從快取接續，或設 YOUTUBE_API_KEY 改用官方 API。")
    for c in final:
        print(f"  {c['分數']:5}｜{c['標題'][:50]}｜{c.get('頻道','')}｜{c.get('片長')} 秒｜觀看 {c.get('觀看','—')}｜離群 {c.get('離群倍數','—')}×｜{'；'.join(c['同類理由'])}")
    print(f"開範本牆：pb.py scout serve {out}　廣告庫網址：{out / 'ad_links.md'}")
    return out


# ---------------------------------------------------------------- semi-automatic sources and the wall
def ad_links(out: Path, need: str, queries: list[str], region: str) -> None:
    q = urllib.parse.quote(queries[0] if queries else need)
    lines = [f"# 半自動來源（{need}）", "", "看完把好的連結用 `pb.py scout add <資料夾> <網址>` 補進候選。只記連結與指標，不在這些頁面下載影片。", ""]
    for s in RULES["半自動來源"]:
        lines += [f"## {s['名稱']}", f"- 網址：{s['網址'].format(q=q, region=region)}", f"- 誰看：{s['誰看']}", f"- 記什麼：{s['記什麼']}", f"- 條款：{s['條款']}", ""]
    (out / "ad_links.md").write_text("\n".join(lines), encoding="utf-8")


WALL_CSS = """:root{--bg:#f6f4ef;--ink:#1d2430;--mute:#667080;--line:#ddd8cc;--on:#2f7d4f;--off:#b23b3b}
@media (prefers-color-scheme:dark){:root{--bg:#15191e;--ink:#e9e5dd;--mute:#9aa3ad;--line:#2c333b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,"PingFang TC",sans-serif}
main{max-width:1180px;margin:auto;padding:20px 16px 120px}h1{font-size:24px;margin:0}.sub{color:var(--mute);margin:4px 0 18px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}
.card{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:color-mix(in srgb,var(--bg) 92%,#fff)}
.card img{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;background:#ccc}.b{padding:10px 12px}
.t{font-weight:600;margin:0 0 4px}.m{color:var(--mute);font-size:13px}.why{font-size:13px;margin:6px 0}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.row label{font-size:13px;border:1px solid var(--line);border-radius:20px;padding:2px 10px;cursor:pointer}
.pick{display:flex;gap:8px;margin-top:8px}.pick button{flex:1;padding:8px;border-radius:8px;border:1px solid var(--line);background:none;color:var(--ink);font:inherit;cursor:pointer}
.pick button.on.y{background:var(--on);color:#fff;border-color:var(--on)}.pick button.on.n{background:var(--off);color:#fff;border-color:var(--off)}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--bg);border-top:1px solid var(--line);padding:12px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.bar button{padding:10px 18px;border-radius:8px;border:0;background:var(--ink);color:var(--bg);font:inherit;font-weight:600;cursor:pointer}
a{color:inherit}"""


def thumb(c: dict, th: Path) -> str:
    """A small local copy of the platform thumbnail (some browsers block the CDN from a local page); purge deletes it with the rest."""
    import urllib.request
    src = c.get("縮圖") or ""
    m = re.search(r"youtube\.com/(?:watch\?v=|shorts/)([\w-]{11})", c.get("網址") or "")
    if m:
        src = f"https://i.ytimg.com/vi/{m.group(1)}/hqdefault.jpg"
    if not src.startswith("http"):
        return ""
    f = th / (re.sub(r"[^\w-]+", "_", c["id"]) + ".jpg")
    if not f.is_file():
        try:
            req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
            f.write_bytes(urllib.request.urlopen(req, timeout=10).read())
        except Exception:
            return src
    return "thumbs/" + f.name


def wall(out: Path) -> Path:
    D = json.loads((out / "candidates.json").read_text(encoding="utf-8"))
    m, cs = D["meta"], D["候選"]
    tags = ["鉤子", "節奏", "版型", "字幕", "配色", "音樂", "結構"]
    cards = []
    th = out / "wall" / "thumbs"; th.mkdir(parents=True, exist_ok=True)
    for c in cs:
        img = thumb(c, th)
        stats = " · ".join(x for x in [f"{c['片長']:.0f} 秒" if c.get("片長") else "", f"觀看 {c['觀看']:,}" if c.get("觀看") else "",
                                        f"離群 {c['離群倍數']}×" if c.get("離群倍數") else "", f"觀看/訂閱 {c['觀看訂閱比']}" if c.get("觀看訂閱比") else "",
                                        f"可行性 {c.get('可行性')}", f"分數 {c.get('分數')}"] if x)
        cards.append(f"""<div class="card" data-id="{html.escape(c['id'])}">{f'<img src="{html.escape(img)}" alt="" loading="lazy" referrerpolicy="no-referrer">' if img else ''}
<div class="b"><p class="t"><a href="{html.escape(c.get('網址') or '#')}" target="_blank" rel="noopener">{html.escape(c['標題'][:90])}</a></p>
<div class="m">{html.escape(c.get('頻道') or c.get('來源',''))}｜{html.escape(stats)}</div>
<div class="why">{'<br>'.join(html.escape(w) for w in c.get('同類理由', []))}</div>
<div class="pick"><button class="y">要</button><button class="n">不要</button></div>
<div class="row">{''.join(f'<label><input type="checkbox" value="{t}"> {t}</label>' for t in tags)}</div></div></div>""")
    page = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>同類範本牆</title><style>{WALL_CSS}</style></head><body><main>
<h1>同類範本牆</h1><p class="sub">{html.escape(m['需求'])}｜形式 {html.escape(m['形式'])}｜平台 {html.escape(m['平台'])}｜搜尋詞：{html.escape('、'.join(m['搜尋詞']))}{'｜已放寬：' + html.escape('、'.join(m['已放寬'])) if m.get('已放寬') else ''}<br>
勾 2–3 支「要」，標出要借的點，再按「核准下載」。只在本機開，不發佈。</p>
<div class="grid">{''.join(cards)}</div></main>
<div class="bar"><span id="n">已選 0 支</span><button id="save">存檔</button><button id="ok">核准下載所選</button><span id="msg" class="m"></span></div>
<script>
const st={{}};document.querySelectorAll('.card').forEach(c=>{{const id=c.dataset.id;st[id]={{選:null,借:[]}};
c.querySelectorAll('.pick button').forEach(b=>b.onclick=()=>{{st[id].選=b.classList.contains('y')?'要':'不要';c.querySelectorAll('.pick button').forEach(x=>x.classList.toggle('on',x===b));count()}});
c.querySelectorAll('input').forEach(i=>i.onchange=()=>{{st[id].借=[...c.querySelectorAll('input:checked')].map(x=>x.value)}})}});
function count(){{document.getElementById('n').textContent='已選 '+Object.values(st).filter(x=>x.選==='要').length+' 支'}}
async function save(ok){{const body={{選擇:st,核准下載:ok,時間:new Date().toISOString()}};const r=await fetch('/save',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});
document.getElementById('msg').textContent=r.ok?(ok?'已核准，回到對話說一聲':'已存檔'):'存檔失敗'}}
document.getElementById('save').onclick=()=>save(false);document.getElementById('ok').onclick=()=>save(true);
</script></body></html>"""
    p = out / "wall" / "index.html"; p.parent.mkdir(exist_ok=True); p.write_text(page, encoding="utf-8")
    return p


def serve(out: Path, port: int) -> int:
    import http.server
    out = out.resolve(); picks = out / "scout_picks.json"

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=str(out / "wall"), **k)

        def log_message(self, *a):
            pass

        def do_POST(self):
            origin, host = self.headers.get("Origin", ""), f"http://{self.headers.get('Host', '')}"
            n = int(self.headers.get("Content-Length") or 0)
            if self.path != "/save" or (origin and origin != host) or not 0 < n <= 500_000:
                self.send_error(403); return
            try:
                d = json.loads(self.rfile.read(n).decode("utf-8")); assert isinstance(d.get("選擇"), dict)
            except Exception:
                self.send_error(400); return
            picks.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            self.send_response(204); self.end_headers()

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
    print(f"範本牆：http://127.0.0.1:{port}/　（Ctrl-C 結束；選擇存到 {picks}）", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


def add(out: Path, urls: list[str]) -> int:
    p = out / "candidates.json"; D = json.loads(p.read_text(encoding="utf-8"))
    have = {c["網址"] for c in D["候選"]}
    for u in urls:
        if u in have:
            continue
        rows = [] if any(s in u for s in RULES["下載"]["無法自動下載"]) else ytdlp([u], timeout=120)
        if rows:
            c = to_candidate(slim(rows[0]), "負責人提供"); c["來源"] = "負責人提供（公開資料）"
        else:
            c = {"id": "manual:" + hashlib.sha1(u.encode()).hexdigest()[:8], "來源": "負責人提供（網頁讀不到資料）", "網址": u, "標題": u, "頻道": "",
                 "同類理由": ["負責人挑選"], "可行性": "可行", "狀態": "未看", "說明": "請補標題、指標；研究時需負責人螢幕錄影後放進 study/<id>/"}
        c.setdefault("同類理由", ["負責人挑選"]); c.setdefault("可行性", feasibility(c)); c["分數"] = score(c)
        D["候選"].append(c); print(f"已加入：{c['標題'][:60]}")
    p.write_text(json.dumps(D, ensure_ascii=False, indent=1), encoding="utf-8")
    wall(out)
    return 0


# ---------------------------------------------------------------- study: download → breakdown → transcript → beats → hashes → report
def approved(out: Path) -> list[dict]:
    p = out / "scout_picks.json"
    if not p.is_file():
        sys.exit("還沒有選擇：先 pb.py scout serve 在範本牆勾選並核准下載")
    P = json.loads(p.read_text(encoding="utf-8"))
    if not P.get("核准下載"):
        sys.exit("負責人還沒按「核准下載」（S1-07）")
    C = {c["id"]: c for c in json.loads((out / "candidates.json").read_text(encoding="utf-8"))["候選"]}
    return [{**C[k], "借": v.get("借", [])} for k, v in P["選擇"].items() if v.get("選") == "要" and k in C and not C[k].get("本地")]


def download(c: dict, d: Path) -> Path | None:
    have = [f for f in d.iterdir() if f.suffix.lower() in (".mp4", ".mov", ".webm", ".mkv")] if d.is_dir() else []
    if have:
        return have[0]
    u = c.get("網址") or ""
    if any(s in u for s in RULES["下載"]["無法自動下載"]):
        print(f"  {c['標題'][:40]}：這個來源不自動下載，請負責人螢幕錄影後放進 {d}/")
        return None
    d.mkdir(parents=True, exist_ok=True)
    args = ["yt-dlp", "--no-warnings", "-q", "-f", RULES["下載"]["格式"], "--merge-output-format", "mp4", "-o", str(d / "ref.%(ext)s")]
    if "instagram.com" in u:
        args += RULES["下載"]["Instagram"].split()
    subprocess.run(args + [u], timeout=900)
    got = [f for f in d.iterdir() if f.suffix.lower() == ".mp4"]
    return got[0] if got else None


def transcribe(video: Path, d: Path) -> list | None:
    T = RULES["選用工具"]["逐字稿"]
    code = ("import json,sys,mlx_whisper;r=mlx_whisper.transcribe(sys.argv[1],path_or_hf_repo=sys.argv[2],word_timestamps=True);"
            "w=[[x['word'].strip(),round(x['start'],2),round(x['end'],2)] for s in r['segments'] for x in s.get('words',[])];"
            "json.dump({'text':r['text'],'words':w},open(sys.argv[3],'w'),ensure_ascii=False)")
    out = d / "transcript.json"
    p = subprocess.run([os.path.expanduser(T["python"]), "-c", code, str(video), T["模型"], str(out)], capture_output=True, text=True, timeout=1200)
    if p.returncode or not out.is_file():
        print("  逐字稿略過（mlx_whisper 不可用）：" + p.stderr.strip()[-160:]); return None
    return json.loads(out.read_text(encoding="utf-8"))["words"]


def beats(video: Path, d: Path) -> list[float] | None:
    B = RULES["選用工具"]["節拍"]; py = os.path.expanduser(B["python"])
    if not Path(py).exists() and not shutil.which(py):
        return None
    wav = d / "audio.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-ac", "1", "-ar", "22050", str(wav)])
    code = "import json,sys,librosa;y,sr=librosa.load(sys.argv[1]);t,b=librosa.beat.beat_track(y=y,sr=sr,units='time');print(json.dumps([round(float(x),2) for x in b]))"
    p = subprocess.run([py, "-c", code, str(wav)], capture_output=True, text=True, timeout=600)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("  節拍略過（librosa 不可用）"); return None


def dhash(path: Path) -> str:
    from PIL import Image
    im = Image.open(path).convert("L").resize((9, 8))
    px = list(im.getdata())
    bits = "".join("1" if px[r * 9 + c] > px[r * 9 + c + 1] else "0" for r in range(8) for c in range(8))
    return f"{int(bits, 2):016x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def shot_text(s: dict) -> str:
    m = s.get("量測", {})
    seen = []
    for k in ("文字（進場）", "文字（中段）", "文字（出場）"):
        for b in (m.get(k) or {}).get("位置", []):
            if b.get("字") and b["字"] not in seen:
                seen.append(b["字"])
    return " ".join(seen)


def study_one(c: dict, out: Path) -> dict | None:
    d = out / "study" / re.sub(r"[^\w-]+", "_", c["id"])
    v = download(c, d)
    if not v:
        return None
    words = transcribe(v, d)
    if words and len({w[0].lower().strip(".,!?") for w in words}) < max(4, 0.3 * len(words)):
        print("  逐字稿多半是重複字（音樂被聽成字），當作沒有旁白"); words = None
    wj = None
    if words:
        wj = d / "words.json"; wj.write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    args = [sys.executable, str(REPO / "bin" / "video_probe.py"), "breakdown", str(v), "--out", str(d / "probe"), "--measure"] + (["--words", str(wj)] if wj else [])
    subprocess.run(args, capture_output=True, text=True, timeout=1800)
    bp = d / "probe" / "breakdown.json"
    if bp.is_file() and json.loads(bp.read_text(encoding="utf-8"))["鏡數"] == 1 and json.loads(bp.read_text(encoding="utf-8"))["片長"] > 8:
        subprocess.run(args + ["--threshold", "4"], capture_output=True, text=True, timeout=1800)   # soft transitions hide cuts at the default 10
    if not bp.is_file():
        print(f"  拆解失敗：{c['標題'][:40]}"); return None
    B = json.loads(bp.read_text(encoding="utf-8"))
    bt = beats(v, d)
    cuts = [s["起"] for s in B["鏡頭"][1:]]
    on_beat = round(sum(1 for x in cuts if bt and min(abs(x - y) for y in bt) <= 0.1) / len(cuts), 2) if (bt and cuts) else None
    for s in B["鏡頭"]:
        f = d / "probe" / s["關鍵格"]
        if f.is_file():
            s["dHash"] = dhash(f)
    B["節拍"] = {"拍點": bt, "切點踩拍比例": on_beat} if bt else None
    bp.write_text(json.dumps(B, ensure_ascii=False, indent=1), encoding="utf-8")
    secs = [s["秒數"] for s in B["鏡頭"]]
    text = " ".join(shot_text(s) for s in B["鏡頭"])
    wps = round(sum(len(re.findall(r"[A-Za-z]+", shot_text(s))) for s in B["鏡頭"]) / max(1, B["片長"]), 2)
    summ = {"id": c["id"], "標題": c["標題"], "網址": c["網址"], "頻道": c.get("頻道"), "觀看": c.get("觀看"), "離群倍數": c.get("離群倍數"),
            "借": c.get("借", []), "片長": B["片長"], "鏡數": B["鏡數"], "第一鏡秒": secs[0] if secs else None, "每鏡秒中位數": round(statistics.median(secs), 2) if secs else None,
            "每分鐘切點": B.get("每分鐘切點"), "剪輯節奏": B.get("剪輯節奏"), "畫面字每秒": wps, "切點踩拍比例": on_beat,
            "第一鏡畫面字": shot_text(B["鏡頭"][0]) if B["鏡頭"] else "", "開頭台詞": " ".join(w[0] for w in (words or []) if w[1] < 3)[:160],
            "秒數序列": secs, "畫面字": text[:2000], "逐字稿": " ".join(w[0] for w in (words or []))[:4000], "dHash": [s.get("dHash") for s in B["鏡頭"] if s.get("dHash")],
            "拆解卡": str(bp)}
    (d / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding="utf-8")
    return summ


def norms(form: str) -> dict:
    try:
        f = json.loads((REPO / "data" / "storyboards.json").read_text(encoding="utf-8"))["形式"][form]["常模"]
        first = f.get("第一鏡秒數", {}); each = f.get("每鏡秒數", {})
        return {"第一鏡秒": first.get("中位") or first.get("中位數"), "每鏡秒": each.get("中位") or each.get("中位數")}
    except Exception:
        return {}


def templates_for(need: str, form: str) -> list[str]:
    p = subprocess.run([sys.executable, str(REPO / "pb.py"), "storyboard", need, "--form", form], capture_output=True, text=True, timeout=60)
    return list(dict.fromkeys(re.findall(r"SB-[A-Z]\d+", p.stdout)))[:3]


def report(out: Path, rows: list[dict]) -> None:
    D = json.loads((out / "candidates.json").read_text(encoding="utf-8"))["meta"]
    N = norms(D["形式"]); med = lambda k: round(statistics.median([r[k] for r in rows if r.get(k) is not None]), 2) if any(r.get(k) is not None for r in rows) else None
    common = {"第一鏡秒": med("第一鏡秒"), "每鏡秒中位數": med("每鏡秒中位數"), "每分鐘切點": med("每分鐘切點"), "畫面字每秒": med("畫面字每秒"), "切點踩拍比例": med("切點踩拍比例")}
    def vs(k, nk):
        a, b = common.get(k), N.get(nk)
        return "" if not (a and b) else ("比手冊常模快" if a < b * 0.8 else "比手冊常模慢" if a > b * 1.2 else "和手冊常模相近")
    best = max(rows, key=lambda r: (r.get("離群倍數") or 0, r.get("觀看") or 0))
    sb = templates_for(D["需求"], D["形式"])
    borrow_all = sorted({t for r in rows for t in r.get("借", [])})
    proposals = [
        {"方向": "A 照這個類型的主流做", "學": f"每鏡約 {common['每鏡秒中位數']} 秒、第一鏡約 {common['第一鏡秒']} 秒（{len(rows)} 支中位數）", "不同": "內容與畫面全用自己的", "模板": sb[:1], "借": borrow_all, "不借": ["原片畫面", "原句", "人物與品牌"]},
        {"方向": f"B 學表現最好的一支（{best['標題'][:30]}）", "學": f"結構與節奏：{best['鏡數']} 鏡、每鏡 {best['每鏡秒中位數']} 秒" + (f"、離群 {best['離群倍數']}×" if best.get("離群倍數") else ""), "不同": "換掉它的鉤子句和畫面素材", "模板": sb[1:2] or sb[:1], "借": best.get("借", []), "不借": ["原片畫面", "原句"]},
        {"方向": "C 刻意和大家不同", "學": "沿用同類的資訊密度", "不同": ("節奏放慢一級（大家都快）" if (common["每鏡秒中位數"] or 9) < 2.5 else "節奏加快一級（大家都慢）"), "模板": sb[2:3] or sb[:1], "借": [], "不借": ["主流的開場方式"]}]
    for p in proposals:
        p["說明"] = "代理依報告改寫：寫清楚學哪支的哪一點、哪裡刻意不同；再進 1.0 用 pb.py direction samples 做方向樣片（S1-03、S1-11）"
    (out / "proposals.json").write_text(json.dumps({"需求": D["需求"], "共同點": common, "手冊常模": N, "提案": proposals}, ensure_ascii=False, indent=1), encoding="utf-8")
    refs = ["| 層 | 部位 | 參考 | 借的點 | 不借的點 | 我們的數值 |", "|---|---|---|---|---|---|"]
    for r in rows:
        refs.append(f"| L1 整體 | 節奏 | [{r['標題'][:30]}]({r['網址']}) | 每鏡 {r['每鏡秒中位數']} 秒、{r['剪輯節奏']} | 原片畫面、原句 | 待填 |")
        refs.append(f"| L2 結構 | 前 3 秒 | 同上 | 第一鏡 {r['第一鏡秒']} 秒；畫面字「{r['第一鏡畫面字'][:30]}」 | 原句不照用 | 待填 |")
    (out / "refs.md").write_text("# 參考表草稿（S1-10；L3、L4 依需要補）\n\n" + "\n".join(refs) + "\n", encoding="utf-8")
    def tr(r):
        return (f"<tr><td><a href='{html.escape(r['網址'])}'>{html.escape(r['標題'][:40])}</a></td><td>{r.get('觀看') or '—'}</td><td>{r.get('離群倍數') or '—'}</td><td>{r['鏡數']}</td>"
                f"<td>{r['第一鏡秒']}</td><td>{r['每鏡秒中位數']}</td><td>{r.get('每分鐘切點')}</td><td>{r['畫面字每秒']}</td><td>{r.get('切點踩拍比例') if r.get('切點踩拍比例') is not None else '—'}</td>"
                f"<td>{html.escape(r['第一鏡畫面字'][:40])}<br><span class=m>{html.escape(r['開頭台詞'][:80])}</span></td><td>{html.escape('、'.join(r.get('借', [])))}</td></tr>")
    body = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>同類範本報告</title>
<style>{WALL_CSS} table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{border-bottom:1px solid var(--line);padding:6px;text-align:left;vertical-align:top}} .wrap{{overflow-x:auto}} h2{{font-size:18px;margin-top:28px}}</style></head><body><main>
<h1>同類範本報告</h1><p class="sub">{html.escape(D['需求'])}｜形式 {html.escape(D['形式'])}｜{len(rows)} 支｜本機檢視，不發佈。範本影片研究完已刪除，只留數字與文字。</p>
<h2>每支量到的</h2><div class="wrap"><table><tr><th>範本</th><th>觀看</th><th>離群×</th><th>鏡數</th><th>第一鏡秒</th><th>每鏡秒</th><th>切點/分</th><th>畫面字/秒</th><th>踩拍</th><th>開頭（畫面字／台詞）</th><th>負責人要借</th></tr>{''.join(tr(r) for r in rows)}</table></div>
<h2>共同點</h2><ul><li>第一鏡 {common['第一鏡秒']} 秒；每鏡 {common['每鏡秒中位數']} 秒（{vs('每鏡秒中位數','每鏡秒')}，手冊常模 {N.get('每鏡秒')}）</li><li>每分鐘切點 {common['每分鐘切點']}；畫面字每秒 {common['畫面字每秒']}</li><li>切點踩拍比例 {common['切點踩拍比例'] if common['切點踩拍比例'] is not None else '沒量到'}</li></ul>
<h2>方向提案（草稿，代理改寫後給負責人選）</h2><ol>{''.join(f"<li><b>{html.escape(p['方向'])}</b>：學 {html.escape(p['學'])}；不同：{html.escape(p['不同'])}；模板 {html.escape('、'.join(p['模板']))}</li>" for p in proposals)}</ol>
<h2>代理要補的</h2><ul><li>每支的鉤子類型、結構骨架、版型代號（看 probe 的格子，標「代理判讀」）</li><li>差異與空白：大家都做／少數做且表現好／沒人做</li><li>參考表草稿 refs.md 補 L3、L4 與「我們的數值」</li></ul>
</main></body></html>"""
    (out / "report.html").write_text(body, encoding="utf-8")


def study(out: Path, keep: bool) -> int:
    picks = approved(out)
    if not picks:
        sys.exit("範本牆沒有勾「要」的外部範本")
    rows = []
    for c in picks:
        print(f"研究：{c['標題'][:60]}", flush=True)
        r = study_one(c, out)
        if r:
            rows.append(r)
    if not rows:
        sys.exit("沒有一支研究成功（下載或拆解失敗）")
    report(out, rows)
    print(f"報告：{out / 'report.html'}；方向提案：{out / 'proposals.json'}；參考表草稿：{out / 'refs.md'}")
    if not keep:
        purge(out)
    return 0


def purge(out: Path) -> int:
    G = RULES["刪檔"]; gone = []
    for f in [*((out / "study").rglob("*") if (out / "study").is_dir() else []), *((out / "wall" / "thumbs").glob("*") if (out / "wall" / "thumbs").is_dir() else [])]:
        if f.is_file() and (f.suffix.lower() in G["副檔名"] or any(f.match(p) for p in G["全尺寸格"]) or f.parent.name == "thumbs"):
            gone.append(str(f.relative_to(out))); f.unlink()
    with (out / "purge.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{dt.datetime.now().isoformat(timespec='seconds')} 刪除 {len(gone)} 個檔案：{', '.join(gone[:50])}{' …' if len(gone) > 50 else ''}\n")
    print(f"已刪除 {len(gone)} 個影片、音訊與畫格檔（保留 json 與文字）")
    return 0


# ---------------------------------------------------------------- similarity (step 6) and learning back into the index
def ngrams(text: str, n: int, zh: bool) -> set:
    toks = re.findall(r"[㐀-鿿]", text) if zh else re.findall(r"\b[a-z][a-z']+\b", text.lower())   # real words only: OCR noise like "1n9e" never counts
    grams = {" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)}
    return grams if zh else {g for g in grams if sum(len(w) >= 3 for w in g.split()) >= n - 2}


def corr(a: list[float], b: list[float]) -> float | None:
    if len(a) != len(b) or len(a) < 3:
        return None
    ma, mb = statistics.mean(a), statistics.mean(b)   # Pearson by hand: the system Python is 3.9 (no statistics.correlation)
    sa = sum((x - ma) ** 2 for x in a) ** 0.5; sb = sum((y - mb) ** 2 for y in b) ** 0.5
    return None if not sa or not sb else sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb)


def similar(video: str, refs: Path, words: str | None = None) -> int:
    S = RULES["相似度"]
    tmp = refs / "_similar"
    subprocess.run([sys.executable, str(REPO / "bin" / "video_probe.py"), "breakdown", video, "--out", str(tmp), "--measure"], capture_output=True, text=True, timeout=1800)
    B = json.loads((tmp / "breakdown.json").read_text(encoding="utf-8"))
    secs = [s["秒數"] for s in B["鏡頭"]]
    text = " ".join(shot_text(s) for s in B["鏡頭"]) + " " + (" ".join(w[0] for w in json.loads(Path(words).read_text())) if words else "")
    hashes = [dhash(tmp / s["關鍵格"]) for s in B["鏡頭"] if (tmp / s["關鍵格"]).is_file()]
    verdict, lines = "PASS", []
    for sp in sorted((refs / "study").glob("*/summary.json")):
        R = json.loads(sp.read_text(encoding="utf-8")); name = R["標題"][:40]
        c = corr(secs, R["秒數序列"])
        if c is not None and c >= S["結構相關係數"]:
            lines.append(f"WARN 結構太像「{name}」：{len(secs)} 鏡、秒數相關 {c:.2f}"); verdict = "WARN" if verdict == "PASS" else verdict
        ref_text = R.get("畫面字", "") + " " + R.get("逐字稿", "")
        same = (ngrams(text, S["原句英文字數"], False) & ngrams(ref_text, S["原句英文字數"], False)) | (ngrams(text, S["原句中文字數"], True) & ngrams(ref_text, S["原句中文字數"], True))
        if same:
            lines.append(f"FAIL 出現「{name}」的原句：{sorted(same)[0][:60]}"); verdict = "FAIL"
        near = min((hamming(a, b) for a in hashes for b in R.get("dHash", [])), default=99)
        if near <= S["dHash 距離"]:
            lines.append(f"WARN 有一格畫面太像「{name}」（dHash 距離 {near}）"); verdict = "WARN" if verdict == "PASS" else verdict
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"相似度檢查：{verdict}"); [print("  " + x) for x in lines]
    return 1 if verdict == "FAIL" else 0


def learn(out: Path) -> int:
    rules = json.loads((REPO / "data" / "direction_rules.json").read_text(encoding="utf-8"))["參考片"]
    ref = Path(os.environ.get(rules["環境變數"]) or os.path.expanduser(rules["預設"]))
    p = ref / "direction_index.json"
    I = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"片": []}
    meta = json.loads((out / "candidates.json").read_text(encoding="utf-8"))["meta"]
    ext = {v.get("網址"): v for v in I.get("外部", [])}
    n = 0
    for sp in sorted((out / "study").glob("*/summary.json")):
        R = json.loads(sp.read_text(encoding="utf-8"))
        ext[R["網址"]] = {"key": R["id"], "標題": R["標題"], "網址": R["網址"], "形式類": meta["形式"], "形式": meta["形式"], "目的": meta["需求"],
                          "片長": R["片長"], "每鏡秒": R["每鏡秒中位數"], "第一鏡秒": R["第一鏡秒"], "畫面字每秒": R["畫面字每秒"], "觀看": R.get("觀看"),
                          "離群倍數": R.get("離群倍數"), "借": R.get("借", []), "加入": dt.date.today().isoformat(), "媒體": "已刪除（只留數值）"}
        n += 1
    I["外部"] = list(ext.values())
    p.write_text(json.dumps(I, ensure_ascii=False), encoding="utf-8")
    print(f"已把 {n} 支外部範本的數值併入 {p}（外部區，共 {len(I['外部'])} 支）")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pb.py scout", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("find"); p.add_argument("need"); p.add_argument("--platform", choices=list(RULES["平台"])); p.add_argument("--q", action="append")
    p.add_argument("--region", default="US"); p.add_argument("--max", type=int, default=RULES["搜尋"]["輸出上限"]); p.add_argument("--out"); p.add_argument("--no-local", action="store_true"); p.add_argument("--tag", action="append", help="extra hashtag for the Shorts tab, without #")
    p = sub.add_parser("serve"); p.add_argument("dir"); p.add_argument("--port", type=int, default=8766)
    p = sub.add_parser("add"); p.add_argument("dir"); p.add_argument("urls", nargs="+")
    p = sub.add_parser("study"); p.add_argument("dir"); p.add_argument("--keep", action="store_true")
    p = sub.add_parser("purge"); p.add_argument("dir")
    p = sub.add_parser("similar"); p.add_argument("video"); p.add_argument("--refs", required=True); p.add_argument("--words")
    p = sub.add_parser("learn"); p.add_argument("dir")
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in {"find", "serve", "add", "study", "purge", "similar", "learn", "-h", "--help"}:
        argv = ["find", *argv]   # pb.py scout "需求" is the one-command entry point
    a = ap.parse_args(argv)
    if a.cmd == "find":
        find(a.need, a.platform, a.q, a.region, a.max, Path(a.out).expanduser() if a.out else None, not a.no_local, a.tag); return 0
    if a.cmd == "serve":
        return serve(Path(a.dir).expanduser(), a.port)
    if a.cmd == "add":
        return add(Path(a.dir).expanduser(), a.urls)
    if a.cmd == "study":
        return study(Path(a.dir).expanduser(), a.keep)
    if a.cmd == "purge":
        return purge(Path(a.dir).expanduser())
    if a.cmd == "similar":
        return similar(a.video, Path(a.refs).expanduser(), a.words)
    if a.cmd == "learn":
        return learn(Path(a.dir).expanduser())
    ap.print_help(); return 0


if __name__ == "__main__":
    sys.exit(main())
