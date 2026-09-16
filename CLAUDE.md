# CLAUDE.md

給 Claude Code 的專案脈絡。動手改任何東西之前先讀這份。

## 這是什麼

Wiwynn 內部工具，用來查詢 Cerberus `sn_info` API。純靜態前端 + 一支 serverless proxy，部署在 Vercel，`git push` 自動上線。

單一維護者、內部使用、規模刻意維持極小。**新增任何依賴之前，先確認它真的必要** —— 目前 runtime 依賴為零。

## 架構

```
瀏覽器 (index.html)
   │  POST /api/query
   ▼
Vercel Function (api/query.js)
   │  POST（server-to-server，不受 CORS 限制）
   ▼
https://apim.wiwynn.com/nifi/{prd|dev}/api/cerberus/v1/sn_info
```

| 檔案 | 角色 |
|---|---|
| `index.html` | 前端全部 —— HTML、CSS、JS 都在裡面。無框架、無建置步驟 |
| `api/query.js` | 唯一的後端。驗證輸入、轉發、正規化回應 |
| `scripts/dev-server.mjs` | 本機測試用，模擬 Vercel runtime。Vercel 不會執行它 |
| `vercel.json` | Function 逾時 60 秒、安全標頭 |
| `query_api.py` | 舊版 Streamlit，已停用。**不要繼續開發它** |

## 硬性限制

這幾條是刻意的設計決定，不是還沒做完：

1. **不要引入建置步驟。** 沒有 bundler、沒有 TypeScript 編譯、沒有 CSS 前處理器。`index.html` 可以直接被瀏覽器讀懂。
2. **不要把 `index.html` 拆檔。** 除非它超過約 1,500 行。目前 950 行，單檔的可讀性仍勝過跨檔跳轉。
3. **不要動 `api/query.js` 的 `ALLOWED_ENVS` allow-list。** `env` 會被插進上游 URL 的路徑，那個 allow-list 是 SSRF 防護。
4. **不要用公開 CORS proxy**（corsproxy.io 之類）。回傳內容含硬體信任根等級的資料，不能流經不明第三方。
5. **前端呼叫 API 的地方只有一處** —— `runQuery()` 裡的那個 `fetch`。維持如此：若哪天上游開了 CORS，拿掉 proxy 只需要改這一行。

## 上游 API 的意外行為

完整版在 [docs/API.md](docs/API.md)，以下是最容易踩的三個：

- **查無資料時回 200 + 完全空白的 body**，不是 `[]`。直接 `.json()` 會丟 parse error。`api/query.js` 已處理，改寫該處時不要弄丟。
- **一組 SN 會對應多筆記錄。** `m1120` 回三筆（`M1120_TPM` / `M1120_LION` / `M1120_BMC`），是同一塊板子的不同金鑰記錄。所以「記錄數」和「SN 數」必須分開呈現。
- **上游沒有任何 CORS 標頭。** 這是 `api/query.js` 存在的唯一理由。不要以為它只是個可有可無的包裝。

另外：**上游沒有任何認證，且從公網可達。** 這是已知現況、維護者已知悉並決定暫不處理，不需要在每次改動時重新提起。詳見 README 的安全性章節。

## 測試

```bash
node scripts/dev-server.mjs     # http://localhost:3000
```

沒有自動化測試。改動後至少手動跑過 [docs/API.md](docs/API.md) 裡的驗證案例 —— 那份清單涵蓋正常查詢、批次、空結果、非法 `env`、缺參數、錯誤 method。

語法檢查：

```bash
node --check api/query.js
```

## 撰碼慣例

- **JS**：vanilla ES2020+，`const`/`let`，不用 jQuery 或任何函式庫。
- **CSS**：色彩與尺寸走 `:root` 的 CSS 變數。**不要用 `!important`** —— 舊的 Streamlit 版有 276 行 `!important` hack 綁死在框架內部 DOM 上，那正是這次改寫要擺脫的東西。
- **註解寫「為什麼」，不寫「做什麼」。** 程式碼本身已經說明它在做什麼。
- **語言**：使用者可見文字用繁體中文；識別字、註解、commit 訊息用英文。

## 這個專案踩過的坑

- **不要在沒實測的情況下宣稱 API 行為。** 本專案曾據推測寫下「未指定 SN 時必定回空」，實測卻發現同樣的請求有時會回若干筆記錄（後來官方規格證實那是「待處理佇列」）。不確定就寫「不確定」，或實際打一次。
- **也不要在沒實測的情況下就相信規格。** 規格 v4.3.0 記載的 `ROW_LIMIT` 在 PRD 上完全無效，規格聲稱非 TPM 型別的 `Public_key` 為 null 但實際有值。規格是起點，不是結論。
- **不要把樣式綁在框架產生的 DOM 上。** 舊版 CSS 依賴 `data-baseweb`、`react-json-view` 等 Streamlit 內部實作細節，框架一升級就整片失效。

## 官方規格

上游有正式規格：**Cerberus_API_spec v4.3.0 (2026-09-14)**，位於 Dixon Chu 的 OneDrive `Attachments/` 資料夾（同目錄有 v4.2.0、v3.0.1 可比對版本差異）。聯絡人 `WYHQ_DP_IT@wiwynn.com`、`Remi_Chang@wiwynn.com`。

[docs/API.md](docs/API.md) 已依該規格重寫，並用 **[實測]** 標出與規格不符之處。動手改上游相關的程式前先讀那份文件 —— 特別是這三點：

1. **`TYPE` 是唯一必填欄位**，`SITE` 省略代表不限廠區（規格支援的查詢模式）。
2. **`HwkeyDownloadStatus` / `GPkeyDownloadStatus` 決定回傳哪些記錄**：不帶只回「尚未下載金鑰」的待處理佇列，帶 `=all` 才是全部。這不是可有可無的參數。
3. **帶 `all` 時上限 1000 筆且無任何提示。** `api/query.js` 用「筆數剛好等於上限」來推測截斷，這是目前唯一可用的訊號。
