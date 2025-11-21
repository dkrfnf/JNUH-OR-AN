import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from streamlit_autorefresh import st_autorefresh

# --- 설정 ---
ZONE_A = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
ZONE_B = ["B1", "B2", "B3", "B4", "C2", "Angio", "회복실"]
ALL_ROOMS = ZONE_A + ZONE_B
DATA_FILE = 'or_status_kst.csv' 
NOTICE_FILE = 'notice.txt'
OP_STATUS = ["▶ 수술", "Ⅱ 대기", "■ 종료"]

# 2초 자동 새로고침
st_autorefresh(interval=2000, key="datarefresh")

# --- 보조 함수 ---
def get_korean_time():
    """라이브러리 없이 한국 시간 구하기"""
    utc_now = datetime.utcnow()
    kst_now = utc_now + timedelta(hours=9)
    return kst_now.strftime("%H:%M")

def get_room_index(df, room_name):
    return df[df['Room'] == room_name].index[0]

# --- 공지사항 관리 ---
def load_notice():
    if not os.path.exists(NOTICE_FILE): return ""
    try:
        with open(NOTICE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except: return ""

def save_notice_file(text):
    with open(NOTICE_FILE, "w", encoding="utf-8") as f:
        f.write(text)

def update_notice_callback():
    save_notice_file(st.session_state["notice_input"])

# --- 데이터 관리 ---
def load_data():
    try:
        if not os.path.exists(DATA_FILE):
            now_time = get_korean_time()
            data = {
                'Room': ALL_ROOMS, 'Status': ['▶ 수술'] * len(ALL_ROOMS), 
                'Last_Update': [now_time] * len(ALL_ROOMS),
                'Morning': [''] * len(ALL_ROOMS), 'Lunch': [''] * len(ALL_ROOMS), 'Afternoon': [''] * len(ALL_ROOMS)
            }
            df = pd.DataFrame(data)
            df.to_csv(DATA_FILE, index=False, encoding='utf-8')
            return df
        df = pd.read_csv(DATA_FILE, encoding='utf-8')
    except Exception:
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        return load_data()

    if len(df) != len(ALL_ROOMS) or df.loc[0, 'Status'] not in OP_STATUS:
        os.remove(DATA_FILE)
        return load_data()
    return df.fillna('')

def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding='utf-8')

# ★ 핵심: 서버 데이터 -> 내 화면 강제 동기화
def sync_session_state(df):
    # 1. 공지사항 동기화
    server_notice = load_notice()
    if "notice_input" not in st.session_state or st.session_state["notice_input"] != server_notice:
        # 내가 입력 중이 아닐 때만 업데이트 (포커스 문제 방지 위해 단순 비교)
        st.session_state["notice_input"] = server_notice

    # 2. 수술방 데이터 동기화
    for index, row in df.iterrows():
        room = row['Room']
        
        # 상태 동기화
        key_status = f"st_{room}"
        if key_status in st.session_state and st.session_state[key_status] != row['Status']:
            st.session_state[key_status] = row['Status']
            
        # 입력값 동기화
        for col in ['Morning', 'Lunch', 'Afternoon']:
            key_input = f"{col[0].lower()}_{room}" # 예: m_A1
            if key_input in st.session_state and st.session_state[key_input] != row[col]:
                st.session_state[key_input] = row[col]

# --- 액션 함수 (콜백 방식) ---
def reset_all_data():
    df = load_data()
    now_time = get_korean_time()
    df['Status'] = '▶ 수술'
    df['Morning'] = ''
    df['Lunch'] = ''
    df['Afternoon'] = ''
    df['Last_Update'] = now_time
    save_data(df)
    
    save_notice_file("")
    st.session_state["notice_input"] = ""
    sync_session_state(df)
    st.rerun()

# 통합 업데이트 콜백
def update_data_callback(room_name, col_name, session_key):
    new_value = st.session_state.get(session_key)
    
    if new_value is not None:
        df = load_data()
        idx = get_room_index(df, room_name)
        
        if df.loc[idx, col_name] != new_value:
            df.loc[idx, col_name] = new_value
            if col_name == 'Status':
                df.loc[idx, 'Last_Update'] = get_korean_time()
            save_data(df)

# --- UI 렌더링 ---
def render_final_card(room_name, df):
    row = df[df['Room'] == room_name].iloc[0]
    status = row['Status']

    if "수술" in status:
        bg_color, icon_color, text_color = "#E0F2FE", "#0EA5E9", "#0EA5E9"
    elif "대기" in status:
        bg_color, icon_color, text_color = "#FFF3E0", "#EF6C00", "#EF6C00"
    else: 
        bg_color, icon_color, text_color = "#F5F5F5", "#616161", "#424242"

    current_icon = status.split(" ")[0] 

    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"""
                <div style='
                    width: 45%; font-size: 1.2rem; font-weight:bold; color:{text_color};
                    background-color:{bg_color}; padding: 4px 0px; border-radius: 6px;
                    text-align: center; display: block; margin-top: 1px;'>
                    <span style='color:{icon_color}; margin-right: 5px;'>{current_icon}</span>{room_name}
                </div>
                """, unsafe_allow_html=True)
        with c2:
            key_status = f"st_{room_name}"
            st.selectbox(
                "상태", OP_STATUS, key=key_status,
                index=OP_STATUS.index(status) if status in OP_STATUS else 0,
                label_visibility="collapsed",
                on_change=update_data_callback, args=(room_name, 'Status', key_status)
            )

        s1, s2, s3 = st.columns(3)
        key_m, key_l, key_a = f"m_{room_name}", f"l_{room_name}", f"a_{room_name}"
        
        s1.text_input("오전", key=key_m, placeholder="", label_visibility="collapsed", on_change=update_data_callback, args=(room_name, 'Morning', key_m))
        s2.text_input("점심", key=key_l, placeholder="", label_visibility="collapsed", on_change=update_data_callback, args=(room_name, 'Lunch', key_l))
        s3.text_input("오후", key=key_a, placeholder="", label_visibility="collapsed", on_change=update_data_callback, args=(room_name, 'Afternoon', key_a))

        st.markdown(f"<p style='text-align: right; font-size: 10px; color: #888; margin-top: 2px; margin-bottom: 0;'>최종 업데이트: **{row['Last_Update']}**</p>", unsafe_allow_html=True)

def render_zone(col, title, zone_list, df):
    with col:
        st.markdown(f"#### {title}")
        for room in zone_list:
            render_final_card(room, df)

# --- 메인 실행 ---
st.set_page_config(page_title="JNUH OR", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 3rem; padding-bottom: 5rem; } /* 제목 여백 확보 */
    div[data-testid="stVerticalBlock"] > div { gap: 0rem; }
    hr { margin-top: 0.2rem !important; margin-bottom: 0.5rem !important; }
    h3, h4 { margin-bottom: 0rem !important; padding-top: 0rem !important; }

    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        padding-top: 0px; padding-bottom: 0px; padding-left: 5px;
        height: 32px; min-height: 32px; font-size: 15px; display: flex; align-items: center; border-color: #E0E0E0;
    }
    div[data-testid="stTextInput"] div[data-baseweb="input"] {
        background-color: #FFFFFF !important; border: 1px solid #CCCCCC !important;
        border-radius: 4px; padding-top: 0px; padding-bottom: 0px; height: 32px; min-height: 32px;
    }
    div[data-testid="stTextInput"] input {
        background-color: #FFFFFF !important; color: #000000 !important; font-size: 14px;
    }
    div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within { border: 1px solid #2196F3 !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 10px !important; }
    button p { font-size: 14px; font-weight: bold; }

    div[data-testid="stVerticalBlock"] > div > [data-testid="stVerticalBlock"] { margin-top: -10px !important; }
    @media (max-width: 600px) {
        div[data-testid="stVerticalBlockBorderWrapper"] { max-width: 90vw; margin: auto; }
    }
    
    /* 공지사항 스타일 */
    div[data-testid="stTextArea"] textarea {
        background-color: #FFFDE7; border: 1px solid #FFECB3; font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# 1. 상단 제목
st.markdown("### 🩺 JNUH OR Dashboard")

# 2. 공지사항 (높이 100px로 설정하여 세로로 2~3줄 확보)
current_notice = load_notice()
st.text_area("공지사항", value=current_notice, height=100, key="notice_input", label_visibility="collapsed", placeholder="📢 공지사항을 입력하세요...", on_change=update_notice_callback)

st.markdown("---")

# 3. 데이터 로드 및 강제 동기화
df = load_data()
sync_session_state(df) # ★ 호환성의 핵심: 화면 강제 동기화

# 4. 구역 렌더링
left_col, right_col = st.columns(2, gap="small")
render_zone(left_col, "A 구역", ZONE_A, df)
render_zone(right_col, "B / C / 기타", ZONE_B, df)

# 5. 하단 리셋 버튼
st.markdown("") 
st.markdown("---")
if st.button("⟳ 하루 시작 (전체 초기화)", type="primary", use_container_width=True):
    reset_all_data()
