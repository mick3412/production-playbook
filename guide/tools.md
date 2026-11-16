# 工具總覽

> 由 `python3 pb.py build` 產生。依第一個階段分組；狀態：已整合、已安裝、待試、待查、未採用、避開。

## 0 開案

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [Meetily](https://github.com/Zackriya-Solutions/meetily)（T-108） | 待試 | 免費 | MIT（寬鬆） | 客戶訪談、諮詢通話要留下逐字稿和重點，拿來做受眾研究時 |
| [anarlog（前身 Hyprnote）](https://github.com/fastrepl/anarlog)（T-109） | 待試 | 免費 | MIT（寬鬆） | 想要像 Granola 那樣邊開會邊記筆記、會後自動整理時 |

## 1 研究與參考

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [SenseVoice（SenseVoiceSmall）](https://github.com/QwenAudio/SenseVoice)（T-102） | 已安裝 | 免費 | MIT（寬鬆） | 中文為主的逐字稿：中、粵、英、日、韓；要快、要標出笑聲掌聲等聲音事件時。保留給多語自動辨識、情緒與聲音事件標籤；一定要配 fsmn-vad，否則遇停頓就截斷（P12） |
| [FunASR（modelscope）](https://github.com/modelscope/FunASR)（T-103） | 已安裝 | 免費 | MIT（寬鬆） | 中文逐字稿要一次做完語音偵測、加標點、講者分辨時。中文逐字稿預設（P12：字錯率 0.8%／12.6%，最快）；輸出簡體無標點，用 OpenCC 轉繁、標點另外處理；講者分辨用 T-95，不用 CAM++（要 1.1 GB 標點模型） |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp)（T-34） | 已安裝 | 免費 | Unlicense（寬鬆） | 下載自己發佈過的影片做重剪，或下載參考影片做分析（別人的影片不放進成品） |
| [faster-whisper／mlx-whisper](https://github.com/SYSTRAN/faster-whisper)（T-56） | 已安裝 | 免費 | MIT（寬鬆） | 語音轉文字和逐字時間；Mac 用 mlx-whisper 較快。要直接輸出繁體加標點時用（P12：字錯率 3.8%／13.4%，比 Paraformer 慢 4–6 倍） |
| [Scriberr](https://github.com/rishikanthc/Scriberr)（T-110） | 待試 | 免費 | MIT（寬鬆） | 要一個自架的網頁介面，批次上傳音檔轉錄時 |
| [awesome-opus5-5-videos](https://github.com/yihui-dev/awesome-opus5-5-videos)（T-22） | 待試 | 免費 | MIT（寬鬆） | 開新系列前找靈感、學提示詞寫法 |
| [claude-real-video（crv）](https://github.com/HUANGCHIHHUNGLeo/claude-real-video)（T-37） | 待試 | 免費 | MIT（寬鬆） | 拆解參考片或回頭檢查自己的成品：依場景挑關鍵畫面、縮圖表、逐字稿 |
| [動態參考圖庫（Prompt Motion、Eyecandy、24fps、Raivcoo、Motionographer、Motion Index）](https://learnaiwithmariah.com/guides/websites-to-give-ai-taste/)（T-72） | 待試 | 部分付費 | 各網站內容各自所有（未標） | 找動態、剪輯、運鏡參考時 |
| [youtube-agent-skill（11 個 YouTube 技能）](https://github.com/Jakeschincariol/youtube-agent-skill)（T-74） | 待試 | 免費 | MIT（寬鬆） | 寫 YouTube 腳本與開場、檢查標題縮圖、剪停頓清單、做章節、讀留存、切 Shorts、找同領域爆款時 |
| [pyannote-audio](https://github.com/pyannote/pyannote-audio)（T-107） | 待查 | 免費 | MIT（寬鬆） | 講者分辨要最準時；模型要 Hugging Face 帳號、同意條款與 token |
| [whisper-diarization](https://github.com/MahmoudAshraf97/whisper-diarization)（T-106） | 未採用 | 免費 | BSD-2-Clause（寬鬆） | 訪談或對談錄音要分出誰在說話時。P13：要裝整套 NeMo，sherpa-onnx（T-95）已夠 |
| [MotionClone](https://github.com/blixvip/MotionClone)（T-23） | 未採用 | 免費 | 未標（未標） | 想把參考影片重建成可編輯的 HyperFrames 專案（沒有授權，只參考概念） |

## 2 腳本

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [OpenWhispr](https://github.com/OpenWhispr/openwhispr)（T-100） | 待試 | 免費 | MIT（寬鬆） | 聽寫要能切換本機模型（Parakeet／Whisper）時；雲端模式要自己的金鑰，不用 |
| [Umless（jatinbishla）](https://github.com/jatinbishla/Umless)（T-98） | 待試 | 免費 | Apache-2.0（寬鬆） | 口述想法要直接變成乾淨文字時（寫腳本、交代 AI）；比一般聽寫多做去贅詞、自我更正、依 App 調語氣、個人詞庫 |
| [Handy（cjpais）](https://github.com/cjpais/Handy)（T-99） | 待試 | 免費 | MIT（寬鬆） | 要一個跨平台、離線、免費的按鍵聽寫 App 時 |
| [VoiceInk](https://github.com/Beingpax/VoiceInk)（T-101） | 未採用 | 免費 | GPL-3.0（特殊） | 只當參考：macOS 聽寫做法 |
| [Vyral content-skills](https://github.com/vyralcontent/content-skills)（T-39） | 未採用 | 免費 | MIT（寬鬆） | 找短影音鉤子和腳本的寫法（鉤子三層：畫面、口白、字卡） |
| [digital-marketing-pro：video-script](https://github.com/indranilbanerjee/digital-marketing-pro)（T-40） | 未採用 | 免費 | MIT（寬鬆） | 需要含時間碼、畫面欄與聲音欄的腳本表格範本 |
| [ClipForge](https://github.com/xixihhhh/clipforge)（T-43） | 未採用 | 免費 | AGPL-3.0（本機限定） | 實體商品的帶貨短片：商品圖 → 腳本 → 畫面、配音、字幕（AGPL，只在本機用） |
| [YouMind 影片腳本](https://youmind.com/zh-TW/video-script)（T-44） | 未採用 | 不明 | 商業服務（未標） | 雲端寫腳本、從網頁或影片抽逐字稿（素材要上傳，資料用途沒說明） |
| [Faceless Video Studio](https://github.com/cybiqon-ai/faceless-video-studio)（T-45） | 未採用 | 免費 | MIT（寬鬆） | 想參考一整套自動化關卡：配音前腳本關卡、第二意見、混音與滿版檢查 |

## 3 分鏡與規格

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft)（T-20） | 已整合 | 部分付費 | Apache-2.0（寬鬆） | 找鏡頭和動效的說法：124 張鏡頭配方卡和動態樣片 |
| [lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar)（T-21） | 已整合 | 免費 | MIT（寬鬆） | 需要現成的影片風格（59 種，含水彩、衛星簡報等）和它的風格提示詞 |
| [Motion Prompt](https://github.com/showheyohtaki/motion-prompt)（T-36） | 已整合 | 免費 | MIT（寬鬆） | 指定和移植動效：168 個有編號的動作，附規格和 Canvas 程式；photo 包只當生圖用語 |
| [video-script-builder（SURGE）](https://github.com/erduo1998-cell/video-script-builder)（T-38） | 已整合 | 免費 | MIT（寬鬆） | 新格式或新風格開工前，先產一份分鏡規格當設計審查（意圖卡、母題、時間閉合、開放問題） |
| [huashu-art-motion（畫術動態）](https://github.com/alchaincyf/huashu-art-motion)（T-120） | 已安裝 | 免費 | MIT（角色圖只供示範）（寬鬆） | 要做解說片、財經圖表、動態文字、白板等「語法」明確的程式動畫，或想照一套分鏡表→算圖→QA→交付紅綠燈的流程做時 |
| [onetake](https://github.com/feitangyuan/onetake)（T-42） | 未採用 | 不明 | 未標明（未標） | 一鏡到底的動態影片概念（授權不明，只參考） |

## 4 素材

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [auto-editor](https://github.com/WyattBlue/auto-editor)（T-01） | 已整合 | 免費 | Unlicense（寬鬆） | 口播粗剪第一步：依音量剪掉停頓和空白；故意留的停頓要先排除 |
| [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet)（T-09） | 已整合 | 免費 | MIT／Apache-2.0（寬鬆） | 視訊或手機錄音的底噪 |
| [Demucs](https://github.com/adefossez/demucs)（T-10） | 已整合 | 免費 | MIT（寬鬆） | 素材混著背景音樂時，抽出乾淨的人聲 |
| [Pixabay（影片與照片）](https://pixabay.com/videos/)（T-57） | 已整合 | 免費 | Pixabay Content License（特殊） | 免費、可商用的實拍 B-roll；挑之前先看畫面，記下影片 ID |
| [Poly Haven](https://polyhaven.com)（T-58） | 已整合 | 免費 | CC0（寬鬆） | 3D 場景用的材質、HDRI 和模型 |
| [Kevin MacLeod（incompetech）](https://incompetech.com/music/)（T-59） | 已整合 | 免費 | CC BY 4.0（寬鬆） | 免費配樂；CC BY 4.0，說明欄一定要附標註 |
| [LosslessCut](https://github.com/mifi/lossless-cut)（T-02） | 已安裝 | 免費 | GPL-2.0（本機限定） | 手動挑素材、切長錄影，不重新編碼 |
| [media-use（HyperFrames 技能）](https://github.com/heygen-com/hyperframes)（T-111） | 已安裝 | 免費 | Apache-2.0（寬鬆） | 影片需要配樂、音效或圖片時，先用它找可用的素材，再照 4.5 登記授權 |
| [FLUX.1-schnell 4-bit＋mflux](https://github.com/filipstrand/mflux)（T-112） | 已安裝 | 免費 | Apache-2.0（FLUX.1-schnell）（寬鬆） | 要快速出草稿、或畫浮世繪、80 年代合成波時；其他情況預設用 T-113 Z-Image |
| [Z-Image Turbo（通義，mflux 4-bit）](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)（T-113） | 已安裝 | 免費 | Apache-2.0（官方模型卡；衍生微調版另有授權）（寬鬆） | 本機生成圖的預設：插圖、風格試稿、背景、縮圖素材；要很快出草稿才改用 T-112 |
| [anidoodle](https://github.com/alexgreensh/anidoodle)（T-121） | 已安裝 | 免費 | Apache-2.0（寬鬆） | 要用程式畫插畫、循環動畫或配樂短片，又不想用生圖模型時 |
| [claude-drawing-skill](https://github.com/cloveric/claude-drawing-skill)（T-122） | 已安裝 | 免費 | MIT（寬鬆） | 要離線做水彩、浮世繪、彩繪玻璃、剪紙、Art Deco 等畫風的插圖，或 Z-Image 畫不準某種畫風時 |
| [javascript-animation-skills（含 sync-check）](https://github.com/iart-ai/javascript-animation-skills)（T-123） | 已安裝 | 免費 | MIT（寬鬆） | 要做 Canvas 逐格動畫＋程式合成配樂；或要量畫面切點和音效有沒有對上時 |
| [HandDraw-Skill](https://github.com/ToBeWin/HandDraw-Skill)（T-124） | 已安裝 | 免費 | MIT（底層 Remotion 另有授權）（特殊） | 要做白板手繪解說片（逐筆畫出 SVG＋字）時 |
| [manim-skill（Manim CE）](https://github.com/awesome-skills/manim-skill)（T-125） | 已安裝 | 免費 | MIT（寬鬆） | 要做數學、演算法、幾何變換的動畫（物件從一種形狀變成另一種）時 |
| [Kokoro TTS](https://github.com/hexgrad/kokoro)（T-55） | 已安裝 | 免費 | Apache-2.0（寬鬆） | 免費、本機、沒有額度限制的英文配音；每句分開生成，時間精準（數字要先拼成英文字）。預設英文配音（2026-11-12 比較定案：和 Pocket TTS 字錯率同為 0%，Kokoro 授權 Apache-2.0 免標註、聲音選擇多） |
| [parakeet-mlx](https://github.com/senstella/parakeet-mlx)（T-104） | 待試 | 免費 | Apache-2.0（寬鬆） | 英文或歐洲語言的逐字稿要在 Apple Silicon 上跑得很快時 |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp)（T-105） | 待試 | 免費 | MIT（寬鬆） | 不想裝 Python、要在命令列或其他程式裡直接跑 Whisper 時 |
| [Wan2.2 TI2V-5B](https://github.com/Wan-Video/Wan2.2)（T-114） | 待試 | 免費 | Apache-2.0（寬鬆） | 需要本機免費生成短片（抽象背景、氛圍空鏡）時；ITA Reels 規定用真實照片，不適用 |
| [Qwen-Image／Qwen-Image-Edit](https://github.com/QwenLM/Qwen-Image)（T-115） | 待試 | 免費 | Apache-2.0（寬鬆） | 生成圖裡要有準確的中文字、或要用文字指令修圖時 |
| [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio)（T-12） | 待試 | 免費 | Apache-2.0（寬鬆） | 多人錄音要抽出單一講者的聲音時（降噪本身用 DeepFilterNet） |
| [Affinity（Canva 版，Mac／Windows／iPad）](https://www.affinity.studio/)（T-127） | 待試 | 部分付費 | Affinity 條款（2026-03-12 版）：內容歸使用者，未見商用限制；內附素材依 Canva 免費內容授權（特殊） | 要做向量、版面、修圖，又不想付 Adobe 時 |
| [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5)（T-60） | 待試 | 免費 | MIT（寬鬆） | 需要長度剛好的配樂、又不想付費或擔心 Content ID 時 |
| [Stable Audio 3（Small／Medium）](https://stability.ai/)（T-61） | 待試 | 免費 | Stability 社群授權（年營收 100 萬美元以下可商用）（特殊） | 要快、長度要準的純音樂 |
| [Openverse 音訊搜尋](https://api.openverse.org/v1/audio/)（T-65） | 待試 | 免費 | 各檔不同（篩 CC0、CC BY）（寬鬆） | 要找音效或配樂時先用它 |
| [Pixel2Motion](https://github.com/nolangz/pixel2motion)（T-83） | 待試 | 免費 | MIT（寬鬆） | 要把點陣圖 logo 做成片頭或網頁的 logo 動畫時 |
| [story-to-handdrawn-video](https://github.com/gnipbao/story-to-handdrawn-video)（T-84） | 待試 | 免費 | MIT（底層 Remotion 另有授權）（特殊） | 要把中文故事或一組圖片做成手繪日記漫畫風的直式動畫時 |
| [banana-claude](https://github.com/AgriciDaniel/banana-claude)（T-88） | 待試 | 部分付費 | MIT（寬鬆） | 要用 Gemini 生圖並由 agent 當創意總監時 |
| [Kolors（快手可圖）](https://github.com/Kwai-Kolors/Kolors)（T-118） | 待查 | 免費 | Kolors 授權：學術免費，商用要先登記（特殊） | 要生成中式題材的圖、且 Z-Image 不夠時 |
| [混元生圖（騰訊雲 API）](https://cloud.tencent.com/document/product/1616/118994)（T-119） | 待查 | 部分付費 | 騰訊雲服務條款；開放權重版為騰訊混元社群授權（不適用歐盟、英國、南韓）（特殊） | 要用 API 生圖、又想先用首次免費額度試時 |
| [Beeble](https://beeble.ai)（T-96） | 待查 | 不明 | 商業服務（特殊） | 想把實拍場景換成另一個空間並重新打光時 |
| [Adobe Podcast（Enhance Speech）](https://podcast.adobe.com/enhance)（T-97） | 待查 | 部分付費 | 商業服務（特殊） | 人聲錄音很差、DeepFilterNet 救不回來時 |
| [resemble-enhance](https://github.com/resemble-ai/resemble-enhance)（T-11） | 未採用 | 免費 | MIT（寬鬆） | 降噪後音質還是很差，需要增強時 |
| [Stable Diffusion 3.5（Stability AI）](https://stability.ai/license)（T-116） | 未採用 | 部分付費 | Stability 社群授權（整個組織年營收 100 萬美元以下可商用）（特殊） | 要用 Stability 的模型時 |
| [HiDream-I1](https://github.com/HiDream-ai/HiDream-I1)（T-117） | 未採用 | 免費 | MIT（權重）；管線另用 Llama 3.1（Llama 授權）與 T5（特殊） | — |
| [motion-skill（復古剪貼報動畫）](https://github.com/LunaAI519/motion-skill)（T-128） | 未採用 | 付費 | MIT（寬鬆） | — |
| [video2x](https://github.com/k4yt3x/video2x)（T-16） | 未採用 | 免費 | AGPL-3.0（本機限定） | 素材畫質太低、需要 AI 放大或補幀時（只支援 Linux、Windows） |
| [FlashVSR](https://github.com/OpenImagingLab/FlashVSR)（T-17） | 未採用 | 免費 | Apache-2.0（寬鬆） | 有 NVIDIA GPU、需要即時超解析度時 |
| [FILM](https://github.com/google-research/frame-interpolation)（T-18） | 未採用 | 免費 | Apache-2.0（寬鬆） | 實拍素材需要補幀做慢動作時 |
| [OpenCreator（原 KrillinAI）](https://github.com/krillinai/OpenCreator)（T-26） | 未採用 | 付費 | Apache-2.0（寬鬆） | 需要影片翻譯和多語配音時（以 Codex 為引擎，要 OpenAI 付費帳號） |
| [ViMax](https://github.com/HKUDS/ViMax)（T-27） | 未採用 | 付費 | MIT（寬鬆） | 劇情片：導演、編劇到生成全包（要接付費的影片和語言模型 API） |
| [Pocket TTS（Kyutai）](https://github.com/kyutai-labs/pocket-tts)（T-46） | 未採用 | 免費 | MIT（程式）；模型權重 CC BY 4.0（寬鬆） | 需要複製真人聲音、或要比 Kokoro 更自然的英文配音時；權重 CC BY 4.0 要標註。比較後預設改用 T-55 Kokoro；只有要複製真人聲音時再開（聲音複製模型要在 Hugging Face 同意條款，權重 CC BY 4.0 要標註） |
| [Mureka](https://www.mureka.ai/)（T-62） | 未採用 | 付費 | 商用授權（付費）（未標） | 要中文歌、歌詞要唱清楚時 |
| [ElevenLabs Music v2.5](https://elevenlabs.io/music)（T-63） | 未採用 | 付費 | 商用授權（付費）（未標） | 要最快、長度準的配樂且有預算 |
| [earshot](https://github.com/Leonxlnx/earshot)（T-67） | 未採用 | 免費 | MIT（寬鬆） | Openverse 找不到想要的聲音、或要一整組風格統一的介面音效時。進階功能要下載約 1.1 GB 模型，超過 1 GB 上限 |
| [Higgsfield Genjutsu](https://higgsfield.ai/)（T-70） | 未採用 | 付費 | 商用條款依方案（未標） | 要做動作轉移、換掉畫面裡的物件時 |
| [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo)（T-76） | 未採用 | 免費 | MIT（寬鬆） | 要從主題快速做出一支素材拼接短片的初稿時 |
| [VoiceStudio](https://github.com/debpalash/VoiceStudio)（T-77） | 未採用 | 免費 | AGPL-3.0（另有商業授權）（本機限定） | 要在本機免費配音或複製聲音時 |
| [Cap](https://github.com/CapSoftware/Cap)（T-78） | 未採用 | 部分付費 | AGPL-3.0（部分 crate 為 MIT）（本機限定） | 錄螢幕操作、做產品示範或教學片時（Loom 類） |
| [ArtCraft](https://github.com/storytold/artcraft)（T-80） | 未採用 | 付費 | Apache-2.0（寬鬆） | — |
| [Open Generative AI](https://github.com/Anil-matcha/Open-Generative-AI)（T-81） | 未採用 | 付費 | MIT（寬鬆） | — |
| [Archify](https://github.com/tt-a1i/archify)（T-85） | 未採用 | 免費 | Apache-2.0（寬鬆） | 要把想法、計畫或流程做成互動式圖表時。它畫的是程式架構圖，不是影片圖解；已轉給開發手冊收件匣 |
| [拍片哥服裝與姿勢參考庫（nvzhuang、ai-pose-gallery、omilic.com）](https://github.com/paipiange/nvzhuang)（T-86） | 未採用 | 免費 | MIT（模特庫 CC0；圖片為 AI 生成）（寬鬆） | 要生成人物角色，需要服裝、姿勢參考或中英提示詞時 |
| [GPT Image（OpenAI）](https://platform.openai.com/docs/guides/images)（T-91） | 未採用 | 付費 | 商業服務（特殊） | 生成圖片素材時 |
| [ElevenLabs 語音合成（TTS）](https://elevenlabs.io)（T-93） | 未採用 | 部分付費 | 商業服務（特殊） | 需要 AI 配音時 |
| [hypit](https://github.com/hypit-ai/hypit)（T-30） | 避開 | 不明 | 未明確（未標） | 換臉、換台詞複製別人的爆紅影片（肖像權和平台政策風險） |
| [Framesail](https://api.framesail.com/mcp)（T-47） | 避開 | 付費 | 商業服務（未標） | 長片 AI 生成、要處理角色一致性時（付費，價格未公開） |
| [Suno 免費版](https://suno.com/)（T-64） | 避開 | 部分付費 | 免費版禁止商用（未標） | — |

## 5 製作

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill)（T-03） | 已整合 | 免費 | MIT（寬鬆） | 剪、接、轉檔、音量、平台規格檢查（check.py）、縮圖表（look.py） |
| [stable-ts](https://github.com/jianfch/stable-ts)（T-05） | 已整合 | 免費 | MIT（寬鬆） | 已經有定稿文字時，把文字強制對齊到聲音，產生逐字時間 |
| [rembg（U2-Net／BiRefNet）](https://github.com/danielgatis/rembg)（T-13） | 已整合 | 免費 | MIT（寬鬆） | 非 Mac 平台的去背；邊緣品質看模型 |
| [HyperFrames](https://github.com/heygen-com/hyperframes)（T-19） | 已整合 | 免費 | Apache-2.0（寬鬆） | 主要的影片引擎：用 HTML、CSS、GSAP 做畫面，逐格算成影片；snapshot 指令可以取任意時間點的定格。同一套生態的技能：hyperframes-cli 管指令操作（建專案、預覽、算圖）；hyperframes-registry 有約 450 個現成轉場和字卡，第 5 階段先從這裡挑，不從零寫 |
| [diagram-design](https://github.com/cathrynlavery/diagram-design)（T-31） | 已整合 | 免費 | MIT（圖示 Tabler MIT、Simple Icons CC0）（寬鬆） | 需要流程圖、架構圖、比較圖這類圖表（45 種，輸出 HTML＋SVG，可套品牌配色） |
| [taste-skill（design-taste-frontend）](https://github.com/Leonxlnx/taste-skill)（T-32） | 已整合 | 免費 | MIT（寬鬆） | 網頁的美術方向：抽選研究過的方向、用開放圖庫真圖、三種寬度檢查 |
| [Apple Vision 人物分割](https://developer.apple.com/documentation/vision/vngeneratepersonsegmentationrequest)（T-35） | 已整合 | 免費 | macOS 內建（寬鬆） | Mac 上的人物去背（預設）：免費、不用下載模型、邊緣細 |
| [GSAP AI Skills（官方）](https://github.com/greensock/gsap-skills)（T-82） | 已安裝 | 免費 | MIT（GSAP 本身含全部外掛免費）（寬鬆） | 在 HyperFrames（底層是 GSAP）裡寫時間軸、文字拆分、SVG 變形動效時 |
| [emilkowalski/skills（animate、choreograph 等）](https://github.com/emilkowalski/skills)（T-90） | 已安裝 | 免費 | MIT（寬鬆） | 做 HTML 動效（HyperFrames）要選曲線、時長、編排時 |
| [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx)（T-95） | 已安裝 | 免費 | Apache-2.0（寬鬆） | 需要本機離線語音辨識和逐字時間戳時。講者分辨預設（P13：pyannote-segmentation-3.0＋3D-Speaker，46 MB，兩人對談正確率 92.7%、自動判斷講者數） |
| [Instagram Edits（Mac 版）](https://apps.apple.com/app/edits-an-instagram-app/id6738967378)（T-126） | 待試 | 免費 | Meta 服務條款（特殊） | 要在 Mac 上剪 Reels、直接發佈或發試用 Reels 時 |
| [Anatomy（wheresryan22）](https://github.com/wheresryan22/anatomy)（T-129） | 待試 | 免費 | MIT（寬鬆） | 要解釋「一個東西怎麼運作」（產品結構、流程裡的機關、系統元件）時，畫成可互動的立體剖面圖 |
| [Remotion](https://github.com/remotion-dev/remotion)（T-24） | 待試 | 免費 | Remotion License（特殊） | 想用 React 寫影片時；超過 3 人的公司要付費 |
| [FunClip](https://github.com/modelscope/FunClip)（T-87） | 待試 | 免費 | MIT（寬鬆） | 要從長片轉字幕、讓 LLM 挑片段剪成短片時 |
| [kinocut](https://github.com/KyaniteLabs/kinocut)（T-04） | 未採用 | 免費 | Apache-2.0（寬鬆） | 想讓 agent 透過 MCP 做有護欄的剪輯時 |
| [WhisperX](https://github.com/m-bain/whisperX)（T-06） | 未採用 | 免費 | BSD-2-Clause（寬鬆） | 需要分辨多位講者或音素級對齊時。2026-11-12 重評：講者分辨要用 pyannote，同樣卡在 Hugging Face 帳號；改用 T-106 或 T-103 |
| [transcribe-anything](https://github.com/zackees/transcribe-anything)（T-07） | 未採用 | 免費 | MIT（寬鬆） | Mac M 晶片上想換一個多後端的轉錄工具時 |
| [auto-subtitle／subsai／Buzz](https://github.com/chidiwilliams/buzz)（T-08） | 未採用 | 免費 | MIT／GPL-3.0／MIT（寬鬆） | 只要現成的「產生並燒錄字幕」時 |
| [RobustVideoMatting](https://github.com/PeterL1n/RobustVideoMatting)（T-14） | 未採用 | 免費 | GPL-3.0（本機限定） | 影片去背、需要前後格穩定時；GPL 只在本機用 |
| [backgroundremover](https://github.com/nadermx/backgroundremover)（T-15） | 未採用 | 免費 | MIT（寬鬆） | 一行指令的簡單去背 |
| [short-video-maker](https://github.com/gyoridavid/short-video-maker)（T-28） | 未採用 | 免費 | MIT（寬鬆） | 用 MCP 自動產生模板化短影音 |
| [landing-page-design（elayadesign）](https://github.com/elayadesign/ai-design-skills)（T-50） | 未採用 | 免費 | MIT（寬鬆） | 做落地頁時參考它的規則：間距階梯、巢狀圓角公式、動效曲線、元件狀態、上線清單（字體規則很主觀，不照單全收） |
| [design-to-motion（elayadesign）](https://github.com/elayadesign/ai-design-skills/tree/5e57840/skills/design-to-motion)（T-51） | 未採用 | 免費 | MIT（寬鬆） | 把靜態設計稿或截圖做成循環展示動畫（新 repo 尚未公開） |
| [Motion Design 技能（LottieFiles）](https://github.com/LottieFiles/motion-design-skill)（T-68） | 未採用 | 免費 | MIT（寬鬆） | 要設計動效的時間、緩動、編排時 |
| [remotion-reel 技能（Michael Ly）](https://milleemd.com/guides/claude-x-remotion/)（T-71） | 未採用 | 免費 | 未標（未標） | — |
| [WAI 自動剪輯技能（理工威森）](https://wilson-men.tw/ai-auto-edit/)（T-73） | 未採用 | 免費 | 未標（未標） | 要在口播片上疊人後大字、玻璃卡、音效時 |
| [FilmCraft](https://github.com/storytold/filmcraft)（T-75） | 未採用 | 免費 | MIT 或 Apache 2.0（寬鬆） | 需要免費的時間軸剪輯軟體（Premiere 類）時 |
| [Concat](https://github.com/jub0t/Concat)（T-79） | 未採用 | 免費 | AGPL-3.0（只當桌面剪輯軟體使用，不修改、不散布，無額外義務）（特殊） | 需要免費的 CapCut 類剪輯軟體時 |
| [video-autopilot-kit（Hao0321）](https://github.com/Hao0321/video-autopilot-kit)（T-89） | 未採用 | 免費 | MIT（寬鬆） | 想參考短影音自動化流程（CapCut JSON、ffmpeg）時 |
| [Ultra Skills Edit Engine](https://www.ultra-skills.com)（T-92） | 未採用 | 付費 | 商業服務（特殊） | 想要現成的 AI 剪片流程與動畫效果時 |
| [OpenMontage](https://github.com/calesthio/OpenMontage)（T-29） | 避開 | 免費 | AGPL-3.0（本機限定） | 完整的 agent 影片製作框架；AGPL，只借點子 |
| [vox-director](https://github.com/Alisa0808/vox-director)（T-41） | 避開 | 付費 | MIT（寬鬆） | Vox 風格紙張拼貼解說片（核心步驟要付費 API） |

## 6 審片

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [design-motion-principles（kylezantos）](https://github.com/kylezantos/design-motion-principles)（T-69） | 未採用 | 免費 | MIT（寬鬆） | 要審查既有動畫時 |

## 7 算圖與混音

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [Real SFX（Clipwing）](https://github.com/Clipwing/skills)（T-66） | 待試 | 免費 | MIT（腳本）；內附 78 個 UI 音效為 CC0；自己的音效庫依各自授權（寬鬆） | 音效庫準備好、要把音效對到畫面時 |
| [SFX Kit（wyzowl）](https://github.com/wyzowl/sfx-kit)（T-94） | 待試 | 免費 | CC0-1.0（寬鬆） | 需要基本音效庫並讓 AI 自己選、對齊、混音時 |

## 8 交付與發佈

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [yutu](https://github.com/eat-pray-ai/yutu)（T-25） | 已安裝 | 免費 | Apache-2.0（寬鬆） | 從命令列上傳 YouTube、改影片資訊和播放清單 |

## 協作

| 工具 | 狀態 | 費用 | 授權 | 何時用 |
|---|---|---|---|---|
| [agency-agents（挑 3 個）](https://github.com/msitarzewski/agency-agents)（T-33） | 已整合 | 免費 | MIT（寬鬆） | 需要獨立審查員時：reality-checker（要證據才算完成）、evidence-collector、brand-guardian |
