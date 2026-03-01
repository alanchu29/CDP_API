# Wiwynn CDP Cerberus API 查詢系統

本專案為基於 Streamlit 的內部工具，可透過 `SITE`、`TYPE` 與選填 `SN` 查詢 Wiwynn Cerberus API。

## 功能特色

- 可依 `SITE` 與 `TYPE` 進行 Cerberus API 查詢。
- `SN` 可不填，也可一次輸入多筆（每行一筆）。
- 側欄可切換環境（`PRD` / `DEV`）。
- 當 `SITE`、`TYPE` 或 `ENV` 切換時，自動清空 SN 與 Response。
- 可於回應區一鍵 `Copy JSON`。
- 側欄 `System Status` 顯示目前 API endpoint 供參考。

## 專案結構

- `query_api.py`：主要 Streamlit 應用程式。
- `requirements.txt`：Python 相依套件。

## 執行需求

- Python 3.9 以上（建議）
- 需可連線至：
  - `https://apim.wiwynn.com/nifi/prd/api/cerberus/v1/sn_info`
  - `https://apim.wiwynn.com/nifi/dev/api/cerberus/v1/sn_info`

## 安裝方式

```bash
pip install -r requirements.txt
```

## 啟動方式

```bash
streamlit run query_api.py
```

啟動後請開啟終端機顯示的本機網址（通常為 `http://localhost:8501`）。

## 使用流程

1. 在左側欄選擇 `SITE` 與 `TYPE`。
2. 在 **System Status** 選擇 `ENV`（`PRD` 或 `DEV`）。
3. （選填）輸入 SN，每行一筆。
4. 點擊 `Send Request`。
5. 在 `Response` 區查看回傳結果。
6. 點擊 `Copy JSON` 複製完整 JSON 回應內容。

## 注意事項

- 若 `SN` 留空，仍會以 `SITE` 與 `TYPE` 發送 API 請求。
- `Copy JSON` 依賴瀏覽器剪貼簿 API；若被瀏覽器權限或政策限制，會顯示錯誤訊息。
- 本工具為內部使用用途。
