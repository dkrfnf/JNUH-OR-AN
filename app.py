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
    """한국 시간(KST)을 HH:MM 형식으로 반환"""
    kst_now = datetime.utcnow() + timedelta(hours=9)
    return kst_now.strftime("%H:%M")

def get_room_index(df, room_name):
    return df[df['Room'] == room_name].index[0]

# --- 공지사항 함수 ---
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

# --- 액션 함수 ---
def update_data_callback(room_name, col_name, session_key):
    new_value = st.session_state.get(session_key)
    df = load_data()
    idx = get_room_index(df, room_name)
    data_changed = False
    
    if col_name == 'Status':
        if df.loc[idx, 'Status'] != new_value:
            df.loc[idx, 'Status'] = new_value
            df.loc[idx, 'Last_Update'] = get_korean_time()
            data_changed = True
    elif df.loc[idx, col_name] != new_value:
        df.loc[idx, col_name] = new_value
        data_changed = True

    if data_changed:
        save_data(df)
        if col_name == 'Status': st.rerun()

def reset_all_data():
    df = load_data()
    now_time = get_korean_time()
    df['Status'] = '▶ 수술'
    df['Morning'] = ''
    df['Lunch'] = ''
    df['Afternoon'] = ''
    df['Last_Update'] = now_time
    save_data(df)
    
    save_notice_file("") # 공지사항도 초기화
    st.session_state["notice_input"] = ""
    
    for room in ALL_ROOMS:
        if f"st_{room}" in st.session_state: st.session_state[f"st_{room}"] = "▶ 수술"
        if f"m_{room}" in st.session_state: st.session_state[f"m_{room}"] = ""
        if f"l_{room}" in st.session_state: st.session_state[f"l_{room}"] = ""
        if f"a_{room}" in st.session_state: st.session_state[f"a_{room}"] = ""
    st.rerun()

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
    key_status, key_m, key_l, key_a = f"st_{room_name}", f"m_{room_name}", f"l_{room_name}", f"a_{room_name}"

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
            st.selectbox(
                "상태", OP_STATUS, key=key_status,
                index=OP_STATUS.index(status) if status in OP_STATUS else 0,
                label_visibility="collapsed", on_change=update_data_callback, args=(room_name, 'Status', key_status)
            )

        s1, s2, s3 = st.columns(3)
        s1.text_input("오전", value=row['Morning'], key=key_m, placeholder="", label_visibility="collapsed", on_change=update_data_callback, args=(room_name, 'Morning', key_m))
        s2.text_input("점심", value=row['Lunch'], key=key_l, placeholder="", label_visibility="collapsed", on_change=update_data_callback, args=(room_name, 'Lunch', key_l))
        s3.text_input("오후", value=row['Afternoon'], key=key_a, placeholder="", label_visibility="collapsed", on_change=update_data_callback, args=(room_name, 'Afternoon', key_a))

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
    /* ★ 제목 여백 확보: 위쪽 패딩을 3.5rem(약 50px) 주어서 내림 */
    .block-container { padding-top: 3.5rem; padding-left: 1rem; padding-right: 1rem; padding-bottom: 5rem; }
    
    div[data-testid="stVerticalBlock"] > div { gap: 0rem; }
    hr { margin-top: 0.2rem !important; margin-bottom: 0.5rem !important; }
    h3, h4 { margin-bottom: 0rem !important; padding-top: 0rem !important; }

    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        padding-top: 0px; padding-bottom: 0px; padding-left: 5px;
        height: 32px; min-height: 32px;
        font-size: 15px; display: flex; align-items: center;
        border-color: #E0E0E0;
    }
    
    div[data-testid="stTextInput"] div[data-baseweb="input"] {
        background-color: #FFFFFF !important; 
        border: 1px solid #CCCCCC !important;
        border-radius: 4px;
        padding-top: 0px; padding-bottom: 0px;
        height: 32px; min-height: 32px;
    }
    div[data-testid="stTextInput"] input {
        background-color: #FFFFFF !important; color: #000000 !important; font-size: 14px;
    }
    div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
        border: 1px solid #2196F3 !important;
    }
    
    div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 10px !important; }
    button p { font-size: 14px; font-weight: bold; }

    div[data-testid="stVerticalBlock"] > div > [data-testid="stVerticalBlock"] {
        margin-top: -10px !important;
    }
    @media (max-width: 600px) {
        div[data-testid="stVerticalBlockBorderWrapper"] { max-width: 90vw; margin: auto; }
    }
    
    /* 공지사항 스타일 */
    div[data-testid="stTextArea"] textarea {
        background-color: #FFFDE7; /* 연한 노란색 */
        border: 1px solid #FFF59D;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# 1. 상단 제목 & 공지사항 (리셋 버튼 제거됨)
st.markdown("### 🩺 JNUH OR Dashboard")

current_notice = load_notice()
st.text_area("공지사항", value=current_notice, height=68, key="notice_input", label_visibility="collapsed", placeholder="📢 공지사항을 입력하세요...", on_change=update_notice_callback)

st.markdown("---")

# 2. 현황판 렌더링
df = load_data()
left_col, right_col = st.columns(2, gap="small")
render_zone(left_col, "A 구역", ZONE_A, df)
render_zone(right_col, "B / C / 기타", ZONE_B, df)

# 3. 하단 리셋 버튼 (맨 아래로 이동)
st.markdown("") 
st.markdown("") 
st.markdown("---")
# type="primary"로 설정하여 빨간색 버튼으로 표시 (주의)
if st.button("⟳ 하루 시작 (전체 초기화)", type="primary", use_container_width=True):
    reset_all_data()
