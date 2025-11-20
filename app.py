import streamlit as st
import pandas as pd
from datetime import datetime
import os
from streamlit_autorefresh import st_autorefresh

# --- 설정 ---
ZONE_A = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
ZONE_B = ["B1", "B2", "B3", "B4", "C2", "Angio", "회복실"]
ALL_ROOMS = ZONE_A + ZONE_B
# ★ 파일 이름 변경: 이전 데이터와의 충돌 방지를 위해 파일명을 변경함
DATA_FILE = 'or_status_final.csv' 
OP_STATUS = ["▶ 수술", "Ⅱ 대기", "■ 종료"]

# 2초 자동 새로고침
st_autorefresh(interval=2000, key="datarefresh")

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {
            'Room': ALL_ROOMS,
            'Status': ['▶ 수술'] * len(ALL_ROOMS),
            'Last_Update': [datetime.now().strftime("%H:%M")] * len(ALL_ROOMS),
            'Morning': [''] * len(ALL_ROOMS),
            'Lunch': [''] * len(ALL_ROOMS),
            'Afternoon': [''] * len(ALL_ROOMS)
        }
        df = pd.DataFrame(data)
        df.to_csv(DATA_FILE, index=False)
        return df
    # 이 부분은 유지하여, 혹시라도 잘못된 상태값이 들어오면 리셋합니다.
    df = pd.read_csv(DATA_FILE)
    if len(df) != len(ALL_ROOMS) or df.loc[0, 'Status'] not in OP_STATUS:
        os.remove(DATA_FILE)
        return load_data()
    return df.fillna('')

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

def reset_all_data():
    df = load_data()
    df['Status'] = '▶ 수술' 
    df['Morning'] = ''
    df['Lunch'] = ''
    df['Afternoon'] = ''
    df['Last_Update'] = datetime.now().strftime("%H:%M")
    save_data(df)

    for room in ALL_ROOMS:
        if f"st_{room}" in st.session_state: st.session_state[f"st_{room}"] = "▶ 수술"
        if f"m_{room}" in st.session_state: st.session_state[f"m_{room}"] = ""
        if f"l_{room}" in st.session_state: st.session_state[f"l_{room}"] = ""
        if f"a_{room}" in st.session_state: st.session_state[f"a_{room}"] = ""

    st.rerun()

def update_status(room_name, new_status):
    df = load_data()
    idx = df[df['Room'] == room_name].index[0]
    if df.loc[idx, 'Status'] != new_status:
        df.loc[idx, 'Status'] = new_status
        df.loc[idx, 'Last_Update'] = datetime.now().strftime("%H:%M")
        save_data(df)
        st.rerun()

def update_shift(room_name, col, value):
    df = load_data()
    idx = df[df['Room'] == room_name].index[0]
    if df.loc[idx, col] != value:
        df.loc[idx, col] = value
        save_data(df)

# --- UI 디자인 ---
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
        background-color: #FFFFFF !important; 
        color: #000000 !important; 
        font-size: 14px;
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
    </style>
""", unsafe_allow_html=True)

# --- 상단 헤더 ---
c_head1, c_head2 = st.columns([5, 1])
with c_head1:
    st.markdown("### 🩺 JNUH OR Dashboard")
with c_head2:
    if st.button("⟳ 하루 시작", use_container_width=True):
        reset_all_data()

st.markdown("---")

df = load_data()

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
        bg_color = "#F5F5F5"     
        icon_color = "#616161"   
        text_color = "#424242"

    current_icon = status.split(" ")[0] 

    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"""
                <div style='
                    width: 45%; 
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
        with c2:
            new_status = st.selectbox(
                "상태", OP_STATUS,
                key=f"st_{room_name}",
                index=OP_STATUS.index(status),
                label_visibility="collapsed"
            )
            if new_status != status: update_status(room_name, new_status)

        s1, s2, s3 = st.columns(3)
        val_m = s1.text_input("오전", value=row['Morning'], key=f"m_{room_name}", placeholder="", label_visibility="collapsed")
        val_l = s2.text_input("점심", value=row['Lunch'], key=f"l_{room_name}", placeholder="", label_visibility="collapsed")
        val_a = s3.text_input("오후", value=row['Afternoon'], key=f"a_{room_name}", placeholder="", label_visibility="collapsed")

        if val_m != row['Morning']: update_shift(room_name, 'Morning', val_m)
        if val_l != row['Lunch']: update_shift(room_name, 'Lunch', val_l)
        if val_a != row['Afternoon']: update_shift(room_name, 'Afternoon', val_a)

left_col, right_col = st.columns(2, gap="small")

with left_col:
    st.markdown("#### A 구역")
    for room in ZONE_A:
        render_final_card(room, df)

with right_col:
    st.markdown("#### B / C / 기타")
    for room in ZONE_B:
        render_final_card(room, df)