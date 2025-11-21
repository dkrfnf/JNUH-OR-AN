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

# 한국 시간
def get_korean_time():
    utc_now = datetime.utcnow()
    kst_now = utc_now + timedelta(hours=9)
    return kst_now.strftime("%H:%M")

def get_room_index(df, room_name):
    return df[df['Room'] == room_name].index[0]

# --- 공지사항 관리 ---
def load_notice():
    if not os.path.exists(NOTICE_FILE):
        return ""
    try:
        with open(NOTICE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

def save_notice_file(text):
    with open(NOTICE_FILE, "w", encoding="utf-8") as f:
        f.write(text)

def update_notice_callback():
    new_text = st.session_state["notice_input"]
    save_notice_file(new_text)

# --- 데이터 관리 ---
def load_data():
    try:
        if not os.path.exists(DATA_FILE):
            now_time = get_korean_time()
            data = {
                'Room': ALL_ROOMS,
                'Status': ['▶ 수술'] * len(ALL_ROOMS),
                'Last_Update': [now_time] * len(ALL_ROOMS),
                'Morning': [''] * len(ALL_ROOMS),
                'Lunch': [''] * len(ALL_ROOMS),
                'Afternoon': [''] * len(ALL_ROOMS)
            }
            df = pd.DataFrame(data)
            df.to_csv(DATA_FILE, index=False, encoding='utf-8')
            return df
        df = pd.read_csv(DATA_FILE, encoding='utf-8')
    except Exception:
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            return load_data()
        return pd.DataFrame()

    if len(df) != len(ALL_ROOMS) or df.loc[0, 'Status'] not in OP_STATUS:
        os.remove(DATA_FILE)
        return load_data()
    return df.fillna('')

def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding='utf-8')

# ★ 서버 데이터 -> 내 화면 강제 동기화 (공지사항 포함)
def sync_session_state(df):
    # 1. 공지사항 동기화 (이게 있어야 PC-모바일 호환됨)
    server_notice = load_notice()
    if "notice_input" not in st.session_state or st.session_state["notice_input"] != server_notice:
        st.session_state["notice_input"] = server_notice

    # 2. 수술방 데이터 동기화
    for index, row in df.iterrows():
        room = row['Room']
        
        key_status = f"st_{room}"
        if key_status not in st.session_state or st.session_state[key_status] != row['Status']:
            st.session_state[key_status] = row['Status']
            
        key_m = f"m_{room}"
        if key_m not in st.session_state or st.session_state[key_m] != row['Morning']:
            st.session_state[key_m] = row['Morning']
        key_l = f"l_{room}"
        if key_l not in st.session_state or st.session_state[key_l] != row['Lunch']:
            st.session_state[key_l] = row['Lunch']
        key_a = f"a_{room}"
        if key_a not in st.session_state or st.session_state[key_a] != row['Afternoon']:
            st.session_state[key_a] = row['Afternoon']

# --- 액션 함수 ---
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

def update_status(room_name, new_status):
    df = load_data()
    idx = get_room_index(df, room_name)
    if df.loc[idx, 'Status'] != new_status:
        df.loc[idx, 'Status'] = new_status
        df.loc[idx, 'Last_Update'] = get_korean_time()
        save_data(df)
        st.rerun()

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

def manual_save(room_name):
    st.toast(f"✅ {room_name} 저장 완료!", icon="💾")

# --- UI 렌더링 ---
def render_final_card(room_name, df):
    row = df[df['Room'] == room_name].iloc[0]
    status = row['Status']

    if "수술" in status:
        bg_color = "#E0F2FE"     
        icon_color = "#0EA5E9"   
        text_color = "#0EA5E9"   
    elif "대기" in status:
        bg_color = "#FFF3E0"     
        icon_color = "#EF6C00"   
        text_color = "#EF6C00"   
    else: 
        bg_color = "#D6D6D6"     
        icon_color = "#000000"   
        text_color = "#000000"   

    current_icon = status.split(" ")[0] 

    with st.container(border=True):
        # ★ 상단 3분할: [방번호(2)] [저장버튼(0.8)] [상태선택(1.2)]
        c1, c2, c3 = st.columns([1.8, 0.8, 1.4])
        
        # 1. 방 번호
        with c1:
            st.markdown(f"""
                <div style='
                    width: 100%; 
                    font-size: 1.2rem;
                    font-weight:bold;
                    color:{text_color};
                    background-color:{bg_color};
                    padding: 4px 0px; 
                    border-radius: 6px;
                    text-align: center;
                    display: block;
                    margin-top: 1px;
                '>
                    <span style='color:{icon_color}; margin-right: 5px;'>{current_icon}</span>{room_name}
                </div>
                """, unsafe_allow_html=True)
        
        # 2. 저장 버튼 (가운데 배치)
        with c2:
            st.button("💾", key=f"sv_{room_name}", on_click=manual_save, args=(room_name,), use_container_width=True)

        # 3. 상태 선택
        with c3:
            key_status = f"st_{room_name}"
            st.selectbox(
                "상태", OP_STATUS,
                key=key_status,
                index=OP_STATUS.index(status) if status in OP_STATUS else 0,
                label_visibility="collapsed",
                on_change=update_data_callback, 
                args=(room_name, 'Status', key_status)
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
    .block-container { padding: 1rem; }
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
    div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within { border: 1px solid #2196F3 !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 10px !important; }
    
    /* 일반 버튼 */
    button p { font-size: 14px; font-weight: bold; }
    
    /* 저장 버튼(중앙) 스타일 최적화 */
    div[data-testid="stButton"] button {
        min-height: 0px !important;
        height: 32px !important; /* 높이를 옆의 칸들과 동일하게 */
        padding: 0px !important;
        margin: 0px !important;
        border: 1px solid #E0E0E0;
    }

    div[data-testid="stVerticalBlock"] > div > [data-testid="stVerticalBlock"] { margin-top: -10px !important; }
    @media (max-width: 600px) {
        div[data-testid="stVerticalBlockBorderWrapper"] { max-width: 90vw; margin: auto; }
    }
    
    div[data-testid="stTextArea"] textarea {
        background-color: #FFF8E1; border: 1px solid #FFECB3; font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# 1. 상단 영역
c_title, c_notice = st.columns([1, 2])
with c_title:
    st.markdown("### 🩺 JNUH OR Dashboard")
with c_notice:
    current_notice = load_notice()
    st.text_area("📢 공지사항", value=current_notice, height=68, key="notice_input", label_visibility="collapsed", placeholder="📢 공지사항...", on_change=update_notice_callback)

st.markdown("---")

df = load_data()
sync_session_state(df) # ★ 공지사항 및 데이터 강제 동기화 실행

# 2. 메인 현황판
left_col, right_col = st.columns(2, gap="small")
render_zone(left_col, "A 구역", ZONE_A, df)
render_zone(right_col, "B / C / 기타", ZONE_B, df)

# 3. 하단 리셋
st.markdown("---")
st.caption("⚠️ 아래 버튼을 누르면 모든 상태와 이름이 초기화됩니다.")
if st.button("⟳ 하루 시작 (전체 초기화)", type="primary", use_container_width=True):
    reset_all_data()
