# Wiwynn CDP Cerberus API 查詢系統

查詢 Wiwynn Cerberus `sn_info` API 的內部工具。純靜態前端 + 一支 serverless proxy，部署在 Vercel，`git push` 即自動上線。

## 專案結構

```
index.html        前端（單檔，無框架、無建置步驟）
api/query.js      Serverless proxy，轉發請求到 Cerberus API
vercel.json       Function 逾時與安全標頭設定
package.json      標記為 ESM，供 Vercel Node runtime 使用
query_api.py      舊版 Streamlit 應用（已停用，保留備查）
```

## 為什麼需要 proxy

Cerberus API 從公網可達，但**不回傳任何 CORS 標頭**。瀏覽器因此禁止網頁的 JavaScript 讀取它的回應，純靜態頁面（例如 GitHub Pages）無法直接呼叫。

`api/query.js` 在伺服器端代為發送請求 —— server-to-server 不受 CORS 限制。

若日後 API 端加上 `Access-Control-Allow-Origin`，前端只需把 `fetch('/api/query')` 改成直接呼叫 API，即可拿掉 proxy 並改用 GitHub Pages 託管。

## 部署

1. 到 [vercel.com](https://vercel.com) 用 GitHub 帳號登入。
2. **Add New → Project**，選 `CDP_API` repo。
3. Framework Preset 選 **Other**，其餘留空（不需要 build command 或 output directory）。
4. Deploy。

之後每次 push 到 `main` 就會自動重新部署。

### 本機預覽

```bash
npm i -g vercel
vercel dev
```

開 `http://localhost:3000`。

> 直接用瀏覽器開啟 `index.html` 不會運作 —— `/api/query` 需要有 serverless runtime 才存在。

## 功能

- **SITE / TYPE / ENV**：ENV 可切 `PRD` / `DEV`，選擇會記在瀏覽器 localStorage。
- **批次 SN**：換行、逗號或空白分隔皆可，自動去重並顯示組數。
- **表格檢視**：可排序、跨欄位即時篩選、自由開關欄位。憑證類的長欄位（`HW_key1`–`HW_key3` 等）預設隱藏，點任一列可展開完整明細並個別複製。
- **JSON 檢視**：語法highlight，可一鍵複製。
- **匯出 CSV**：只匯出目前顯示的欄位與篩選結果，含 BOM 以便 Excel 正確讀取 UTF-8。
- <kbd>Ctrl</kbd>+<kbd>Enter</kbd> 送出查詢。

## API 行為備忘

- 回傳為 JSON 陣列。**一組 SN 可能對應多筆記錄** —— 例如 `m1120` 會回 `M1120_TPM` / `M1120_LION` / `M1120_BMC` 三筆，分別是不同的金鑰記錄，不是三塊板子。
- 查無資料時回 HTTP 200 搭配**完全空白的 body**（不是 `[]`），proxy 會將其正規化為 `{ records: [] }`。
- 帶 SN 查詢時會附上 `HwkeyDownloadStatus=all` 與 `GPkeyDownloadStatus=all` 兩個 query param。
- 未指定 SN 時的回傳內容不固定，實測同樣的請求可能回空、也可能回若干筆記錄。用途未明，建議一律指定 SN。
- 單筆 SN 查詢約需 1.5–2.5 秒。`vercel.json` 將 function 逾時設為 60 秒以容納批次查詢。

## 安全性注意事項

⚠️ **這支 API 目前沒有任何認證，且從公網可直接呼叫。**

- 無 API key、無 token、無 Cookie —— 知道 URL 的人都能查詢。
- 回傳內容包含硬體信任根等級的資料：TPM 憑證、Cerberus / Azure Hardware 憑證鏈、公鑰、料號、廠區與產線時間戳。
- 本 repo 為 public，端點與參數皆公開可見。
- 本工具部署後同樣不設存取限制。

若要加上防護，最實際的作法是在部署平台這層設存取控制（例如 Vercel 的 Deployment Protection，或改用 Cloudflare Access 綁公司帳號），無須改動 API。長期而言，仍建議與 API 負責人確認端點的公開範圍是否符合預期。

## 舊版 Streamlit

`query_api.py` 為改版前的 Streamlit 版本，已不再維護。如需執行：

```bash
pip install -r requirements.txt
streamlit run query_api.py
```
