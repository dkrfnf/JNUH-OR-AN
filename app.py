import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

# --- 설정 ---
ZONE_A = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
ZONE_B = ["B1", "B2", "B3", "B4", "C2", "Angio", "회복실"]
ALL_ROOMS = ZONE_A + ZONE_B
# 파일명은 kst로 통일
DATA_FILE = 'or_status_kst.csv' 
NOTICE_FILE = 'notice.txt'
OP_STATUS = ["▶ 수술", "Ⅱ 대기", "■ 종료"]

# (streamlit_autorefresh는 UI 렌더링 시작 시 호출됨)

# --- 보조 함수 ---
def get_korean_time():
    """한국 시간(KST)을 HH:MM 형식으로 반환"""
    kst_now = datetime.utcnow() + timedelta(hours=9)
    return kst_now.strftime("%H:%M")

def get_room_index(df, room_name):
    """방 이름으로 DataFrame 인덱스 찾기"""
    return df[df['Room'] == room_name].index[0]

# --- 공지사항 파일 관리 ---
def load_notice():
    if not os.path.exists(NOTICE_FILE): return ""
    try:
        with open(NOTICE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except: return ""

def save_notice_file(text):
    with open(NOTICE_FILE, "w", encoding="utf-8") as f:
        f.write(text)

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
        # 파일이 손상되었을 경우 강제 삭제 및 재생성
        if os.path.exists(DATA_FILE): os.remove(DATA_FILE)
        return load_data()

    if len(df) != len(ALL_ROOMS) or df.loc[0, 'Status'] not in OP_STATUS:
        os.remove(DATA_FILE)
        return load_data()
    return df.fillna('')

def save_data(df):
    df.to_csv(DATA_FILE, index=False, encoding='utf-8')

# --- 액션 함수 (콜백 포함) ---

# 1. 모든 데이터 업데이트/저장 (상태, 교대자)
def update_data_callback(room_name, col_name, session_key):
    """상태 변경 또는 교대자 이름 입력 시 호출되어 데이터를 저장합니다."""
    
    # 텍스트 입력은 session_key에서 값을 가져옴, selectbox는 새로운 값(new_value)이 없음
    new_value = st.session_state.get(session_key)
    
    df = load_data()
    idx = get_room_index(df, room_name)
    data_changed = False
    
    # Selectbox (Status) 처리
    if col_name == 'Status':
        if df.loc[idx, 'Status'] != new_value:
            df.loc[idx, 'Status'] = new_value
            df.loc[idx, 'Last_Update'] = get_korean_time()
            data_changed = True
    
    # Text Input (Shift Names) 처리
    elif df.loc[idx, col_name] != new_value:
        df.loc[idx, col_name] = new_value
        # 교대자 이름만 바뀌었을 경우, 시간 업데이트는 하지 않음 (상태 변경만 시간 기록)
        # df.loc[idx, 'Last_Update'] = get_korean_time() 
        data_changed = True

    if data_changed:
        save_data(df)
        # 상태가 변경되었을 때만 강제 새로고침하여 즉시 반영 (텍스트 입력은 on_change로 자동 반영)
        if col_name == 'Status':
            st.rerun()

# 2. 공지사항 업데이트
def update_notice_callback():
    save_notice_file(st.session_state["notice_input"])

# 3. 전체 초기화
def reset_all_data():
    df = load_data()
    now_time = get_korean_time()
    
    df['Status'] = '▶ 수술'
    df['Morning'] = ''
    df['Lunch'] = ''
    df['Afternoon'] = ''
    df['Last_Update'] = now_time
    save_data(df)

    save_notice_file("모든 수술방 상태가 초기화되었습니다.") # 공지사항 초기화 메시지
    st.session_state["notice_input"] = "모든 수술방 상태가 초기화되었습니다."
    
    # 세션 상태 강제 초기화
    for room in ALL_ROOMS:
        if f"st_{room}" in st.session_state: st.session_state[f"st_{room}"] = "▶ 수술"
        if f"m_{room}" in st.session_state: st.session_state[f"m_{room}"] = ""
        if f"l_{room}" in st.session_state: st.session_state[f"l_{room}"] = ""
        if f"a_{room}" in st.session_state: st.session_state[f"a_{room}"] = ""

    st.rerun()

# 4. UI 렌더링

def render_final_card(room_name, df):
    row = df[df['Room'] == room_name].iloc[0]
    status = row['Status']

    # 색상 로직
    if "수술" in status:
        bg_color, icon_color, text_color = "#E0F2FE", "#0EA5E9", "#0EA5E9"
    elif "대기" in status:
        bg_color, icon_color, text_color = "#FFF3E0", "#EF6C00", "#EF6C00"
    else: 
        bg_color, icon_color, text_color = "#D6D6D6", "#424242", "#424242" # 종료 색상 조정

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

        # 교대자 입력 필드
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

# CSS는 그대로 유지

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

# --- 상단 헤더 ---
c_head1, c_head2 = st.columns([5, 1])
with c_head1:
    st.markdown("### 🩺 JNUH OR Dashboard")
with c_head2:
    if st.button("⟳ 하루 시작", use_container_width=True):
        reset_all_data()

st.markdown("---")

# 공지사항 섹션
st.text_area("📢 공지사항", value=load_notice(), key="notice_input", placeholder="📢 공지사항...", on_change=update_notice_callback)
st.markdown("---") # 공지사항과 현황판 구분

# 데이터 로드 및 초기 동기화
df = load_data()

# 구역별 렌더링 실행
left_col, right_col = st.columns(2, gap="small")
render_zone(left_col, "A 구역", ZONE_A, df)
render_zone(right_col, "B / C / 기타", ZONE_B, df)
