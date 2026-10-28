# 工具總覽

> 由 `python3 pb.py build` 產生。依第一個階段分組；狀態：已整合、已安裝、待試、待查、未採用、避開。

## 1 研究與參考

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [yt-dlp](https://github.com/yt-dlp/yt-dlp)（T-34） | 已安裝 | 免費 | Unlicense（寬鬆） | 下載自己發佈過的影片做重剪，或下載參考影片做分析（別人的影片不放進成品） |
| [faster-whisper／mlx-whisper](https://github.com/SYSTRAN/faster-whisper)（T-56） | 已安裝 | 免費 | MIT（寬鬆） | 語音轉文字和逐字時間；Mac 用 mlx-whisper 較快 |
| [awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos)（T-22） | 待試 | 免費 | MIT（寬鬆） | 開新系列前找靈感、學提示詞寫法 |
| [claude-real-video（crv）](https://github.com/HUANGCHIHHUNGLeo/claude-real-video)（T-37） | 待試 | 免費 | MIT（寬鬆） | 拆解參考片或回頭檢查自己的成品：依場景挑關鍵畫面、縮圖表、逐字稿 |
| [MotionClone](https://github.com/blixvip/MotionClone)（T-23） | 未採用 | 免費 | 未標（未標） | 想把參考影片重建成可編輯的 HyperFrames 專案（沒有授權，只參考概念） |

## 2 腳本

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [Faceless Video Studio](https://github.com/cybiqon-ai/faceless-video-studio)（T-45） | 待試 | 免費 | MIT（寬鬆） | 想參考一整套自動化關卡：配音前腳本關卡、第二意見、混音與滿版檢查 |
| [Vyral content-skills](https://github.com/vyralcontent/content-skills)（T-39） | 未採用 | 免費 | MIT（寬鬆） | 找短影音鉤子和腳本的寫法（鉤子三層：畫面、口白、字卡） |
| [digital-marketing-pro：video-script](https://github.com/indranilbanerjee/digital-marketing-pro)（T-40） | 未採用 | 免費 | MIT（寬鬆） | 需要含時間碼、畫面欄與聲音欄的腳本表格範本 |
| [ClipForge](https://github.com/xixihhhh/clipforge)（T-43） | 未採用 | 免費 | AGPL-3.0（本機限定） | 實體商品的帶貨短片：商品圖 → 腳本 → 畫面、配音、字幕（AGPL，只在本機用） |
| [YouMind 影片腳本](https://youmind.com/zh-TW/video-script)（T-44） | 未採用 | 不明 | 商業服務（未標） | 雲端寫腳本、從網頁或影片抽逐字稿（素材要上傳，資料用途沒說明） |

## 3 分鏡與規格

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft)（T-20） | 已整合 | 部分付費 | Apache-2.0（寬鬆） | 找鏡頭和動效的說法：124 張鏡頭配方卡和動態樣片 |
| [lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar)（T-21） | 已整合 | 免費 | MIT（寬鬆） | 需要現成的影片風格（59 種，含水彩、衛星簡報等）和它的風格提示詞 |
| [Motion Prompt](https://github.com/showheyohtaki/motion-prompt)（T-36） | 已整合 | 免費 | MIT（寬鬆） | 指定和移植動效：168 個有編號的動作，附規格和 Canvas 程式；photo 包只當生圖用語 |
| [video-script-builder（SURGE）](https://github.com/erduo1998-cell/video-script-builder)（T-38） | 已整合 | 免費 | MIT（寬鬆） | 新格式或新風格開工前，先產一份分鏡規格當設計審查（意圖卡、母題、時間閉合、開放問題） |
| [onetake](https://github.com/feitangyuan/onetake)（T-42） | 未採用 | 不明 | 未標明（未標） | 一鏡到底的動態影片概念（授權不明，只參考） |

## 4 素材

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [auto-editor](https://github.com/WyattBlue/auto-editor)（T-01） | 已整合 | 免費 | Unlicense（寬鬆） | 口播粗剪第一步：依音量剪掉停頓和空白；故意留的停頓要先排除 |
| [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet)（T-09） | 已整合 | 免費 | MIT／Apache-2.0（寬鬆） | 視訊或手機錄音的底噪 |
| [Demucs](https://github.com/adefossez/demucs)（T-10） | 已整合 | 免費 | MIT（寬鬆） | 素材混著背景音樂時，抽出乾淨的人聲 |
| [Kokoro TTS](https://github.com/hexgrad/kokoro)（T-55） | 已整合 | 免費 | Apache-2.0（寬鬆） | 免費、本機、沒有額度限制的英文配音；每句分開生成，時間精準（數字要先拼成英文字） |
| [Pixabay（影片與照片）](https://pixabay.com/videos/)（T-57） | 已整合 | 免費 | Pixabay Content License（特殊） | 免費、可商用的實拍 B-roll；挑之前先看畫面，記下影片 ID |
| [Poly Haven](https://polyhaven.com)（T-58） | 已整合 | 免費 | CC0（寬鬆） | 3D 場景用的材質、HDRI 和模型 |
| [Kevin MacLeod（incompetech）](https://incompetech.com/music/)（T-59） | 已整合 | 免費 | CC BY 4.0（寬鬆） | 免費配樂；CC BY 4.0，說明欄一定要附標註 |
| [LosslessCut](https://github.com/mifi/lossless-cut)（T-02） | 已安裝 | 免費 | GPL-2.0（本機限定） | 手動挑素材、切長錄影，不重新編碼 |
| [resemble-enhance](https://github.com/resemble-ai/resemble-enhance)（T-11） | 待試 | 免費 | MIT（寬鬆） | 降噪後音質還是很差，需要增強時 |
| [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio)（T-12） | 待試 | 免費 | Apache-2.0（寬鬆） | 多人對談只要抽出其中一位講者時 |
| [Pocket TTS（Kyutai）](https://github.com/kyutai-labs/pocket-tts)（T-46） | 待試 | 免費 | MIT（程式）；模型權重 CC BY 4.0（寬鬆） | 需要複製真人聲音、或要比 Kokoro 更自然的英文配音時；權重 CC BY 4.0 要標註 |
| [video2x](https://github.com/k4yt3x/video2x)（T-16） | 未採用 | 免費 | AGPL-3.0（本機限定） | 素材畫質太低、需要 AI 放大或補幀時（只支援 Linux、Windows） |
| [FlashVSR](https://github.com/OpenImagingLab/FlashVSR)（T-17） | 未採用 | 免費 | Apache-2.0（寬鬆） | 有 NVIDIA GPU、需要即時超解析度時 |
| [FILM](https://github.com/google-research/frame-interpolation)（T-18） | 未採用 | 免費 | Apache-2.0（寬鬆） | 實拍素材需要補幀做慢動作時 |
| [OpenCreator（原 KrillinAI）](https://github.com/krillinai/OpenCreator)（T-26） | 未採用 | 付費 | Apache-2.0（寬鬆） | 需要影片翻譯和多語配音時（以 Codex 為引擎，要 OpenAI 付費帳號） |
| [ViMax](https://github.com/HKUDS/ViMax)（T-27） | 未採用 | 付費 | MIT（寬鬆） | 劇情片：導演、編劇到生成全包（要接付費的影片和語言模型 API） |
| [hypit](https://github.com/hypit-ai/hypit)（T-30） | 避開 | 不明 | 未明確（未標） | 換臉、換台詞複製別人的爆紅影片（肖像權和平台政策風險） |
| [Framesail](https://api.framesail.com/mcp)（T-47） | 避開 | 付費 | 商業服務（未標） | 長片 AI 生成、要處理角色一致性時（付費，價格未公開） |

## 5 製作

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill)（T-03） | 已整合 | 免費 | MIT（寬鬆） | 剪、接、轉檔、音量、平台規格檢查（check.py）、縮圖表（look.py） |
| [stable-ts](https://github.com/jianfch/stable-ts)（T-05） | 已整合 | 免費 | MIT（寬鬆） | 已經有定稿文字時，把文字強制對齊到聲音，產生逐字時間 |
| [rembg（U2-Net／BiRefNet）](https://github.com/danielgatis/rembg)（T-13） | 已整合 | 免費 | MIT（寬鬆） | 非 Mac 平台的去背；邊緣品質看模型 |
| [HyperFrames](https://github.com/heygen-com/hyperframes)（T-19） | 已整合 | 免費 | Apache-2.0（寬鬆） | 主要的影片引擎：用 HTML、CSS、GSAP 做畫面，逐格算成影片；snapshot 指令可以取任意時間點的定格 |
| [diagram-design](https://github.com/cathrynlavery/diagram-design)（T-31） | 已整合 | 免費 | MIT（圖示 Tabler MIT、Simple Icons CC0）（寬鬆） | 需要流程圖、架構圖、比較圖這類圖表（45 種，輸出 HTML＋SVG，可套品牌配色） |
| [taste-skill（design-taste-frontend）](https://github.com/Leonxlnx/taste-skill)（T-32） | 已整合 | 免費 | MIT（寬鬆） | 網頁的美術方向：抽選研究過的方向、用開放圖庫真圖、三種寬度檢查 |
| [Apple Vision 人物分割](https://developer.apple.com/documentation/vision/vngeneratepersonsegmentationrequest)（T-35） | 已整合 | 免費 | macOS 內建（寬鬆） | Mac 上的人物去背（預設）：免費、不用下載模型、邊緣細 |
| [kinocut](https://github.com/KyaniteLabs/kinocut)（T-04） | 未採用 | 免費 | Apache-2.0（寬鬆） | 想讓 agent 透過 MCP 做有護欄的剪輯時 |
| [WhisperX](https://github.com/m-bain/whisperX)（T-06） | 未採用 | 免費 | BSD-2-Clause（寬鬆） | 需要分辨多位講者或音素級對齊時 |
| [transcribe-anything](https://github.com/zackees/transcribe-anything)（T-07） | 未採用 | 免費 | MIT（寬鬆） | Mac M 晶片上想換一個多後端的轉錄工具時 |
| [auto-subtitle／subsai／Buzz](https://github.com/chidiwilliams/buzz)（T-08） | 未採用 | 免費 | MIT／GPL-3.0／MIT（寬鬆） | 只要現成的「產生並燒錄字幕」時 |
| [RobustVideoMatting](https://github.com/PeterL1n/RobustVideoMatting)（T-14） | 未採用 | 免費 | GPL-3.0（本機限定） | 影片去背、需要前後格穩定時；GPL 只在本機用 |
| [backgroundremover](https://github.com/nadermx/backgroundremover)（T-15） | 未採用 | 免費 | MIT（寬鬆） | 一行指令的簡單去背 |
| [Remotion](https://github.com/remotion-dev/remotion)（T-24） | 未採用 | 部分付費 | Remotion License（特殊） | 想用 React 寫影片時；超過 3 人的公司要付費 |
| [short-video-maker](https://github.com/gyoridavid/short-video-maker)（T-28） | 未採用 | 免費 | MIT（寬鬆） | 用 MCP 自動產生模板化短影音 |
| [landing-page-design（elayadesign）](https://github.com/elayadesign/ai-design-skills)（T-50） | 未採用 | 免費 | MIT（寬鬆） | 做落地頁時參考它的規則：間距階梯、巢狀圓角公式、動效曲線、元件狀態、上線清單（字體規則很主觀，不照單全收） |
| [design-to-motion（elayadesign）](https://github.com/elayadesign/ai-design-skills/tree/5e57840/skills/design-to-motion)（T-51） | 未採用 | 免費 | MIT（寬鬆） | 把靜態設計稿或截圖做成循環展示動畫（新 repo 尚未公開） |
| [OpenMontage](https://github.com/calesthio/OpenMontage)（T-29） | 避開 | 免費 | AGPL-3.0（本機限定） | 完整的 agent 影片製作框架；AGPL，只借點子 |
| [vox-director](https://github.com/Alisa0808/vox-director)（T-41） | 避開 | 付費 | MIT（寬鬆） | Vox 風格紙張拼貼解說片（核心步驟要付費 API） |

## 8 交付與發佈

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [yutu](https://github.com/eat-pray-ai/yutu)（T-25） | 已安裝 | 免費 | Apache-2.0（寬鬆） | 從命令列上傳 YouTube、改影片資訊和播放清單 |

## 協作

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [agency-agents（挑 3 個）](https://github.com/msitarzewski/agency-agents)（T-33） | 已整合 | 免費 | MIT（寬鬆） | 需要獨立審查員時：reality-checker（要證據才算完成）、evidence-collector、brand-guardian |
