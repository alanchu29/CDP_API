# 開發指南

## 本機執行

```bash
node scripts/dev-server.mjs
```

開 `http://localhost:3000`。需要 Node 18 以上（用到原生 `fetch` 與頂層 `await`）。不需要 `npm install` —— 本專案沒有 runtime 依賴。

存檔後重新整理瀏覽器即可看到 `index.html` 的改動；改 `api/query.js` 則需要重啟伺服器。

也可以用官方 CLI，行為更貼近正式環境，但需要安裝並登入：

```bash
npm i -g vercel && vercel dev
```

> 直接用瀏覽器開啟 `index.html` 檔案不會運作 —— `/api/query` 需要有 runtime 才存在。

## 部署

推到 `main` 即自動部署。首次設定：

1. [vercel.com](https://vercel.com) 用 GitHub 登入
2. **Add New → Project** → 選 `CDP_API`
3. Framework Preset 選 **Other**，build command 與 output directory 全部留空
4. Deploy

## 常見修改

### 新增 SITE 或 TYPE

只改 `index.html` 的 `<select>`。後端不需要動 —— `api/query.js` 對 `site` / `type` 只做「非空」檢查，刻意不維護白名單，這樣上游新增機種時前端改一行就好。

```html
<option value="新機種代號">顯示名稱</option>
```

> `env` 是唯一有白名單的參數，因為它會被插進上游 URL 的路徑。那是 SSRF 防護，不要比照辦理。

### 調整預設隱藏哪些欄位

`index.html` 的 `LONG_VALUE_CHARS`（預設 120）。任一欄位的最長值超過這個字元數就預設收起。這是動態判斷，不是寫死清單，所以未實測過的 `TYPE` 若回傳不同 schema 也能自適應。

表格內的截斷長度另由 `CELL_TRUNCATE`（預設 60）控制。

### 調整逾時

兩個地方要一起改，且**上游的值必須小於平台的值**：

- `vercel.json` 的 `maxDuration` —— 平台層級的上限
- `api/query.js` 的 `UPSTREAM_TIMEOUT_MS` —— 對上游的上限

目前是 60 秒 / 55 秒。留這 5 秒差距，function 才來得及回傳有意義的逾時訊息，而不是被平台直接砍斷。

### 若上游哪天開了 CORS

前端只有一處呼叫 API（`runQuery()` 裡的 `fetch('/api/query')`）。把它改成直接打上游、調整請求格式，即可刪掉 `api/query.js`、`vercel.json`、`package.json`，改用 GitHub Pages 託管。這個結構是刻意保留的退路。

## 推送前檢查

沒有 CI，所以這幾項請手動跑：

```bash
node --check api/query.js
node -e "const h=require('fs').readFileSync('index.html','utf8');new Function(h.match(/<script>([\s\S]*)<\/script>/)[1]);console.log('inline JS OK')"
```

改過 `api/query.js` 的話，再跑一次 [docs/API.md](docs/API.md#驗證案例) 的驗證案例。

UI 改動請順手確認：手機寬度（約 400px）不會橫向捲動、表格欄位很多時仍可捲動、長憑證欄位不會撐破版面。

## 撰碼風格

規則寫在 [CLAUDE.md](CLAUDE.md#撰碼慣例)，摘要：

- vanilla JS，不加依賴、不加建置步驟
- CSS 變數定義在 `:root`，**不用 `!important`**
- 註解寫「為什麼」，不寫「做什麼」
- 使用者可見文字用繁中，識別字與 commit 訊息用英文

## 不要做的事

- 不要繼續開發 `query_api.py`（舊版 Streamlit，已停用）
- 不要引入公開 CORS proxy
- 不要移除 `api/query.js` 的 `ALLOWED_ENVS` 檢查
- 不要在未實測的情況下把 API 行為寫進文件 —— 本專案已經因此錯過一次，見 [docs/API.md](docs/API.md)
