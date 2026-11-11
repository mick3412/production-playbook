# 桌上試驗樣本包

`pb.py bench` 排出的待試項目用這裡的樣本測，結果用 `pb.py run-log --bench` 記進 `data/runs.csv`。樣本和輸出不進 git（見 `.gitignore`），這份說明記來源，換電腦時照著重建。

| 樣本 | 內容 | 來源 |
|---|---|---|
| `samples/motion_55s.mp4` | 55 秒直式動態圖文（色塊轉場、大字、照片），7 個轉場事件 | 過去作品的 HyperFrames 試驗輸出 |
| `samples/broll_19s.mp4` | 19 秒 2560×1440 實拍 B-roll | Pixabay 免費素材快取 |
| `samples/voice_clean_17s.wav` | 17 秒乾淨配音 | 過去作品的 TTS 快取 |

缺：真人口播（30 秒、腳架、胸上）。測去背、字幕對齊和人聲增強時需要，請負責人提供一段可公開的片子。

外部套件和資料放 `vendor/`（例如 `vendor/sfx-kit`），只在這台機器上。
