import streamlit as st
import pandas as pd
from datetime import datetime
import os
from streamlit_autorefresh import st_autorefresh

# --- 설정 ---
ZONE_A = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
ZONE_B = ["B1", "B2", "B3", "B4", "C2", "Angio", "회복실"]
ALL_ROOMS = ZONE_A + ZONE_B
DATA_FILE = 'or_status_final.csv'
OP_STATUS = ["▶ 수술", "Ⅱ 대기", "■ 종료"]

# 2초 자동 새로고침
st_autorefresh(interval=2000, key="datarefresh")

def get_current_time():
    """서버의 현재 시간을 HH:MM 형식으로 반환"""
    return datetime.now().strftime("%H:%M")

def get_room_index(df, room_name):
    """방 이름에 해당하는 DataFrame 인덱스 반환"""
    return df[df['Room'] == room_name].index[0]

# --- 데이터 로드 및 저장 함수 (이전 버전과 동일) ---
def load_data():
    try:
        if not os.path.exists(DATA_FILE):
            now_time = get_current_time()
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
        
    except UnicodeDecodeError:
        print("ALERT: Detected corrupt CSV file. Forcing data reset.")
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            return load_data()
        raise Exception("Critical: Could not load data even after deleting corrupt file.") 

    if len(df) != len(ALL_ROOMS) or df.loc[0, 'Status'] not in OP_STATUS:
        os.remove(DATA_FILE)
        return load_data()
        
    return df.fillna('')

def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding='utf-8')

# --- 액션 함수 ---

def reset_all_data():
    df = load_data()
    now_time = get_current_time()
    
    df['Status'] = '▶ 수술'
    df['Morning'] = ''
    df['Lunch'] = ''
    df['Afternoon'] = ''
    df['Last_Update'] = now_time
    save_data(df)

    for room in ALL_ROOMS:
        # Session state 초기화 코드 (생략)
        if f"st_{room}" in st.session_state: st.session_state[f"st_{room}"] = "▶ 수술"
        if f"m_{room}" in st.session_state: st.session_state[f"m_{room}"] = ""
        if f"l_{room}" in st.session_state: st.session_state[f"l_{room}"] = ""
        if f"a_{room}" in st.session_state: st.session_state[f"a_{room}"] = ""

    st.rerun()

def update_status(room_name, new_status):
    df = load_data()
    idx = get_room_index(df, room_name)
    
    if df.loc[idx, 'Status'] != new_status:
        df.loc[idx, 'Status'] = new_status
        df.loc[idx, 'Last_Update'] = get_current_time()
        save_data(df)
        st.rerun()

# ★ 수정: 이름을 Session State에서 직접 가져와 저장하도록 콜백 구조 변경
def update_shift_callback(room_name, col_name, session_key):
    # Session State에서 현재 입력된 값 가져오기
    new_value = st.session_state.get(session_key) 
    
    if new_value is not None:
        df = load_data()
        idx = get_room_index(df, room_name)
        
        # 값이 변경되었을 때만 저장
        if df.loc[idx, col_name] != new_value:
            df.loc[idx, col_name] = new_value
            save_data(df)
            # 상태 변경과 달리, 텍스트 입력은 별도의 st.rerun()을 하지 않습니다.

# --- UI 렌더링 함수 ---

def render_final_card(room_name, df):
    row = df[df['Room'] == room_name].iloc[0]
    status = row['Status']
    # ... (색상 로직은 생략) ...
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
            if new_status != status: update_status(room_name, new_status) # 상태 변경 시 강제 리런

        s1, s2, s3 = st.columns(3)
        
        # ★ 수정: on_change 콜백 추가 (이름 입력 완료 시 즉시 저장)
        key_m = f"m_{room_name}"
        key_l = f"l_{room_name}"
        key_a = f"a_{room_name}"
        
        s1.text_input("오전", value=row['Morning'], key=key_m, placeholder="", label_visibility="collapsed",
                      on_change=update_shift_callback, args=(room_name, 'Morning', key_m))
        s2.text_input("점심", value=row['Lunch'], key=key_l, placeholder="", label_visibility="collapsed",
                      on_change=update_shift_callback, args=(room_name, 'Lunch', key_l))
        s3.text_input("오후", value=row['Afternoon'], key=key_a, placeholder="", label_visibility="collapsed",
                      on_change=update_shift_callback, args=(room_name, 'Afternoon', key_a))
        
        # 기존의 if 문을 모두 제거함 (on_change 콜백이 대신 처리)

        st.markdown(f"<p style='text-align: right; font-size: 10px; color: #888; margin-top: 5px; margin-bottom: 0;'>최종 업데이트: **{row['Last_Update']}**</p>", unsafe_allow_html=True)


def render_zone(col, title, zone_list, df):
    with col:
        st.markdown(f"#### {title}")
        for room in zone_list:
            render_final_card(room, df)

# --- 메인 실행 (생략: CSS 및 헤더 부분 동일) ---

st.set_page_config(page_title="JNUH OR", layout="wide")

st.markdown("""
    <style>
    /* ... (CSS 코드는 이전과 동일) ... */
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
        height: 35px; min-height: 35px;
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


c_head1, c_head2 = st.columns([5, 1])
with c_head1:
    st.markdown("### 🩺 JNUH OR Dashboard")
with c_head2:
    if st.button("⟳ 하루 시작", use_container_width=True):
        reset_all_data()

st.markdown("---")

df = load_data()

left_col, right_col = st.columns(2, gap="small")
render_zone(left_col, "A 구역", ZONE_A, df)
render_zone(right_col, "B / C / 기타", ZONE_B, df)
