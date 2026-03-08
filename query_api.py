import streamlit as st
import streamlit.components.v1 as components
import requests
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Wiwynn CDP Cerberus API Query System", 
    page_icon="💻",
    layout="centered"
)

# Persist latest successful response across reruns.
if "last_result_json" not in st.session_state:
    st.session_state["last_result_json"] = None

if "sn_text_input" not in st.session_state:
    st.session_state["sn_text_input"] = "M1304365003B53823450076"

# API endpoint template (single source of truth for UI + request call)
API_URL_TEMPLATE = "https://apim.wiwynn.com/nifi/{env}/api/cerberus/v1/sn_info"

def reset_input_and_response():
    st.session_state["sn_text_input"] = ""
    st.session_state["last_result_json"] = None

# --- CSS styling ---
st.markdown("""
    <style>
    :root {
        --bg-main: #0b1220;
        --bg-panel: #111a2b;
        --bg-input: #0f1726;
        --text-main: #e6edf7;
        --text-muted: #9fb3c8;
        --accent: #4ea1ff;
        --accent-strong: #2f81f7;
        --border: #2b3f5f;
    }

    /* Global dark theme */
    .stApp {
        background: radial-gradient(circle at 15% 0%, #1a2740 0%, var(--bg-main) 45%);
        color: var(--text-main);
    }
    header[data-testid="stHeader"],
    .stToolbar,
    #MainMenu,
    footer {
        display: none !important;
    }
    
    /* Text area styling: dark background with light text */
    div[data-baseweb="textarea"] textarea {
        color: var(--text-main) !important;
        background-color: var(--bg-input) !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 10px !important;
        font-family: 'Source Code Pro', monospace !important;
        font-size: 1rem !important;
    }
    div[data-baseweb="textarea"] textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px rgba(78, 161, 255, 0.25) !important;
    }
    div[data-baseweb="textarea"] textarea[disabled] {
        color: #eaf3ff !important;
        -webkit-text-fill-color: #eaf3ff !important;
        background-color: #0f1726 !important;
        border: 1.5px solid #2e466c !important;
        opacity: 1 !important;
    }
    div[data-testid="stJson"] {
        border: 1.5px solid #2e466c !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }
    div[data-testid="stJson"] .react-json-view,
    div[data-testid="stJson"] .react-json-view > div,
    div[data-testid="stJson"] [role="tree"] {
        background-color: #0f1726 !important;
    }
    div[data-testid="stJson"] * {
        opacity: 1 !important;
    }
    div[data-testid="stJson"] span,
    div[data-testid="stJson"] p {
        color: #e8f1ff !important;
        background: transparent !important;
    }
    div[data-testid="stJson"] span[class*="key"] {
        color: #7fd1ff !important;
        font-weight: 600 !important;
    }
    div[data-testid="stJson"] span[class*="string"] {
        color: #ffd39b !important;
    }
    div[data-testid="stJson"] span[class*="number"] {
        color: #90f2b0 !important;
    }
    div[data-testid="stJson"] span[class*="boolean"] {
        color: #d6b3ff !important;
        font-weight: 700 !important;
    }
    div[data-testid="stJson"] span[class*="null"],
    div[data-testid="stJson"] span[title="null"],
    div[data-testid="stJson"] span[aria-label="null"] {
        color: #ff9da1 !important;
        background: transparent !important;
        font-weight: 700 !important;
    }

    /* Header area */
    .main-header {
        display: flex;
        justify-content: center;
        padding-top: 2rem;
        padding-bottom: 1rem;
    }
    .header-content {
        display: inline-block;
    }
    .title-text {
        font-size: 2.2rem;
        font-weight: 700;
        color: #f7fbff;
        letter-spacing: 0.2px;
        text-shadow: 0 2px 18px rgba(78, 161, 255, 0.3);
    }
    .dev-tag {
        font-size: 1.1rem;
        color: #72b7ff;
        font-weight: 600;
        margin-top: 0.5rem;
        text-align: left;
    }

    /* Button style */
    .stButton>button {
        width: 100%;
        background-color: #1b263a;
        color: #eaf2ff;
        border: 1px solid var(--border);
        padding: 0.6rem;
        border-radius: 10px;
        transition: 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #24344f;
        border-color: #5f82b3;
        color: #ffffff;
        transform: translateY(-1px);
    }
    .stButton>button[kind="primary"] {
        font-size: 1.15rem;
        font-weight: 700;
        padding: 0.9rem 1rem;
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 100%);
        border-color: #4a9cff;
        color: #ffffff;
        box-shadow: 0 8px 22px rgba(47, 129, 247, 0.35);
    }
    .stButton>button[kind="primary"]:hover {
        background: linear-gradient(135deg, #5aa9ff 0%, #3b8cff 100%);
        border-color: #7bb7ff;
        box-shadow: 0 10px 24px rgba(47, 129, 247, 0.45);
    }

    div[data-baseweb="select"] > div {
        background-color: var(--bg-input) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }
    div[data-baseweb="select"] span {
        color: var(--text-main) !important;
    }

    /* Sidebar dark mode */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #14233a 0%, #0d1728 100%) !important;
        border-right: 1px solid #36537f;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: #eaf3ff !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 800 !important;
        text-shadow: 0 2px 12px rgba(78, 161, 255, 0.25);
    }
    section[data-testid="stSidebar"] hr {
        border-color: #3a5885 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] label p,
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] label span {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
        color: #f0f7ff !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #0f1c31 !important;
        border: 1.5px solid #3a5b8a !important;
        box-shadow: 0 0 0 1px rgba(78, 161, 255, 0.12) inset;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] *,
    section[data-testid="stSidebar"] div[data-baseweb="select"] span,
    section[data-testid="stSidebar"] div[data-baseweb="select"] div,
    section[data-testid="stSidebar"] div[data-baseweb="select"] input,
    section[data-testid="stSidebar"] div[data-baseweb="select"] svg {
        color: #f7fbff !important;
        fill: #f7fbff !important;
        -webkit-text-fill-color: #f7fbff !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] div[class*="singleValue"],
    section[data-testid="stSidebar"] div[data-baseweb="select"] div[class*="ValueContainer"] * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        font-weight: 700 !important;
        text-shadow: 0 0 1px rgba(255, 255, 255, 0.15);
    }
    section[data-testid="stSidebar"] div[role="listbox"] div[role="option"] {
        color: #f4f9ff !important;
        background-color: #0f1c31 !important;
    }
    section[data-testid="stSidebar"] div[role="listbox"] div[role="option"][aria-selected="true"] {
        background-color: #1f3557 !important;
        color: #ffffff !important;
    }
    section[data-testid="stSidebar"] [data-testid="stRadio"] label span {
        color: #f0f7ff !important;
        font-weight: 700 !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
        color: #c2d7ef !important;
        font-size: 0.98rem !important;
    }
    .api-endpoint-box {
        background-color: #0d1a2e;
        border: 1.5px solid #3a5b8a;
        color: #f3f8ff;
        border-radius: 10px;
        padding: 0.75rem 0.85rem;
        font-size: 0.95rem;
        font-family: "Source Code Pro", "Consolas", monospace;
        font-weight: 700;
        line-height: 1.35;
        word-break: break-all;
    }
    
    /* Remove extra top spacing */
    .block-container {
        padding-top: 3rem !important;
    }
    .copy-notice-center {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background-color: rgba(33, 38, 45, 0.95);
        color: #ffffff;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 0.8rem 1.2rem;
        z-index: 9999;
        font-weight: 600;
        font-size: 1.2rem;
        box-shadow: 0 8px 24px rgba(1, 4, 9, 0.6);
        animation: fadeOutCenterNotice 1.8s ease forwards;
    }
    div[data-testid="stCodeBlock"] pre {
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        background-color: #0f1726 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stCodeBlock"] pre {
        background-color: #0d1a2e !important;
        border: 1.5px solid #3a5b8a !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stCodeBlock"] pre code {
        color: #eef5ff !important;
        background: transparent !important;
        font-weight: 600 !important;
    }
    div[data-testid="stCodeBlock"] pre code {
        color: #eaf3ff !important;
    }
    @keyframes fadeOutCenterNotice {
        0% { opacity: 0; }
        10% { opacity: 1; }
        80% { opacity: 1; }
        100% { opacity: 0; visibility: hidden; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- Title and signature ---
st.markdown(f"""
    <div class="main-header">
        <div class="header-content">
            <div class="title-text">Wiwynn CDP Cerberus API Query System</div>
            <div class="dev-tag">@Dixon Chu</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<p style='text-align: center; color: #8b949e;'>Enter serial numbers to run queries. This tool connects directly to the Wiwynn API Gateway.</p>", unsafe_allow_html=True)

# --- Sidebar settings ---
with st.sidebar:
    st.subheader("⚙️ Settings")
    
    site_options = ['WCZ', 'WYMY', 'WYMX', 'WYTN']
    site = st.selectbox(
        "SITE",
        options=site_options,
        index=2,
        key="site_select",
        on_change=reset_input_and_response
    )
    
    type_map = {
        "overlake (Celestial Peak, Glacier Peak)": "overlake",
        "agilex (Glacier Peak)": "agilex",
        "m1120": "m1120",
        "SoC": "SoC",
        "CaP": "CaP"
    }
    type_label = st.selectbox(
        "TYPE",
        options=list(type_map.keys()),
        index=2,
        key="type_select",
        on_change=reset_input_and_response
    )
    selected_type = type_map[type_label]
    
    st.divider()
    st.markdown("### 🛰️ System Status")
    api_environment = st.radio(
        "ENV",
        options=["PRD", "DEV"],
        horizontal=True,
        key="api_env_select",
        on_change=reset_input_and_response
    )
    API_URL = API_URL_TEMPLATE.format(env=api_environment.lower())
    st.success("API Gateway: Online")
    st.caption(f"Current environment: {api_environment}")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d')}")
    st.caption("Current API endpoint")
    st.markdown(
        f"<div class='api-endpoint-box'>{API_URL}</div>",
        unsafe_allow_html=True
    )

# --- Main input area ---
st.markdown("### 📋 Enter Serial Number (SN)")
sn_text = st.text_area(
    "Enter SN (one per line)", 
    height=95,
    label_visibility="collapsed",
    key="sn_text_input"
)

# Send button
send_col_left, send_col_mid, send_col_right = st.columns([1, 2, 1])
with send_col_mid:
    send_clicked = st.button(
        "🚀 Send Request",
        key="send_request_button",
        type="primary",
        use_container_width=True
    )
if send_clicked:
    sn_list = [s.strip() for s in sn_text.replace(',', '\n').split('\n') if s.strip()]
    payload = {"SITE": site, "TYPE": selected_type}
    if sn_list:
        payload["SN"] = sn_list

    headers = {'Content-Type': 'application/json'}

    with st.spinner('Connecting...'):
        try:
            response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=15)
            
            if response.status_code == 200:
                result_json = response.json()
                st.session_state["last_result_json"] = result_json
                st.success(f"✅ Query succeeded. Found {len(result_json)} record(s).")
            else:
                st.error(f"❌ Request failed (Status code: {response.status_code})")
                st.code(response.text)
        except Exception as e:
            st.error(f"⚠️ Connection error: {str(e)}")

if st.session_state["last_result_json"] is not None:
    result_json = st.session_state["last_result_json"]
    result_json_text = json.dumps(result_json, indent=4)
    response_title_col, response_action_col = st.columns([5, 2])
    with response_title_col:
        st.markdown("### 📦 Response")
    with response_action_col:
        components.html(
            f"""
            <div style="display:flex;justify-content:flex-end;align-items:center;height:44px;">
              <button id="copyJsonBtn" style="
                width: 100%;
                background: linear-gradient(135deg, #4ea1ff 0%, #2f81f7 100%);
                color: #ffffff;
                border: 1px solid #4a9cff;
                border-radius: 10px;
                font-size: 0.95rem;
                font-weight: 700;
                padding: 0.55rem 0.7rem;
                cursor: pointer;
                box-shadow: 0 8px 20px rgba(47, 129, 247, 0.35);
              ">📋 Copy JSON</button>
            </div>
            <script>
            const jsonText = {json.dumps(result_json_text)};
            const copyBtn = document.getElementById("copyJsonBtn");

            function showCenterNoticeInParent(message, isSuccess) {{
              try {{
                const parentDoc = window.parent && window.parent.document ? window.parent.document : document;
                const oldNotice = parentDoc.getElementById("copy-json-status-notice");
                if (oldNotice) oldNotice.remove();

                const notice = parentDoc.createElement("div");
                notice.id = "copy-json-status-notice";
                notice.textContent = message;
                notice.style.position = "fixed";
                notice.style.top = "50%";
                notice.style.left = "50%";
                notice.style.transform = "translate(-50%, -50%)";
                notice.style.backgroundColor = isSuccess ? "rgba(22, 101, 52, 0.95)" : "rgba(127, 29, 29, 0.95)";
                notice.style.color = "#ffffff";
                notice.style.border = isSuccess ? "1px solid #22c55e" : "1px solid #ef4444";
                notice.style.borderRadius = "8px";
                notice.style.padding = "0.8rem 1.2rem";
                notice.style.fontWeight = "700";
                notice.style.fontSize = "1.2rem";
                notice.style.zIndex = "9999";
                notice.style.boxShadow = "0 8px 24px rgba(1, 4, 9, 0.6)";
                notice.style.opacity = "0";
                notice.style.transition = "opacity 120ms ease";

                parentDoc.body.appendChild(notice);
                requestAnimationFrame(() => {{ notice.style.opacity = "1"; }});

                setTimeout(() => {{
                  notice.style.opacity = "0";
                  setTimeout(() => notice.remove(), 180);
                }}, 1800);
              }} catch (e) {{
                console.error("Unable to show copy status notice:", e);
              }}
            }}

            async function copyJsonToClipboard() {{
              let copied = false;
              let errDetail = "";

              if (navigator.clipboard && navigator.clipboard.writeText) {{
                try {{
                  await navigator.clipboard.writeText(jsonText);
                  copied = true;
                }} catch (err) {{
                  errDetail = err && err.message ? err.message : String(err);
                }}
              }}

              if (!copied) {{
                try {{
                  const ta = document.createElement("textarea");
                  ta.value = jsonText;
                  ta.setAttribute("readonly", "");
                  ta.style.position = "fixed";
                  ta.style.left = "-9999px";
                  document.body.appendChild(ta);
                  ta.focus();
                  ta.select();
                  copied = document.execCommand("copy");
                  document.body.removeChild(ta);
                }} catch (err) {{
                  if (!errDetail) {{
                    errDetail = err && err.message ? err.message : String(err);
                  }}
                }}
              }}

              if (copied) {{
                showCenterNoticeInParent("✅ JSON copied to clipboard.", true);
              }} else {{
                const suffix = errDetail ? `: ${{errDetail}}` : "";
                showCenterNoticeInParent(`❌ Copy failed${{suffix}}`, false);
              }}
            }}

            copyBtn.addEventListener("click", copyJsonToClipboard);
            </script>
            """,
            height=48,
        )
    st.json(result_json, expanded=True)

# Footer
st.divider()
st.caption("Wiwynn Corporation | Internal Tool | Developed by Dixon Chu")