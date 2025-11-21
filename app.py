import streamlit as st
import pandas as pd
from datetime import datetime
import os
from streamlit_autorefresh import st_autorefresh
import pytz

# --- 설정 ---
ZONE_A = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
ZONE_B = ["B1", "B2", "B3", "B4", "C2", "Angio", "회복실"]
ALL_ROOMS = ZONE_A + ZONE_B
DATA_FILE = 'or_status_final.csv' 
OP_STATUS = ["▶ 수술", "Ⅱ 대기", "■ 종료"]
KST = pytz.timezone('Asia/Seoul')

# 2초 자동 새로고침 (가장 먼저 실행)
st_autorefresh(interval=2000, key="datarefresh")

def get_current_time():
    return datetime.now(KST).strftime("%H:%M")

def get_room_index(df, room_name):
    return df[df['Room'] == room_name].index[0]

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
        
    except Exception:
        if os.path.exists(DATA_FILE):
            os.remove(DATA_FILE)
            return load_data()
        return pd.DataFrame() # Fallback

    if len(df) != len(ALL_ROOMS) or df.loc[0, 'Status'] not in OP_STATUS:
        os.remove(DATA_FILE)
        return load_data()
        
    return df.fillna('')

def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding='utf-8')

# ★★★ 핵심 추가: 서버 데이터로 내 화면(Session State) 강제 동기화 ★★★
def sync_session_state(df):
    for index, row in df.iterrows():
        room = row['Room']
        
        # 1. 상태 동기화
        key_status = f"st_{room}"
        if key_status not in st.session_state or st.session_state[key_status] != row['Status']:
            st.session_state[key_status] = row['Status']
            
        # 2. 입력값 동기화 (오전/점심/오후)
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
    now_time = get_current_time()
    
    df['Status'] = '▶ 수술'
    df['Morning'] = ''
    df['Lunch'] = ''
    df['Afternoon'] = ''
    df['Last_Update'] = now_time
    save_data(df)
    # 저장 후 즉시 동기화 호출
    sync_session_state(df)
    st.rerun()

def update_status(room_name, new_status):
    df = load_data()
    idx = get_room_index(df, room_name)
    
    if df.loc[idx, 'Status'] != new_status:
        df.loc[idx, 'Status'] = new_status
        df.loc[idx, 'Last_Update'] = get_current_time()
        save_data(df)
        st.rerun()

def update_shift_callback(room_name, col_name, session_key):
    new_value = st.session_state.get(session_key)
    if new_value is not None:
        df = load_data()
        idx = get_room_index(df, room_name)
        if df.loc[idx, col_name] != new_value:
            df.loc[idx, col_name] = new_value
            save_data(df)

# --- UI 렌더링 함수 ---

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
            # key가 있으면 session_state 값을 우선시하므로, 위에서 sync_session_state로 동기화된 값을 씁니다.
            new_status = st.selectbox(
                "상태", OP_STATUS,
                key=f"st_{room_name}",
                index=OP_STATUS.index(status) if status in OP_STATUS else 0,
                label_visibility="collapsed"
            )
            if new_status != status: update_status(room_name, new_status)

        s1, s2, s3 = st.columns(3)
        
        key_m = f"m_{room_name}"
        key_l = f"l_{room_name}"
        key_a = f"a_{room_name}"
        
        # 입력창 값은 session_state를 통해 관리되므로 value arg는 초기 로딩용입니다.
        s1.text_input("오전", key=key_m, placeholder="", label_visibility="collapsed",
                      on_change=update_shift_callback, args=(room_name, 'Morning', key_m))
        s2.text_input("점심", key=key_l, placeholder="", label_visibility="collapsed",
                      on_change=update_shift_callback, args=(room_name, 'Lunch', key_l))
        s3.text_input("오후", key=key_a, placeholder="", label_visibility="collapsed",
                      on_change=update_shift_callback, args=(room_name, 'Afternoon', key_a))

        st.markdown(f"<p style='text-align: right; font-size: 10px; color: #888; margin-top: 5px; margin-bottom: 0;'>최종 업데이트: **{row['Last_Update']}**</p>", unsafe_allow_html=True)


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

# 1. 데이터 로드
df = load_data()

# 2. ★ 중요: 로드된 데이터로 Session State 강제 동기화 (화면 갱신)
sync_session_state(df)

# 3. 화면 그리기
left_col, right_col = st.columns(2, gap="small")
render_zone(left_col, "A 구역", ZONE_A, df)
render_zone(right_col, "B / C / 기타", ZONE_B, df)
