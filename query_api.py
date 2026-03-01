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

# API endpoint (single source of truth for UI + request call)
API_URL = "https://apim.wiwynn.com/nifi/prd/api/cerberus/v1/sn_info"

def reset_input_and_response():
    st.session_state["sn_text_input"] = ""
    st.session_state["last_result_json"] = None

# --- CSS styling ---
st.markdown("""
    <style>
    /* Global dark theme */
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    
    /* Text area styling: dark background with light text */
    div[data-baseweb="textarea"] textarea {
        color: #ffffff !important;
        background-color: #1e2128 !important;
        border: 1px solid #30363d !important;
        font-family: 'Source Code Pro', monospace !important;
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
        color: #ffffff;
    }
    .dev-tag {
        font-size: 1.1rem;
        color: #58a6ff;
        font-weight: 600;
        margin-top: 0.5rem;
        text-align: left;
    }

    /* Button style */
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
    .stButton>button[kind="primary"] {
        font-size: 1.15rem;
        font-weight: 700;
        padding: 0.9rem 1rem;
    }

    /* Sidebar dark mode */
    section[data-testid="stSidebar"] {
        background-color: #010409 !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] label p,
    section[data-testid="stSidebar"] div[data-testid="stSelectbox"] label span {
        font-size: 1.35rem !important;
        font-weight: 700 !important;
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
    st.success("API Gateway: Online")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d')}")
    st.caption("Current API endpoint")
    st.code(API_URL, language=None)

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
    
    if not sn_list:
        st.warning("⚠️ Please enter at least one serial number.")
    else:
        payload = {"SITE": site, "TYPE": selected_type, "SN": sn_list}
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
                background-color: #21262d;
                color: #ffffff;
                border: 1px solid #30363d;
                border-radius: 6px;
                font-size: 0.95rem;
                font-weight: 600;
                padding: 0.55rem 0.7rem;
                cursor: pointer;
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
    st.json(result_json)

# Footer
st.divider()
st.caption("Wiwynn Corporation | Internal Tool | Developed by Dixon Chu")