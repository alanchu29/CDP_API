import streamlit as st
import requests
import json
from datetime import datetime

# 設定頁面資訊
st.set_page_config(
    page_title="Wiwynn CDP Cerberus API Query System", 
    page_icon="🛡️",
    layout="centered"
)

# --- 參考原始風格的 CSS 注入 ---
st.markdown("""
    <style>
    /* 全域背景設為深色 */
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    
    /* 修正輸入框顏色：深底白字 */
    div[data-baseweb="textarea"] textarea {
        color: #ffffff !important;
        background-color: #1e2128 !important;
        border: 1px solid #30363d !important;
        font-family: 'Source Code Pro', monospace !important;
    }

    /* 標題區域樣式 */
    .main-header {
        text-align: center;
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    .title-text {
        font-size: 2.2rem;
        font-weight: 700;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
    }
    .dev-tag {
        font-size: 1.1rem;
        color: #58a6ff;
        font-weight: 600;
        margin-top: 0.5rem;
    }

    /* 按鈕樣式：深色簡約 */
    .stButton>button {
        width: 100%;
        background-color: #21262d;
        color: #ffffff;
        border: 1px solid #30363d;
        padding: 0.6rem;
        border-radius: 6px;
        transition: 0.2s;
    }
    .stButton>button:hover {
        background-color: #30363d;
        border-color: #8b949e;
        color: #ffffff;
    }

    /* 側邊欄深色優化 */
    section[data-testid="stSidebar"] {
        background-color: #010409 !important;
    }
    
    /* 移除不必要的間距 */
    .block-container {
        padding-top: 3rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 標題與署名 ---
st.markdown(f"""
    <div class="main-header">
        <div class="title-text">🛡️ Wiwynn CDP Cerberus API Query System</div>
        <div class="dev-tag">@Dixon Chu</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<p style='text-align: center; color: #8b949e;'>請輸入序號以進行查詢。本系統直接存取 Wiwynn API Gateway。</p>", unsafe_allow_html=True)

# --- Sidebar 設定區 ---
with st.sidebar:
    st.image("https://www.wiwynn.com/wp-content/uploads/2022/03/wiwynn_logo.png", width=150)
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("⚙️ 請求設定")
    
    site_options = ['WCZ', 'WYMY', 'WYMX', 'WYTN']
    site = st.selectbox("選擇 SITE", options=site_options, index=2)
    
    type_map = {
        "overlake (Celestial Peak, Glacier Peak)": "overlake",
        "agilex (Glacier Peak)": "agilex",
        "m1120": "m1120",
        "SoC": "SoC",
        "CaP": "CaP"
    }
    type_label = st.selectbox("選擇 TYPE", options=list(type_map.keys()), index=2)
    selected_type = type_map[type_label]
    
    st.divider()
    st.markdown("### 🛰️ 系統狀態")
    st.success("API Gateway: Online")
    st.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d')}")

# --- 主輸入區 ---
st.markdown("### 📋 輸入序號 (SN)")
sn_text = st.text_area(
    "請輸入 SN (每行一個)", 
    value="M1304365003B53823450076", 
    height=200,
    label_visibility="collapsed"
)

# 發送按鈕
if st.button("🚀 發送請求 (Send Request)"):
    sn_list = [s.strip() for s in sn_text.replace(',', '\n').split('\n') if s.strip()]
    
    if not sn_list:
        st.warning("⚠️ 請輸入至少一個序號。")
    else:
        url = "https://apim.wiwynn.com/nifi/prd/api/cerberus/v1/sn_info"
        payload = {"SITE": site, "TYPE": selected_type, "SN": sn_list}
        headers = {'Content-Type': 'application/json'}

        with st.spinner('連線中...'):
            try:
                response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
                
                if response.status_code == 200:
                    st.success(f"✅ 查詢成功！共找到 {len(response.json())} 筆資料。")
                    
                    # 顯示結果
                    result_json = response.json()
                    st.markdown("### 📦 回傳結果")
                    st.json(result_json)
                    
                    # 下載
                    st.download_button(
                        label="📥 下載 JSON 結果",
                        data=json.dumps(result_json, indent=4),
                        file_name=f"Query_{site}_{datetime.now().strftime('%H%M%S')}.json",
                        mime="application/json"
                    )
                else:
                    st.error(f"❌ 請求失敗 (狀態碼: {response.status_code})")
                    st.code(response.text)
            except Exception as e:
                st.error(f"⚠️ 發生連線錯誤: {str(e)}")

# Footer
st.divider()
st.caption("Wiwynn Corporation | Internal Tool | Developed by Dixon Chu")