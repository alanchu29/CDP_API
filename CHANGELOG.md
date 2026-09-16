# Changelog

## 2.2.0 — 2026-09-16

表格檢視改為以 SN 為主的固定版面，並補上查詢筆數限制。

### 表格

- **固定預設欄位與順序**：`SN` · `PN` · `PN_Type` · `SI_Factory` · `Hwkey_Download_Status` · `GPkey_Download_Status` · `Hwkey_Download_LocalTime` · `GPkey_Download_Time`。SN 一律排在第一欄。
- 先前是照 API 回傳順序排列、僅依值長度決定隱藏，結果 SN 被埋在中間、畫面雜亂。其餘 14 個欄位改為預設隱藏，仍可從「欄位」選單開啟。
- 若某個 `TYPE` 回傳的結構完全不含上述欄位，會退回原本的長度啟發式，避免表格開起來一片空白。

### 待處理佇列

- 未指定 SN 的查詢會在表格上方顯示專屬面板：**SN 數**與**記錄數**，加上完整 SN 清單與「複製 SN 清單」按鈕。這類查詢要的答案是「有幾筆、是哪些序號」，不是欄位細節。

### 查詢筆數限制

- 新增 **Row Limit** 欄位，對應規格的 `ROW_LIMIT` 參數。
- 填入後會就地顯示提醒：PRD 於 2026-09-16 實測尚未部署此參數，送出可能不生效。

### 修正

- **補回 `WYMUS` 與 `WYLZ` 兩個廠區。** 改寫時的基準版本是 `a73032b`，早於 `17f9f31`（新增 WYMUS）與 `e17d096`（新增 WYLZ），這兩個 commit 是後來 merge 進來的，導致新前端只帶了原本的四個廠區。

---

## 2.1.0 — 2026-09-16

取得官方規格 **Cerberus_API_spec v4.3.0 (2026-09-14)** 後，依規格修正實作並重寫 API 文件。

### 修正

- **`SITE` 改為選填。** 規格中 `TYPE` 是唯一必填欄位，省略 `SITE` 代表不限廠區，是規格明列的查詢模式。先前 proxy 同時擋下兩者，等於砍掉了一種官方支援的用法。前端新增「（不限廠區）」選項。
- **新增 `c41ae` 機種**（規格 v4.2.2 加入，先前遺漏）。
- **新增 1000 筆截斷警示。** 帶 `all` 參數且未指定 `ROW_LIMIT` 時，上游會把結果截在 1000 筆且不給任何提示。現在筆數剛好等於上限時會在畫面顯示警告。

### 新增

- **支援 `ROW_LIMIT`**（規格 v4.3.0）。但實測 PRD 尚未部署此欄位，目前送出無效果 —— 詳見 [docs/API.md](docs/API.md)。
- payload 建構改為省略空值 key，符合規格「任何欄位都不接受 JSON `null`」的要求。

### 文件

- [docs/API.md](docs/API.md) 依規格重寫，先前標為「未確認」的項目全部補齊：`Hwkey_Download_Status` 狀態碼（5/6/8/99/999）、`Download_Time` 為 UTC 而 `LocalTime` 為當地時間、`TYPE` → `PN_Type` 對照表、100 MB 上限、錯誤碼。
- 釐清 `HwkeyDownloadStatus` / `GPkeyDownloadStatus` 的語意：不帶只回「尚未下載金鑰」的待處理佇列，帶 `=all` 才回全部。這解答了先前「未指定 SN 時回傳不固定」的疑問 —— 佇列本來就會隨產線處理而變動。
- 記錄兩處規格與實測不符：PRD 忽略 `ROW_LIMIT`；`M1120_LION` / `M1120_BMC` 的 `Public_key` 規格稱為 null 但實際有值。
- 記錄另外三支會寫入資料庫的 API（`update_hwkey`、`update_gpkey`、`update_hwkey_with_action`），本工具刻意不實作。

---

## 2.0.0 — 2026-09-16

從 Streamlit 改寫為靜態前端 + serverless proxy，改以 Vercel 部署。

### 架構

- **移除 Streamlit。** 前端改為單一 `index.html`，無框架、無建置步驟、無 runtime 依賴。
- **新增 `api/query.js`** —— serverless proxy。上游 API 不回傳 CORS 標頭，瀏覽器無法直接呼叫，因此必須由伺服器端代發。
- **部署改為 `git push` 自動觸發**（Vercel），不再需要手動啟動 Streamlit 行程。
- `query_api.py` 與 `requirements.txt` 保留但停止維護。

### 送往上游的請求

與舊版**實質相同** —— 相同的 URL、method、payload 結構，以及「僅在帶 SN 時附上 `HwkeyDownloadStatus` / `GPkeyDownloadStatus`」的條件邏輯。差異僅有：

- 新增 `Accept: application/json` 標頭
- 逾時 15 秒 → 55 秒（容納批次查詢）
- SN 送出前會去重（舊版會把重複的序號原樣送出）

回傳資料**不經任何修改、過濾或改名**，僅在外層包上 `{ records, elapsedMs, empty }`。

### 修正

- **查詢失敗時不再留著上一次的成功結果。** 舊版只顯示錯誤訊息，畫面上仍是舊資料，容易誤判。
- **空回應不再被誤報為連線錯誤。** 上游查無資料時回 200 搭配完全空白的 body，舊版 `response.json()` 會拋出 `JSONDecodeError`，再被寬泛的 `except Exception` 吞掉，顯示成「連線錯誤」。
- **記錄數說明改為正確。** 一組 SN 會對應多筆金鑰記錄（`m1120` 為三筆），舊版的「Found N record(s)」會讓人誤以為查到 N 塊板子。現在分開顯示「N 筆記錄 / M 個 SN」。
- **移除假的健康狀態。** 舊版側欄無條件顯示「API Gateway: Online」，從未實際探測；`Last updated` 顯示的是 `datetime.now()`，永遠是當天。兩者都已移除。
- **移除硬編碼的真實序號。** 舊版把一組正式 SN 寫死為輸入框預設值。
- **錯誤訊息分類。** 現在會區分 proxy 連線失敗、上游非 200、查無資料，而非一律歸為「連線錯誤」。

### 介面

針對批次查詢重新設計：

- 表格檢視，可排序、跨欄位即時篩選、自由開關欄位
- 憑證類長欄位依值長度自動預設隱藏（動態判斷，可適應未實測的 `TYPE`）
- 點列展開記錄明細，各欄位可獨立複製
- 匯出 CSV（含 BOM，Excel 可正確讀取 UTF-8）
- JSON 檢視與複製（沿用舊版功能）
- SN 支援換行 / 逗號 / 空白混合分隔、自動去重、即時顯示組數
- <kbd>Ctrl</kbd>+<kbd>Enter</kbd> 送出
- SITE / TYPE / ENV 記憶於 localStorage

樣式不再依賴任何框架產生的 DOM。舊版有 276 行 `!important` 綁在 Streamlit 內部選擇器（`data-baseweb`、`react-json-view`）上，框架升級即會失效。

### 安全性

- `api/query.js` 對 `env` 設白名單，防止經由 URL 路徑注入的 SSRF。
- 新增 `X-Content-Type-Options` 與 `Referrer-Policy` 標頭。
- **已知且未處理**：上游 API 無認證且公網可達，本工具部署後同樣不設存取限制。經維護者決定暫不處理，詳見 [README](README.md#安全性注意事項)。

### 文件

- `CLAUDE.md`、`CONTRIBUTING.md`、`docs/API.md`、本檔案
- `docs/API.md` 記錄了實測得出的上游行為，包括空 body、一 SN 多記錄、無 CORS、未指定 SN 時回傳不固定等
- 新增 `.gitignore`（先前沒有）
- 新增 `scripts/dev-server.mjs`，讓本機測試不需要安裝或登入 Vercel CLI

---

## 1.x — 2026-03-01 至 2026-03-26

Streamlit 版本。單檔 `query_api.py`，功能為依 `SITE` / `TYPE` / `SN` 查詢並顯示 JSON，支援 PRD / DEV 切換與 Copy JSON。詳見 git 歷史。
