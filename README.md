# 智慧專題創作平台 v4 ｜ 心智圖 → IPO → Python → PPT → 影片

線上網址：https://pjkuo.github.io/AI-empower-platform/?sid=學號&cls=班級
（由 AI 賦能 Hub 連結進入會自動帶入身分）

單一檔案 `index.html`，零後端；學生一路操作就能產出**真正的作品**：心智圖 PNG、IPO 表（xlsx/md）、可執行的 Python、執行結果與圖表、14 頁 PPTX、30 秒影片（webm）＋字幕，最後一鍵打包 ZIP。

## v4 新增（2026-08-29）

| 步驟 | 新功能 |
|---|---|
| 共同 | `?sid=&cls=` 共同身分（與 Hub 相同的 `ae.identity.v1`）；載入 Hub `bridge.js`，每步完成自動回報雲端；側邊欄「成果總覽」 |
| AI | **老師代管模式**：金鑰放在 Apps Script（`gas/ai-proxy.gs`），學生只輸入班級碼；另有自備金鑰、**離線規則引擎**三種模式。所有 AI 功能在無 AI 時自動退回離線引擎，流程永遠走得完 |
| ① 心智圖 | 🪄 一鍵生成（AI 回 JSON／離線依 11 個領域字典）；Canvas 自動繪成心智圖 PNG（進簡報與影片） |
| ② IPO | ✨ 自動補充說明（來源／方法／呈現） |
| ③ Python | 模板改為**可直接執行**：模擬資料、清洗、統計、t 檢定、蒙地卡羅、迴歸、分級、門檻、排序，OUTPUT 以 `emit_chart()` 交給 Chart.js 畫圖（支援中文）；▶ **在瀏覽器執行（Pyodide）**，stdout 與圖表存入專題 |
| ④ PPT | 新增心智圖圖片頁、執行結果頁、每張成果圖表頁、影片分鏡頁；封面／結尾帶學號班級 |
| ⑤ 影片 | 腳本／旁白／字幕可離線生成；🎞 **瀏覽器內直接錄成 .webm**（Canvas 四幕動畫＋燒錄字幕＋合成背景音樂，可選麥克風照提詞機錄旁白）；▶ TTS 預覽；已修補 webm 時長中繼資料 |
| 打包 | ZIP 依 01_心智圖／02_IPO／03_程式／04_簡報／05_影片 分資料夾 |
| 全流程 | 🚀 一鍵示範全流程：心智圖→IPO→程式→執行→大綱→腳本 自動走完 |

## 老師部署 AI 代管（5 分鐘）

1. https://script.google.com 新增專案，貼上 `gas/ai-proxy.gs`。
2. 指令碼屬性：`GEMINI_API_KEY`、`CLASS_CODES=MIS2026`（逗號分隔多班）、`DAILY_LIMIT=60`（選填）。
3. 部署 → 網頁應用程式 → 執行身分「我」、存取「所有人」→ 複製 `/exec` 網址。
4. 貼到 `index.html` 的 `AI_PROXY_URL_DEFAULT`（學生只需輸入班級碼），或讓學生在「設定 AI」自行貼上。
5. 用量自動記錄到雲端硬碟試算表「智慧專題平台 AI 用量」；`?action=usage&code=MIS2026` 可查今日用量。

## 學生操作流程

進入平台 → 填專題名稱 → 🪄 一鍵生成心智圖（或 🚀 一鍵示範全流程）→ 儲存進 IPO → ✨ 自動補充說明 → 生成程式 → ▶ 在瀏覽器執行 → 生成並下載 PPTX → 生成影音腳本 → 🎞 製作影片 → 🎉 打包下載 → 截圖上傳 Moodle。

## 驗證

`tests/simulate_student_flow.py`（Playwright）以學生身分 `sid=6010&cls=MIS` 無 AI、無人工介入走完全流程，實際產出 15 個檔案並逐一驗證（python-pptx 讀 14 頁、openpyxl 讀 16 列、ffprobe 讀出 30.0 秒 VP9+Opus、下載的 .py 在本機 Python 3.11 可執行）。結果見 `docs/驗證報告-v4.md`、`docs/驗證截圖/`。

## 相依（CDN）

pptxgenjs、xlsx、jszip、jspdf、html2canvas、docx、qrcode、mermaid、chart.js、Pyodide 0.26.4（首次執行 Python 約 10–20 秒下載）。離線環境時除「瀏覽器執行」外其餘功能皆可用。

---
（v3 以前：教學中心、學習後測問卷 40 題、多專題管理、學習儀表板等功能保留不變。）
