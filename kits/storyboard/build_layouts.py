"""Write kits/storyboard/layouts.json: the layout catalogue an agent follows (owner rule 2026-11-16).
An agent fills a card's FIELDS only; coordinates live in the kit. `pb.py card-check` validates a card against this file,
`video_qa` checks that read-text stays in the layout's text zone. Run: python3 kits/storyboard/build_layouts.py"""
import json
from pathlib import Path

OUT = Path(__file__).with_name("layouts.json")
A = "/kits/storyboard/gallery/assets/"
# text zone of the beat's padding box in 9:16 (x 148–960, y 400–1248) as % of the frame; full-frame layouts declare their own
FLOW = {"x": [13.7, 88.9], "y": [20.8, 65.0]}
SAFE = {"x": [11.1, 88.9], "y": [14.1, 65.0], "下半右緣": "y > 43.75% 時 x ≤ 72.2%"}

def F(name, kind, need=False, max=None, note=""):
    d = {"欄位": name, "型別": kind, "必填": need}
    if max is not None: d["上限"] = max
    if note: d["說明"] = note
    return d

# glyph advance widths (em) of IBM Plex Sans 600, measured in Chrome 2026-11-17; card-check uses them to tell whether a line still fits its text zone
GLYPHS = {"字型": "IBM Plex Sans", "說明": "IBM Plex Sans 600（套件預設字型）的字寬；card.brand.fonts.heading 是別的字型或有 theme 時，card-check 只給 WARN，要算圖後看定格確認", "全形": 1.0, "其他": 0.6, "em": {' ': 0.236, '!': 0.309, '"': 0.471, '#': 0.656, '$': 0.6, '%': 0.96, '&': 0.713, "'": 0.26, '(': 0.337, ')': 0.337, '*': 0.556, '+': 0.6, ',': 0.299, '-': 0.402, '.': 0.299, '/': 0.285, '0': 0.6, '1': 0.6, '2': 0.6, '3': 0.6, '4': 0.6, '5': 0.6, '6': 0.6, '7': 0.6, '8': 0.6, '9': 0.6, ':': 0.319, ';': 0.319, '<': 0.6, '=': 0.6, '>': 0.6, '?': 0.493, '@': 0.899, 'A': 0.682, 'B': 0.663, 'C': 0.63, 'D': 0.689, 'E': 0.6, 'F': 0.577, 'G': 0.712, 'H': 0.719, 'I': 0.423, 'J': 0.535, 'K': 0.678, 'L': 0.521, 'M': 0.817, 'N': 0.719, 'O': 0.712, 'P': 0.641, 'Q': 0.712, 'R': 0.664, 'S': 0.6, 'T': 0.596, 'U': 0.689, 'V': 0.642, 'W': 0.951, 'X': 0.655, 'Y': 0.632, 'Z': 0.599, '[': 0.329, '\\': 0.437, ']': 0.329, '^': 0.6, '_': 0.559, '`': 0.6, 'a': 0.559, 'b': 0.6, 'c': 0.508, 'd': 0.6, 'e': 0.558, 'f': 0.353, 'g': 0.55, 'h': 0.588, 'i': 0.275, 'j': 0.275, 'k': 0.562, 'l': 0.287, 'm': 0.888, 'n': 0.588, 'o': 0.563, 'p': 0.6, 'q': 0.6, 'r': 0.393, 's': 0.493, 't': 0.368, 'u': 0.588, 'v': 0.524, 'w': 0.819, 'x': 0.544, 'y': 0.524, 'z': 0.502, '{': 0.363, '|': 0.376, '}': 0.363, '~': 0.6, '’': 0.292, '—': 0.78}}

LAYOUTS = [
 # ---- 文字群 -------------------------------------------------------------------------------------------
 dict(id="hook", 名稱="鉤子大字", 群組="文字", 角色=["開場"], 用途="0.6 秒內出現的大字句子；第一段", 字區=FLOW,
      字框={"欄位": "text", "字級": 160, "行高": 1.0, "字距": -0.02, "最小字級": 96, "門檻字級": 160, "門檻說明": "160px 才量得到 8%（0.6 秒鉤子）"},
      欄位=[F("text", "字串陣列（每行一個）", True, "≤3 行、每行 ≤10 字元"), F("kicker", "字串", max="≤3 字"), F("size", "數字 px", note="預設 160（量起來 8%，過 0.6 秒鉤子）；每行 ≤7 字元才放到 180")],
      字級="主句 160px（審片量 8%）", 動態="逐行從遮罩升起 0.7 秒，間隔 0.09 秒；底線 0.6 秒畫出",
      畫面層="必填：沒有照片時用 bars／glow／numeral／word 之一；不能只有底色",
      範例={"layout": "hook", "seconds": 2.6, "text": ["10 years.", "<span class='accent'>One chart.</span>"], "visual": [{"type": "bars", "n": 7, "rising": True}]}),
 dict(id="statement", 名稱="陳述句", 群組="文字", 角色=["主體", "結論"], 用途="一個論點、一個條件、一句轉折", 字區={"x": [11.1, 88.9], "y": [20.8, 65.0]},
      字框={"欄位": "text", "字級": 84, "行高": 1.08, "字距": -0.015, "最小字級": 60},
      欄位=[F("text", "字串陣列", True, "≤4 行、每行 ≤20 字元"), F("kicker", "字串", max="≤3 字"), F("underline", "數字 px", note="底線長度；0 不畫")],
      字級="84px（4.4%）", 動態="逐行升起 0.7 秒", 畫面層="必填：glow、word 或照片",
      範例={"layout": "statement", "seconds": 4.4, "kicker": "And", "text": ["Past results", "are <span class='accent'>not a promise</span>", "of what comes next."], "visual": {"type": "glow"}}),
 dict(id="quote", 名稱="金句逐詞", 群組="文字", 角色=["開場", "主體"], 用途="金句、品牌信念（SB-T3）；關鍵詞最大", 字區=FLOW,
      欄位=[F("words", "物件陣列 {text, key}", True, "3–6 詞，恰好 1 個 key"), F("step", "秒", note="每詞間隔，預設 0.45"), F("kicker", "字串")],
      字級="一般詞 96px、關鍵詞 236px", 動態="逐詞升起；關鍵詞後畫底線", 畫面層="必填：word（重複關鍵詞）或照片",
      範例={"layout": "quote", "seconds": 4.0, "words": [{"text": "Time"}, {"text": "in the"}, {"text": "market", "key": True}], "visual": {"type": "word", "text": "market"}}),
 dict(id="takeaway", 名稱="結論大字", 群組="文字", 角色=["結論"], 用途="全片收束的一句", 字區=FLOW,
      欄位=[F("text", "字串陣列", True, "≤3 行")], 字級="134px", 動態="逐行升起＋420px 底線", 畫面層="必填",
      範例={"layout": "takeaway", "seconds": 3.0, "text": ["Stay", "the course."], "visual": {"type": "glow"}}),
 dict(id="question", 名稱="問句卡", 群組="文字", 角色=["開場", "主體"], 用途="訪談問題、觀眾會問的話（SB-K3）", 字區={"x": [15.2, 87.0], "y": [20.8, 68.8]},
      欄位=[F("text", "字串陣列", True, "≤3 行"), F("who", "字串", note="誰問的"), F("size", "數字 px", note="給了就不顯示大 Q，當鉤子用")],
      字級="104px", 動態="逐行升起", 畫面層="必填",
      範例={"layout": "question", "seconds": 3.5, "text": ["What if", "I cancel later?"], "who": "Asked at every workshop", "visual": {"type": "glow"}}),
 dict(id="story", 名稱="限動波浪字", 群組="文字", 角色=["開場", "主體"], 用途="限時動態（SB-K9）；可留投票貼紙位置", 字區={"x": [9.3, 90.7], "y": [17.2, 75.0]},
      欄位=[F("title", "字串（空格分詞）", True, "≤5 詞"), F("text", "字串", max="≤60 字元"), F("poll", "字串", note="App 內貼紙的位置；算圖時留空"), F("fine", "字串", note="合規小字")],
      字級="標題 132px", 動態="每個字母波浪彈入", 畫面層="主題 organic 自帶色塊；其他主題必填",
      範例={"layout": "story", "seconds": 5, "title": "New post today", "text": "Three numbers, thirty years.", "visual": {"type": "glow"}}),
 # ---- 數字群 -------------------------------------------------------------------------------------------
 dict(id="bignumber", 名稱="大數字", 群組="數字", 角色=["開場", "主體", "證據"], 用途="一個數字＋兩行說明", 字區=FLOW,
      欄位=[F("value", "數字", True), F("text", "字串陣列", True, "≤3 行"), F("prefix", "字串"), F("suffix", "字串"), F("decimals", "整數"), F("from", "數字"), F("size", "數字 px", note="預設 300；長數字 124–240")],
      字級="數字 300px（15.6%）、說明 84px", 動態="數字 1.4 秒跳到目標值（quartic out）", 畫面層="必填：bars 或 numeral 最常用",
      範例={"layout": "bignumber", "seconds": 4.0, "value": 7.7, "decimals": 1, "suffix": "%", "size": 220, "text": ["a year, 2014–2024", "(sample data)"], "visual": {"type": "bars", "n": 9}}),
 dict(id="reveal", 名稱="懸念揭曉", 群組="數字", 角色=["開場", "主體"], 用途="數字或詞先亂碼再定格（SB-T4）", 字區=FLOW,
      欄位=[F("big", "字串", True, "≤6 字元"), F("text", "字串陣列", max="≤2 行"), F("kicker", "字串"), F("scramble", "布林")],
      字級="236px", 動態="亂碼 → 定格＋掃光＋輕震", 畫面層="必填",
      範例={"layout": "reveal", "seconds": 3.0, "big": "140%", "text": ["of what?"], "visual": {"type": "grid"}}),
 dict(id="chart", 名稱="折線圖", 群組="數字", 角色=["證據"], 用途="長期數字、成長曲線（SB-T10）；標題寫結論", 字區={"x": [11.1, 88.9], "y": [20.8, 65.0]},
      欄位=[F("title", "字串陣列", True, "結論一句，≤1 行、每行 ≤18 字元"), F("points", "物件陣列 {t, v, label, side}", True, "3 點：起點、終點、一個轉折"), F("note", "字串", max="≤60 字元", note="單位與出處，≤8 個英文字；標題＋標籤＋註記合計 ≤17 字才讀得完 7 秒"), F("zero", "布林", note="數值軸從 0 開始；長條一定要，折線不從 0 時 note 寫明"), F("fill", "布林", note="曲線下面積只畫資料範圍（第一點到最後一點），停在基線；基線下方以淺色地面鋪滿到畫面邊緣與底部（畫面層）；zero:true 時基線就是 0，標 0"), F("prefix", "字串"), F("decimals", "整數"), F("draw", "秒")],
      字級="標題 84px、標籤 60px", 動態="先軸、後曲線 2.2 秒、點與標籤依序出現、數字跳動", 畫面層="fill:true 時自帶；否則必填",
      範例={"layout": "chart", "seconds": 7.0, "title": ["Rent: up 2.1×"], "points": [{"t": 2014, "v": 1200, "label": "2014", "side": "above"}, {"t": 2019, "v": 1650, "label": "2019", "side": "above"}, {"t": 2024, "v": 2520, "label": "2024", "side": "left"}], "prefix": "$", "note": "Median monthly rent, USD. Sample data.", "zero": True, "fill": True}),
 dict(id="table", 名稱="三欄比較頁", 群組="數字", 角色=["證據"], 用途="三個方案或期限並排（SB-C3）；輪播頁", 字區={"x": [6.7, 93.3], "y": [7.1, 89.0]}, 版面="1080×1350",
      欄位=[F("cols", "物件陣列 {k, v, s}", True, "恰好 3 欄；v ≤6 字元"), F("title", "字串陣列", True), F("kicker", "字串"), F("foot", "字串"), F("page", "字串")],
      字級="數值 104px", 動態="三欄依序彈入", 畫面層="靜態頁不受安全區限制：整頁排滿",
      範例={"layout": "table", "seconds": 5, "title": ["Three plans"], "cols": [{"k": "Basic", "v": "$9"}, {"k": "Plus", "v": "$19"}, {"k": "Pro", "v": "$39"}]}),
 # ---- 結構群 -------------------------------------------------------------------------------------------
 dict(id="steps", 名稱="步驟清單", 群組="結構", 角色=["主體"], 用途="3–5 步、清單、條件（SB-T1／T8）", 字區=FLOW,
      欄位=[F("items", "字串陣列", True, "3–5 條、每條 ≤24 字元"), F("title", "字串陣列"), F("kicker", "字串"), F("marks", "字串陣列", note="自訂編號，如 ✓"), F("step", "秒")],
      字級="條目 70px", 動態="逐條從左滑入，間隔 0.7 秒", 畫面層="必填：numeral（目前第幾步）或 bars",
      範例={"layout": "steps", "seconds": 6.8, "kicker": "Before you start", "items": ["Pick one goal", "Set a budget", "Book a slot"], "visual": {"type": "numeral", "text": "3"}}),
 dict(id="diagram", 名稱="圖解", 群組="結構", 角色=["主體", "證據"], 用途="框和箭頭講關係（R-02）；直式用 stack", 字區={"x": [11.1, 88.9], "y": [15.0, 65.0]},
      欄位=[F("title", "字串陣列", True, "≤3 行"), F("nodes", "物件陣列 {label, kind, x, y, w}", True, "2–4 個；直式加 stack:true"), F("edges", "[起, 迄] 陣列"), F("chapter", "字串"), F("stack", "布林"), F("note", "字串")],
      字級="框內 52px（直式）", 動態="框先出現，線在兩端框都出現後才畫，箭頭沿線移動", 畫面層="必填：grid＋numeral（章節）",
      範例={"layout": "diagram", "seconds": 6.3, "chapter": "CHAPTER 1", "title": ["How an order flows"], "stack": True, "nodes": [{"label": "Customer"}, {"label": "Shop", "kind": "key"}], "edges": [[0, 1]], "visual": [{"type": "grid"}, {"type": "numeral", "text": "1", "outline": True}]}),
 dict(id="compare", 名稱="A ≠ B", 群組="結構", 角色=["主體", "證據"], 用途="兩件常被混為一談的事", 字區=FLOW,
      欄位=[F("left", "字串", True, "≤14 字元"), F("right", "字串", True, "≤14 字元"), F("kicker", "字串"), F("note", "字串")],
      字級="框內 78px", 動態="左框、≠、右框依序", 畫面層="必填",
      範例={"layout": "compare", "seconds": 4.0, "left": "List price", "right": "What you pay", "note": "Taxes and fees differ.", "visual": {"type": "glow"}}),
 dict(id="notes", 名稱="條列說明頁", 群組="結構", 角色=["主體", "結尾"], 用途="多條重要資訊（輪播最後一頁、細則）", 字區={"x": [7.8, 92.2], "y": [6.7, 93.3]}, 版面="1080×1350",
      欄位=[F("points", "字串陣列", True, "≤8 條"), F("title", "字串"), F("foot", "字串")],
      字級="37px（輪播靜態頁）", 動態="逐條淡入", 畫面層="靜態頁：整頁排滿",
      範例={"layout": "notes", "seconds": 5, "title": "Before you decide", "points": ["Prices change.", "Read the full terms."]}),
 # ---- 照片群（自帶滿版畫面）-----------------------------------------------------------------------------
 dict(id="photo", 名稱="滿版照片＋字", 群組="照片", 角色=["開場", "主體", "證據"], 用途="真實照片故事（SB-P）", 字區={"x": [14.1, 88.9], "y": [15.6, 65.0]},
      字框={"欄位": "text", "字級": 92, "行高": 1.12, "字距": 0.01, "最小字級": 60, "大字": {"字級": 152, "行高": 1.04}},
      欄位=[F("image", "路徑", True, "真實照片，直式"), F("text", "字串陣列", True, "≤3 行"), F("tag", "字串", note="地點或時間膠囊"), F("big", "布林", note="大字版"), F("note", "字串"), F("place", "top|mid"), F("scrim", "top|dark|bottom|both"), F("push", "數字", note="慢推比例，≤1.05"), F("fg", "路徑", note="去背前景，做視差"), F("leak", "布林")],
      字級="92px，大字 152px", 動態="照片慢推 ≤5%，字升起", 畫面層="自帶：照片就是畫面層，鋪到底",
      範例={"layout": "photo", "seconds": 4.0, "image": A + "B_s11.jpg", "tag": "06:40 · Ubud", "text": ["Coffee before", "the valley wakes."]}),
 dict(id="speaker", 名稱="講者畫面", 群組="照片", 角色=["開場", "主體"], 用途="口播（SB-K）；攝影機畫面 full、Zoom 用半屏框", 字區={"x": [12.6, 88.9], "y": [15.1, 64.9]},
      欄位=[F("image", "路徑", True), F("topic", "字串", note="頂部固定標題"), F("hook", "字串", note="開場大字"), F("captions", "物件陣列 {text, at, role}", note="role：key／fact／plain"), F("name", "字串"), F("full", "布林"), F("zoom", "數字")],
      字級="字幕 64–84px", 動態="字幕依時間換句；照片輕推", 畫面層="自帶：full＝講者滿版；半屏＝模糊放大的同一畫面鋪底",
      範例={"layout": "speaker", "seconds": 5, "image": A + "B_s33.jpg", "full": True, "topic": "Three things I check first", "captions": [{"text": "Start with the light.", "at": 0.4, "role": "key"}]}),
 dict(id="cover", 名稱="封面頁", 群組="照片", 角色=["開場"], 用途="輪播封面（SB-C）；大標＋副標", 字區={"x": [8.9, 91.1], "y": [8.9, 60.0]}, 版面="1080×1350",
      欄位=[F("text", "字串陣列", True, "≤3 行"), F("sub", "字串"), F("kicker", "字串"), F("image", "路徑"), F("scrim", "top|dark"), F("swipe", "字串", note="滑動提示")],
      字級="118px", 動態="逐行升起", 畫面層="有 image 自帶；無 image 時整頁深色加 visual",
      範例={"layout": "cover", "seconds": 4, "kicker": "3 questions", "text": ["Ask these", "before you book"], "image": A + "A_s22.jpg", "swipe": "Swipe"}),
 dict(id="split", 名稱="上下分割 A／B", 群組="照片", 角色=["主體", "證據"], 用途="兩個選項或前後對照（SB-T5、SB-P8、SB-C3）：兩張照片上下各半鋪滿", 字區={"x": [13.7, 72.2], "y": [15.6, 65.0]},
      欄位=[F("a", "物件 {image, label, value, text}", True, "label ≤12 字元、value ≤6 字元"), F("b", "物件 {image, label, value, text}", True, "同 a"), F("vs", "布林", note="false 不顯示中間的 VS 圓章")],
      字級="數值 150px、標籤 50px", 動態="分隔線展開，上下標籤依序進場，照片反向慢推", 畫面層="自帶：兩張照片就是畫面層，鋪到底",
      範例={"layout": "split", "seconds": 5, "a": {"image": A + "A_s22.jpg", "label": "Stay in", "value": "$0"}, "b": {"image": A + "B_s11.jpg", "label": "Go out", "value": "$40"}}),
 dict(id="grid", 名稱="照片網格", 群組="照片", 角色=["開場", "主體"], 用途="4–6 張照片鋪滿畫面＋一條標題帶（SB-P4、SB-T7）", 字區={"x": [8.9, 91.1], "y": [15.6, 40.0]},
      欄位=[F("images", "路徑陣列", True, "4–6 張"), F("text", "字串陣列", True, "≤2 行"), F("kicker", "字串")],
      字級="標題 84px", 動態="照片依序淡入，標題帶最後進場", 畫面層="自帶：照片網格鋪滿",
      範例={"layout": "grid", "seconds": 4, "kicker": "Ubud", "text": ["4 quiet mornings"], "images": [A + "B_s11.jpg", A + "B_s33.jpg", A + "A_s22.jpg", A + "B_s11.jpg"]}),
 dict(id="checklist", 名稱="打勾清單", 群組="結構", 角色=["主體"], 用途="準備清單、條件逐項打勾（SB-T9、SB-C5）", 字區=FLOW,
      欄位=[F("items", "字串陣列", True, "3–5 條、每條 ≤20 字元"), F("title", "字串陣列"), F("kicker", "字串"), F("on", "整數", note="打勾幾項；預設全部"), F("step", "秒", note="每項間隔，預設 0.9")],
      字級="條目 70px", 動態="逐條滑入、方框內打勾", 畫面層="必填：numeral（項數）或 band",
      範例={"layout": "checklist", "seconds": 6, "title": ["Ready?"], "items": ["Tickets booked", "Bag packed", "Map saved"], "visual": {"type": "numeral", "text": "3"}}),
 # ---- 卡片頁群（輪播）---------------------------------------------------------------------------------
 dict(id="qa", 名稱="問答頁", 群組="卡片頁", 角色=["主體"], 用途="一頁一問一答（SB-C1）", 字區={"x": [6.7, 93.3], "y": [5.3, 94.7]}, 版面="1080×1350",
      欄位=[F("num", "字串", True, "編號，如 01"), F("q", "字串陣列", True, "≤3 行"), F("a", "字串", True, "≤180 字元"), F("src", "字串")],
      字級="問題 78px、答案 56px", 動態="問題升起、答案淡入", 畫面層="靜態頁：框線＋大編號排滿",
      範例={"layout": "qa", "seconds": 5, "num": "01", "q": ["What does it cost", "each month?"], "a": "A flat fee, plus any extras you choose. Sample answer."}),
 dict(id="verdict", 名稱="迷思判定頁", 群組="卡片頁", 角色=["主體"], 用途="迷思測驗（SB-C8）：題目頁不給 verdict，揭曉頁給", 字區={"x": [7.8, 92.2], "y": [5.3, 92.9]}, 版面="1080×1350",
      欄位=[F("myth", "字串", True, "≤60 字元"), F("verdict", "TRUE|FALSE"), F("why", "字串"), F("ask", "字串"), F("masthead", "字串"), F("src", "字串")],
      字級="題目 96px", 動態="蓋章砸下＋輕震", 畫面層="靜態頁：報頭與蓋章排滿",
      範例={"layout": "verdict", "seconds": 5, "masthead": "MYTH CHECK", "myth": "Bigger text is always easier to read.", "verdict": "FALSE", "why": "Past a size, lines wrap and reading slows."}),
 # ---- 收尾群 -------------------------------------------------------------------------------------------
 dict(id="cta", 名稱="行動卡", 群組="收尾", 角色=["結尾"], 用途="一個行動＋帳號", 字區={"x": [13.7, 88.9], "y": [21.9, 50.0]},
      欄位=[F("text", "字串陣列", True, "≤3 行"), F("sub", "字串"), F("handle", "字串")],
      字級="132px", 動態="逐行升起", 畫面層="必填（9:16）",
      範例={"layout": "cta", "seconds": 3, "text": ["Questions?", "Message us."], "handle": "@brand", "visual": {"type": "glow"}}),
 dict(id="disclosure", 名稱="合規結尾", 群組="收尾", 角色=["結尾"], 用途="必要聲明＋行動句；從安全區頂端往下長", 字區={"x": [11.1, 72.2], "y": [15.2, 66.7]},
      欄位=[F("text", "字串", True, "合規全文"), F("title", "字串"), F("cta", "字串", note="會被審片工具要求讀得到")],
      字級="54px（合規小字下限 2.5%）", 動態="淡入", 畫面層="建議 glow；不可蓋過小字的對比",
      範例={"layout": "disclosure", "seconds": 8.5, "title": "Important information", "cta": "Questions? Message us.", "text": "Sample notice. Replace it with the notice your project requires.", "visual": {"type": "glow"}}),
]

VISUALS = [
 {"type": "photo", "欄位": "image, push（≤1.06）, focus, scrim", "用途": "真實照片鋪滿全畫面；字層在上"},
 {"type": "glow", "欄位": "—", "用途": "兩團品牌色光暈慢慢漂移；最保守的填法"},
 {"type": "numeral", "欄位": "text, outline", "用途": "超大數字或字母從右下角出血（章節、步驟、年份）"},
 {"type": "bars", "欄位": "n, rising, seed", "用途": "品牌色柱從底邊升起；抽象的數字節奏"},
 {"type": "grid", "欄位": "—", "用途": "透視地面格線"},
 {"type": "band", "欄位": "—", "用途": "品牌色實心帶鋪滿下三分之一"},
 {"type": "word", "欄位": "text", "用途": "一個超大裝飾字沿底邊出血（重複本段已講過的詞）"},
]

# switching rules: measured 2026-11-16 on 230 FlexClip vertical templates with ≥3 shots (playbook-bench .../layout_switch/measure.py).
# Each shot was classed from its measured text (none / big / label / dense, plus top-mid-bottom); the classer agrees with hand labels on 66 of 80 shots (82.5 %),
# so the figures are reference ranges, not exact. Two readings agree: the AMOUNT of text stays put; the ARRANGEMENT changes every 1–2 shots.
SWITCH = {
 "狀態": "量測（2026-11-16，230 支 FlexClip 直式範本；分類與人工標註一致 82.5%，數字當參考範圍）",
 "量測": {"版型種類（中位／p75／p90）": "3／4／5", "主版型佔比（中位）": "50%", "同版型最長連用（中位／p75）": "2／4 鏡（照片故事 p75 6）",
          "開場與中段不同": "74%", "結尾與中段不同": "76%", "字量（無字／少字／多字）主類佔比": "80%，換字量的片只有約 3 成"},
 "角色": "開場 1 個版型、主版型 1 個（佔中段約一半以上）、輔助 1–2 個；開場和結尾通常和中段不同",
 "種類上限": {"≤30 秒": 4, ">30 秒": 5},
 "同版型連用上限": 3, "同版型連用上限（照片故事）": 5,
 "字量固定": "整支片的字量（無字／少字／多字）維持一種；要變化就換排法（大字 ↔ 標籤、上 ↔ 中 ↔ 下），不換字量",
 "換版時機": "只在內容角色改變時換（論點 → 證據 → 結論）；同一角色的段落用同一個版型",
 "錨點不變": ["字層邊界（安全區）", "標題位置", "品牌色", "字型", "畫面層類型在同一群組內延續"],
 "群組換場": {
  "同群組": "cut 或 fade",
  "文字↔數字": "色塊換場（預設 panel push）",
  "任何→照片": "fade（疊化 0.45 秒）",
  "照片→文字／數字／結構": "色塊換場",
  "任何→收尾": "色塊換場",
 },
}
DENSITY = {"hook": "少字", "statement": "少字", "quote": "少字", "takeaway": "少字", "question": "少字", "story": "少字", "bignumber": "少字", "reveal": "少字",
           "chart": "少字", "table": "多字", "steps": "多字", "diagram": "多字", "compare": "少字", "notes": "多字", "photo": "少字", "speaker": "少字",
           "cover": "少字", "split": "少字", "grid": "少字", "checklist": "多字", "qa": "多字", "verdict": "多字", "cta": "少字", "disclosure": "多字"}
for r in LAYOUTS: r["字量"] = DENSITY[r["id"]]

# Motion is a setting, not part of the layout (2026-11-17): each layout's 動態 above is written in the crisp numbers; card.motion (or a
# beat's own motion) re-times it. Keep MOTION in step with MOTION_PRESETS in text_motion.html (tests/test_layouts.py compares them).
MOTION = {
 "說明": "動態是設定，不是版型的一部分：每個版型的「動態」欄寫的是 crisp 預設的數值；card.motion（整支片）或 beat.motion（單段）可以換預設或調參數。"
         "只動畫面上已有的東西，不新增文字。寫法：\"motion\": {\"preset\": \"calm\"}，或 {\"preset\": \"crisp\", \"speed\": 0.9}。",
 "預設": {
  "crisp":  {"speed": 1,    "stagger": 1,   "enter": "mask",  "ease": None,         "transition": "panel", "適合": "預設；資訊型、乾淨俐落（套件原本的樣子）"},
  "calm":   {"speed": 0.75, "stagger": 1.4, "enter": "fade",  "ease": "power2.out", "transition": "fade",  "適合": "沉穩、高價、慢節奏的品牌；長句"},
  "soft":   {"speed": 0.85, "stagger": 1.2, "enter": "blur",  "ease": "sine.out",   "transition": "fade",  "適合": "生活感、照片故事、柔和調性"},
  "punchy": {"speed": 1.3,  "stagger": 0.7, "enter": "mask",  "ease": "expo.out",   "transition": "panel", "適合": "鉤子密集、快節奏、年輕調性"},
 },
 "欄位": {
  "preset": "crisp｜calm｜soft｜punchy",
  "speed": "0.5–1.6；>1 較快。進場時長與段內間隔 ×(1/speed)",
  "stagger": "0.5–2；多行、多項之間的間隔倍率",
  "enter": "mask（從遮罩升起）｜fade（淡入上移）｜blur（由模糊變清楚）｜scale（放大浮現）",
  "ease": "GSAP 緩動名，例如 power2.out；只換進場類緩動，back（彈出）、inOut、none 保留",
  "transition": "panel（色塊換場）｜fade（疊化）｜cut（硬切）；只在整支片層級。card.transition 有寫就以它為準",
 },
 "不受影響": "持續動態（ease none 的推近、漂移）、repeat／yoyo、跟配音對齊的時間（段落有 step 或 captions 時不移位置）",
 "範圍": {"speed": [0.5, 1.6], "stagger": [0.5, 2]},
 "進場": ["mask", "fade", "blur", "scale"],
 "換場": ["panel", "fade", "cut"],
}

D = {"說明": "版型圖鑑（2026-11-16 負責人規則）：兩層版面——字層只放要讀的字，守安全區 S0-06；畫面層（照片、背景、圖表延伸、特效）鋪滿全畫面，不受安全區限制，也不能留純色空白。"
           "代理只填欄位，不寫座標或 CSS；`pb.py card-check card.json` 驗證，`pb.py qa` 量字有沒有跑出字區。圖鑑頁：kits/storyboard/gallery/index.html。",
     "安全區": SAFE, "兩層": {"字層": "標題、內文、數字、標籤、CTA、合規小字；只能在字區內", "畫面層": "照片、影片、背景、圖表曲線與面積、圖解線框、色塊、裝飾大字；全畫面"},
     "版型": LAYOUTS, "字寬": GLYPHS, "畫面層元件": VISUALS, "換版規則": SWITCH, "動態設定": MOTION}
OUT.write_text(json.dumps(D, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(len(LAYOUTS), "layouts →", OUT)
