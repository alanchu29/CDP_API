# Cerberus `sn_info` API 參考

依據官方規格 **Cerberus_API_spec v4.3.0 (2026-09-14)** 整理，並標註本專案實測到的差異。

- 規格聯絡人：`WYHQ_DP_IT@wiwynn.com`、`Remi_Chang@wiwynn.com`
- 規格檔案：Dixon Chu 的 OneDrive → `Attachments/Cerberus_API_spec_v4.3.0(20260914).xlsx`（同目錄另有 v4.2.0、v3.0.1 舊版可比對）
- 實測日期：2026-09-16

> 標示 **[實測]** 的段落來自實際呼叫端點的觀察，其中與規格不符之處已特別註明。

## 端點

```
https://apim.wiwynn.com/nifi/{env}/api/cerberus/v1/sn_info
```

`{env}` 為 `prd` 或 `dev`。

本專案只使用 `get_sn_info`（唯讀）。規格另有三支**會寫入資料庫**的 API，本工具刻意不實作：

| 功能 | Method | Path |
|---|---|---|
| `update_hwkey` | PUT | `/nifi/{env}/api/cerberus/v1/hwkey_info` |
| `update_gpkey` | PUT | `/nifi/{env}/api/cerberus/v1/gpkey_info` |
| `update_hwkey_with_action` | PUT | `/nifi/{env}/api/cerberus/v1/hwkey_action` |

### 可達性與認證 [實測]

規格未著墨，以下為實測結果：

- **從公網可達。** 在一般家用網路、未連 VPN、不在公司內網的情況下直接呼叫成功，回應含 `Server-Timing: origin`，代表請求確實穿透 CDN 打到後端。
- **無任何認證。** 不需要 API key、token 或 Cookie。
- **不回傳任何 CORS 標頭。** preflight `OPTIONS` 與 simple request（`Content-Type: text/plain`）皆測過，回應都沒有 `Access-Control-Allow-Origin`。這是本專案需要 `api/query.js` 的唯一理由。
- 基礎設施為 **Akamai → Azure API Management → NiFi**。

## 請求

```http
POST /nifi/prd/api/cerberus/v1/sn_info?HwkeyDownloadStatus=all&GPkeyDownloadStatus=all
Content-Type: application/json

{
  "SITE": "WYMX",
  "TYPE": "m1120",
  "SN": ["M1304365003B53823450076"]
}
```

### Request body

| 欄位 | 型別 | 必填 | 大小寫 | 說明 |
|---|---|---|---|---|
| `TYPE` | String | **是** | 不分 | `overlake`、`agilex`、`m1120`、`SoC`、`CaP`、`c41ae` |
| `SITE` | String | 否 | 不分 | `WCZ`、`WYMY`、`WYMX`、`WYTN`。**省略代表不限廠區** |
| `SN` | List | 否 | **區分** | 序號陣列。省略或給 `[]` 都代表不限 SN |
| `ROW_LIMIT` | Integer | 否 | — | 正整數。回傳筆數上限，見下方 |

**`TYPE` 是唯一的必填欄位。** 規格提供了多組「無 SITE 限制」的請求範例。

**任何欄位都不接受 JSON `null`** —— 不需要就整個省略該 key。`SN` 例外允許空陣列 `[]`。

**`SN` 區分大小寫**，其餘欄位不分。所以不要對 SN 做大小寫正規化。

### Query parameters：`HwkeyDownloadStatus` / `GPkeyDownloadStatus`

兩者皆為選填，唯一合法值是 `all`。**這組參數決定回傳哪些記錄，是本 API 最容易誤用的地方。**

| 用法 | 行為 |
|---|---|
| **不帶** | 只回**尚未下載金鑰**的記錄（待處理佇列） |
| **帶 `=all`** | 移除下載狀態過濾，回傳全部記錄 |

規格的 SQL 說明了原因：

```sql
WHERE (HwkeyDownloadStatus IS NULL OR HwkeyDownloadStatus = '')
  AND (GPkeyDownloadStatus IS NULL OR GPkeyDownloadStatus = '')
```

只要有任一個設為 `all`，這段過濾就被移除。

- 帶了參數卻**不給值**會回 **400 BadRequest**。
- 本專案沿用舊版 Streamlit 的行為：**有 SN 時帶 `all`，無 SN 時不帶**。等於「查指定序號 → 看完整狀態；不指定 → 撈待處理佇列」。

### `ROW_LIMIT` 與 1000 筆上限

v4.3.0 新增。**這是很容易踩到的陷阱：**

| 情境 | 上限 |
|---|---|
| 有給 `ROW_LIMIT` | 以 `ROW_LIMIT` 為準，API 不設上界 |
| 未給 `ROW_LIMIT`，且帶了 `all` | **截在 1000 筆，且不會有任何提示** |
| 未給 `ROW_LIMIT`，未帶 `all` | 無上限 |

**`ROW_LIMIT` 不是分頁工具。** 規格明確警告：帶 `all` 時過濾條件不變，所以同樣的前 N 筆會被重複回傳，不會往後推進。要逐批消化待處理記錄，應該**不帶 `all`** —— 記錄被下載後就會自動離開查詢結果。

`ROW_LIMIT` 算的是筆數不是大小，而每筆的大小依 `TYPE` 而異，所以能用多大要各自實測。

> ### ⚠ [實測] PRD 目前忽略 `ROW_LIMIT`
>
> 2026-09-16 實測：對 PRD 送 `ROW_LIMIT: 4` 搭配會回 9 筆的查詢，仍然拿到 9 筆。直接打上游繞過 proxy 結果相同，所以不是本專案的問題。
>
> spec v4.3.0 是 2026-09-14 發布的，這個欄位**看來還沒部署到 PRD**。
>
> `api/query.js` 仍會轉送 `ROW_LIMIT`（上線後即自動生效），但**現在不能依賴它來限制筆數**。也因此截斷偵測會同時檢查 1000 與 `ROW_LIMIT` 兩個上限，而不是讓 `ROW_LIMIT` 蓋過 1000 —— 否則真正的 1000 筆截斷會被漏掉。
>
> 要用之前請先重測。

### 大小限制

請求與回應合計上限 **100 MB**。超過會讓**整個請求失敗並回 413**，不會有部分結果，而且這個限制是在查詢執行完之後才判斷的。API 不會自動下修，呼叫端必須自己降低 `ROW_LIMIT` 重試。

## 回應

HTTP 200，body 為 **JSON 陣列**。

### 欄位

| 欄位 | 型別 | 可為 null | 說明 |
|---|---|---|---|
| `SN` | String | 否 | 序號 |
| `ID` | Int | 否 | 唯一識別碼 |
| `SI_Factory` | String | 否 | 廠區 |
| `PN` | String | 否 | 料號，例如 `M1304365-003$A21` |
| `PN_Type` | String | 否 | 金鑰記錄類型，見下方對照表 |
| `Public_key` | String | 是 | 規格稱僅 `M1120_TPM` 有值（TPMEKHASH_Key），其餘為 null。**[實測] 不符，見下方** |
| `HW_key1` / `HW_key2` / `HW_key3` | String | 是 | 硬體金鑰。Base64 DER 憑證，可長達數千字元 |
| `Hwkey_Download_Count` | Int | 否（預設 0） | 每次更新 +1 |
| `Hwkey_Download_Status` | String | 是 | 狀態碼，見下方 |
| `Hwkey_Download_Message` | String | 是 | 自由文字 |
| `Hwkey_Download_Time` | String | 是 | **UTC** 時間，`YYYY-MM-DD HH:MM:SS` |
| `Hwkey_Download_LocalTime` | String | 是 | **使用者當地**時間，格式同上 |
| `GP_Public_key` | String | 是 | GP / CP 專用 |
| `GPkey_Download_*` | 同 `Hwkey_Download_*` | 是 | GP / CP 專用 |
| `Intel_CA` / `MSFT_CA` | String | 是 | GP / CP 專用 |

### `Hwkey_Download_Status` 狀態碼

| 值 | 意義 |
|---|---|
| `5` | 下載成功（金鑰已下載並寫入 DB） |
| `6` | 下載失敗（SN 已送出，但 HKMS 回傳錯誤） |
| `8` | 下載次數超過上限 |
| `99` | 其他（廢棄 SN 的備份） |
| `999` | B2B 忽略（重複 SN） |
| `null` / `''` | 尚未下載 —— 不帶 `all` 參數時只會回這一類 |

### `TYPE` → `PN_Type` 對照

| 請求的 `TYPE` | 回傳的 `PN_Type` |
|---|---|
| `m1120` | `M1120_LION`、`M1120_BMC`、`M1120_TPM`、`M1120` |
| `CP` | `Celestial Peak` |
| `GP` | `Glacier Peak` |
| `SoC` | `CPU SoC` |
| `CaP` | `CaP_CMC`、`CaP_OMC` |
| `c41ae` | `C41AE_SSM_LION` |

**一組 SN 會對應多筆記錄。** [實測] 查詢單一 `m1120` 序號回三筆（`M1120_TPM` / `M1120_LION` / `M1120_BMC`），是同一塊板子的三種金鑰記錄，不是三塊板子。UI 因此必須把「記錄數」與「SN 數」分開顯示。

### [實測] 與規格不符：`Public_key`

規格說「`PN_TYPE` 不是 `M1120_TPM` 時 `Public_key` = null」，但實測 `M1120_LION` 與 `M1120_BMC` 的 `Public_key` **都有值**（Base64 EC 公鑰）。

程式請以實測為準，不要假設非 TPM 型別的 `Public_key` 必為 null。

### [實測] 查無資料

回 **HTTP 200 搭配完全空白的 body** —— 不是 `[]`，是零位元組。規格未載明。

直接呼叫 `response.json()` / `JSON.parse()` 會拋出 parse error。舊版 Streamlit 正是栽在這裡：錯誤被寬泛的 `except Exception` 吞掉，對使用者顯示成「連線錯誤」。

`api/query.js` 會將其正規化為 `{ "records": [] }`。

## 錯誤回應

| 狀態 | 情境 |
|---|---|
| 400 | 參數無效，或帶了 query param 卻沒給值 |
| 413 | 請求或回應超過 100 MB（整筆失敗，無部分結果） |
| 500 | JSON 格式錯誤、DB 連線失敗、內部錯誤、欄位驗證失敗 |

`ROW_LIMIT` 驗證失敗（0、負數、小數、字串）會回 500 並附訊息 `'ROW_LIMIT' must be a positive integer.`

## [實測] 回應時間

| 情境 | 實測 |
|---|---|
| 單筆 SN | 1.5–2.5 秒 |
| 三筆 SN（回 9 筆記錄） | 約 2.4 秒 |

批次查詢**不是**線性增長，一次送多筆遠優於逐筆呼叫。

`vercel.json` 將 function 逾時設為 60 秒，`api/query.js` 對上游設 55 秒 —— 留 5 秒讓 function 能回傳有意義的逾時訊息。大批量 SN 的上限尚未實測。

## 驗證案例

改動 `api/query.js` 後請至少手動跑過這幾項。先啟動 `node scripts/dev-server.mjs`：

```bash
BASE=http://localhost:3000/api/query

# 1. 正常查詢 -> 200，3 筆記錄
curl -s -X POST $BASE -H "Content-Type: application/json" \
  -d '{"env":"prd","site":"WYMX","type":"m1120","sn":["M1304365003B53823450076"]}'

# 2. 批次 -> 200，9 筆記錄
curl -s -X POST $BASE -H "Content-Type: application/json" \
  -d '{"env":"prd","site":"WYMX","type":"m1120","sn":["M1304365003B53823450076","M1304365002B53651134076","M1304365002B52321662076"]}'

# 3. 不指定 SITE（規格支援）-> 200
curl -s -X POST $BASE -H "Content-Type: application/json" \
  -d '{"env":"prd","type":"m1120","sn":["M1304365003B53823450076"]}'

# 4. 不存在的 SN -> 200，{"records":[],"empty":true}
curl -s -X POST $BASE -H "Content-Type: application/json" \
  -d '{"env":"prd","site":"WYMX","type":"m1120","sn":["NOSUCHSN123456"]}'

# 5. 非法 env（SSRF 防護）-> 400
curl -s -X POST $BASE -H "Content-Type: application/json" \
  -d '{"env":"../../evil","site":"WYMX","type":"m1120","sn":["X"]}'

# 6. 缺少 type -> 400
curl -s -X POST $BASE -H "Content-Type: application/json" -d '{"env":"prd","site":"WYMX"}'

# 7. GET -> 405
curl -s $BASE
```

> 案例 1–4 會打到正式環境的 API。這是唯讀查詢，但畢竟是 PRD，不要拿它跑壓力測試。

## 安全性

見 [README](../README.md#安全性注意事項)。摘要：此端點無認證、公網可達，且回傳硬體信任根等級的資料（TPM 憑證、Cerberus / Azure Hardware 憑證鏈、公鑰、產線時間戳）。
