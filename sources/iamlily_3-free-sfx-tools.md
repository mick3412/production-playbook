# 3 個免費 AI 音效工具：讓 Claude Code 幫影片配上專業音效（IamLily／佳佳，Notion 公開頁，核對日 2026-10-29）

來源：https://app.notion.com/p/3-AI-Claude-Code-408c407363f38123b96feb73c2755fee
收錄：2026-10-29，用內建瀏覽器讀全文（含收合段落）。重點整理，不是全文；課程推薦段不收。

## 三個工具

| 工具 | 負責什麼 | 聲音來源 | 何時用 |
|---|---|---|---|
| Openverse（WordPress） | 搜尋、下載 | 真人錄音（Freesound、Wikimedia Commons、Jamendo），音訊約 521 萬筆 | 每次先用它找 |
| Real SFX（Clipwing 的 Claude Code 技能） | 看影片找出要加音效的時間點，從音效庫挑、對準那一格、音量不蓋人聲；附 critique 自我檢查、78 個 CC0 介面音效 | 你自己的音效庫 | 音效找好、要放進影片時 |
| earshot（MIT，CPU） | 用程式生音效（內建 252 種）或一整組風格統一的音效包；可當 MCP 工具 | 程式合成 | 找不到想要的聲音時 |

- Openverse API：`https://api.openverse.org/v1/audio/?q=<關鍵字>&license=cc0,by&page_size=10`，免金鑰；未登入每分鐘 20 次、每天 200 次。很多結果是音樂，用英文關鍵字（whoosh、pop、click、typing、notification、impact），必要時加 sound effect、跳過超過 3 秒的。
- Real SFX：https://github.com/Clipwing/skills（skills/real-sfx 整個資料夾）；需要 Python 3.9+、FFmpeg；`scripts/setup.py check`、`add-library ... --tier main --index`。它不會下載音效，只從音效庫挑。輸出：加好音效的 mp4、只有音效的 WAV、報告。
- earshot：https://github.com/Leonxlnx/earshot；venv＋CPU 版 torch；`earshot doctor`；`earshot sfx list / render`；`earshot kit init / render`。進階功能第一次會下載約 1.1 GB 模型（只生音效不需要）。

## 授權
CC0 最推薦；CC BY 可商用但要標作者；帶 NC（不能商用）、ND（不能改）、SA（改了要同授權）的，商用影片先不要用。指令要求整理「音效來源.md」：檔名、作者、授權、網址，CC BY 特別標出。

## 作者的做法與心得
1. Openverse 找 → 找不到的用 earshot 生 → Real SFX 放進影片 → 剪輯軟體微調。
2. 一定要分軌：按種類（咻、打字、點擊、彈出、提示音、重擊）拆成多條，每條從第 0 秒開始、長度和影片相同；只拿到混好的成片就無法調單一聲音。
3. AI 聽不到聲音，用數字判斷音量和位置；成品要戴耳機聽一次、手機喇叭聽一次，有問題報秒數請它改。
4. 同一支片用同一批來源的音效；前後段混用不同來源會聽起來不搭。
5. 音效一般 0.2–2 秒，太長的裁掉前後靜音；每種挑 2–3 個最短最乾淨的。
6. 修正說法例：「整體音效降 3 dB，講話時再壓低」「12.5 秒有東西彈出，加一個彈出音效」「同一種音效不要連續用同一個檔案，輪流換」。
