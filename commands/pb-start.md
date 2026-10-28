---
description: 開一支新作品，從開案開始
argument-hint: "<名稱> <影片|口播|圖卡|縮圖|網頁>"
---

用 production-playbook 開一支新作品。參數：$ARGUMENTS（第一個是名稱，第二個是類型；缺類型就問我）。

執行 `python3 "$(cat ~/.config/production-playbook/home)/pb.py" start "<名稱>" --type <類型>`，然後照技能的格式回覆「現在／下一步／工具／注意／提升」五行，接著從 0.1 開始問我需要的資訊。
