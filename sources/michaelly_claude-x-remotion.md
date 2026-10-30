# Claude × Remotion: Edit Your Videos by Talking（Michael Ly，milleemd.com，更新於 2026-10-14）

來源：https://milleemd.com/guides/claude-x-remotion/（收錄時已拿掉網址裡的 mcp_token 和 fbclid）
收錄：2026-10-31，用內建瀏覽器讀全文。重點整理，不是全文。

## 四個部件
- Remotion：主編輯器，放素材、時間軸、字幕、圖形、配樂和最後算圖；每個字幕和圖形都釘在確切的影格上。
- HyperFrames：特效來源（3D、液態玻璃、shader 轉場、手繪標註）；只算需要的片段，放回 Remotion，由 Remotion 主導。
- 技能（remotion-reel，放在 Google Drive 的 zip）：教 Claude 怎麼剪：先量素材、字幕對字、圖形避開臉和裁切區、配樂壓在人聲下、每次算圖都檢查。沒有收錄也沒有安裝。
- 品牌表 brand/BRAND.md：色、字、字幕樣式、標題樣式、母題、常用音效；放在專案裡，和技能分開。

## 工作流程
1. 專案骨架：Remotion（1080x1920、30fps）、ffmpeg、whisper.cpp base.en 逐字時間（{text, startMs, endMs}）、素材資料夾。
2. 第一次剪之前先建品牌表：從自己的網站或喜歡的舊片擷取，給樣本定格，核准才用。
3. Brand Lab：做約 20 個品牌動態樣本（背景、標題、圖表、畫面版型、全螢幕時刻、轉場、音效），逐一標 Keep／Maybe／Drop 並寫備註；Maybe 依備註重做，兩三輪後留下的成為固定風格。
4. 拍攝：不用怕停頓和重來（超過 0.1 秒的空白都剪掉）；頭頂留空間；能拍 4K 就拍 4K（跳切會放大）；iPhone HDR 要轉換，膚色才自然；重點字講清楚。
5. 第一版：放素材、描述要什麼，Claude 算出分鏡審閱頁：每一拍一段短片，逐拍標 Keep／Maybe／Drop 並寫備註再送出；Claude 依備註修改並逐條回覆。
6. 給人看之前先自查：影格數、掃壞格、量配樂和每個音效對人聲的音量。

## 好用的修改說法
「標題出現太晚、消失太早」「我講到 gone viral 時，全螢幕顯示數字面板」「轉場太突然，鏡頭移動順一點」「音樂有點小聲」。用「當我說 X」比「大約 30 秒」準。

## 不收
- YouTube 轉 mp3 網站、myinstants 的音效：版權不清楚，商用片不能用。Pixabay 可以。
- Google Drive 的技能 zip：不是原作者 repo，來源無法驗證。
