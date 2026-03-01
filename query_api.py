import streamlit as st
import requests
import json

# 設定頁面資訊
st.set_page_config(page_title="Wiwynn Cerberus SN Info", layout="centered")

# --- UI 介面設計 ---
st.title("🛡️ Cerberus SN Info 查詢系統")
st.markdown("這是一個本機執行的工具，可以避開瀏覽器 CORS 限制，直接存取 API。")

with st.sidebar:
    st.header("⚙️ 請求設定")
    
    # Site 選擇
    site_options = ['WCZ', 'WYMY', 'WYMX', 'WYTN']
    site = st.selectbox("選擇 SITE", options=site_options, index=2) # 預設 WYMX
    
    # Type 選擇
    type_map = {
        "overlake (Celestial Peak, Glacier Peak)": "overlake",
        "agilex (Glacier Peak)": "agilex",
        "m1120": "m1120",
        "SoC": "SoC",
        "CaP": "CaP"
    }
    type_label = st.selectbox("選擇 TYPE", options=list(type_map.keys()), index=2)
    selected_type = type_map[type_label]

# SN 輸入區
st.subheader("📋 輸入序號 (SN)")
sn_text = st.text_area("請輸入 SN (每行一個，或以逗號分隔)", value="M1304365003B53823450076", height=150)

# 發送按鈕
if st.button("🚀 發送請求 (Send Request)", use_container_width=True):
    # 處理 SN 字串轉陣列
    sn_list = [s.strip() for s in sn_text.replace(',', '\n').split('\n') if s.strip()]
    
    if not sn_list:
        st.error("請至少輸入一個 SN")
    else:
        # API 設定
        url = "https://apim.wiwynn.com/nifi/prd/api/cerberus/v1/sn_info"
        payload = {
            "SITE": site,
            "TYPE": selected_type,
            "SN": sn_list
        }
        headers = {'Content-Type': 'application/json'}

        with st.spinner('正在與伺服器連線中...'):
            try:
                # 由 Python 後端發送請求，無視 CORS
                response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
                
                if response.status_code == 200:
                    st.success(f"查詢成功！狀態碼: {response.status_code}")
                    
                    # 顯示 JSON 結果
                    result_json = response.json()
                    st.subheader("📦 回傳結果 (JSON)")
                    st.json(result_json)
                    
                    # 提供下載按鈕
                    st.download_button(
                        label="📥 下載 JSON 結果",
                        data=json.dumps(result_json, indent=4),
                        file_name=f"api_result_{site}_{selected_type}.json",
                        mime="application/json"
                    )
                else:
                    st.error(f"請求失敗！狀態碼: {response.status_code}")
                    st.code(response.text)
                    
            except Exception as e:
                st.error(f"連線發生錯誤：{str(e)}")
                st.info("💡 解決建議：請檢查是否已連上 Wiwynn VPN 或內網環境。")

# 頁尾資訊
st.divider()
st.caption("Wiwynn Cerberus API Tool | Running on Local Python (No CORS Issues)")

# --- 如何執行此程式 ---
# 1. 安裝必要套件: 
#    pip install streamlit requests
#
# 2. 執行程式 (在終端機輸入):
#    streamlit run query_api.py