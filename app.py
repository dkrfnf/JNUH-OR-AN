import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import time
from streamlit_autorefresh import st_autorefresh

# --- 설정 ---
ZONE_A = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
ZONE_B = ["B1", "B2", "B3", "B4", "C2", "외부", "회복실"]
ALL_ROOMS = ZONE_A + ZONE_B
DATA_FILE = 'or_status_kst.csv'
NOTICE_FILE = 'notice.txt'
NOTICE_TIME_FILE = 'notice_time.txt'
RESET_LOG_FILE = 'reset_log.txt'  # 리셋 기록용 파일

# 상태 옵션 정의
OP_STATUS = ["▶ 수술", "Ⅱ 대기", "■ 종료"]
LUNCH_OPTIONS = ["식사-", "식사+"] 

# 2초 자동 새로고침
st_autorefresh(interval=2000, key="datarefresh")

# --- 시간 관련 함수 ---
def get_korean_datetime():
    """한국 시간 datetime 객체 반환"""
    utc_now = datetime.utcnow()
    kst_now = utc_now + timedelta(hours=9)
    return kst_now

def get_korean_time_str():
    """한국 시간 문자열(HH:MM) 반환"""
    return get_korean_datetime().strftime("%H:%M")

def get_room_index(df, room_name):
    return df[df['Room'] == room_name].index[0]

# --- 자동 리셋 로직 (핵심 변경) ---
def load_last_reset_time():
    """마지막 리셋 시간을 datetime 객체로 불러옴"""
    if not os.path.exists(RESET_LOG_FILE):
        return datetime.min # 파일 없으면 아주 옛날 시간 반환
    try:
        with open(RESET_LOG_FILE, "r", encoding="utf-8") as f:
            timestamp_str = f.read().strip()
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except:
        return datetime.min

def save_current_reset_time(dt_obj):
    """현재 리셋 시간을 파일에 저장"""
    try:
        with open(RESET_LOG_FILE, "w", encoding="utf-8") as f:
            f.write(dt_obj.strftime("%Y-%m-%d %H:%M:%S"))
    except: pass

def check_daily_reset():
    """아침 7시 기준으로 리셋이 필요한지 확인하고 실행"""
    now = get_korean_datetime()
    
    # 오늘의 리셋 기준 시간 설정 (오늘 아침 7시)
    target_reset_time = now.replace(hour=7, minute=0, second=0, microsecond=0)
    
    # 만약 현재 시간이 아침 7시 이전(예: 06:30)이라면, 
    # 리셋 기준은 '어제 아침 7시'가 되어야 함 (아직 오늘 리셋 시간이 안 됨)
    if now.hour < 7:
        target_reset_time = target_reset_time - timedelta(days=1)
        
    last_reset = load_last_reset_time()
    
    # 마지막 리셋 기록이 기준 시간보다 이전이면 리셋 실행
    if last_reset < target_reset_time:
        perform_reset(now)

def perform_reset(current_time):
    """실제 데이터 초기화 수행"""
    # 1. 데이터 초기화
    df = pd.DataFrame({
        'Room': ALL_ROOMS,
        'Status': ['▶ 수술'] * len(ALL_ROOMS),
        'Last_Update': [current_time.strftime("%H:%M")] * len(ALL_ROOMS),
        'Morning': [''] * len(ALL_ROOMS),
        'Lunch': ['식사-'] * len(ALL_ROOMS),
        'Afternoon': [''] * len(ALL_ROOMS)
    })
    
    # 2. 파일 저장
    df.to_csv(DATA_FILE, index=False, encoding='utf-8')
    
    # 3. 리셋 시간 기록 (중복 실행 방지)
    save_current_reset_time(current_time)
    
    # 4. 세션 초기화 및 리런
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    
    st.rerun()

# --- 데이터 로드/저장 ---
def load_data():
    for _ in range(5):
        try:
            if not os.path.exists(DATA_FILE):
                # 파일 없으면 초기화 로직 수행
                now = get_korean_datetime()
                perform_reset(now)
                return pd.read_csv(DATA_FILE, encoding='utf-8')
            
            df = pd.read_csv(DATA_FILE, encoding='utf-8')
            current_rooms = df['Room'].tolist()
            if len(df) != len(ALL_ROOMS) or current_rooms != ALL_ROOMS:
                os.remove(DATA_FILE)
                continue 
            
            df['Morning'] = df['Morning'].fillna('')
            df['Afternoon'] = df['Afternoon'].fillna('')
            if 'Lunch' not in df.columns:
                df['Lunch'] = '식사-'
            df['Lunch'] = df['Lunch'].fillna('식사-')
            df['Lunch'] = df['Lunch'].apply(lambda x: x if x in LUNCH_OPTIONS else '식사-')

            return df
        except Exception:
            time.sleep(0.1)
    return pd.DataFrame()

def save_data(df):
    for _ in range(5):
        try:
            df.to_csv(DATA_FILE, index=False, encoding='utf-8')
            return True
        except Exception:
            time.sleep(0.1)
    return False

def load_notice():
    if not os.path.exists(NOTICE_FILE): return ""
    for _ in range(5):
        try:
            with open(NOTICE_FILE, "r", encoding="utf-8") as f: return f.read()
        except: time.sleep(0.1)
    return ""

def load_notice_time():
    if not os.path.exists(NOTICE_TIME_FILE): return ""
    for _ in range(5):
        try:
            with open(NOTICE_TIME_FILE, "r", encoding="utf-8") as f: return f.read()
        except: time.sleep(0.1)
    return ""

def save_notice_callback():
    new_notice = st.session_state["notice_area"]
    now_time = get_korean_time_str()
    try:
        with open(NOTICE_FILE, "w", encoding="utf-8") as f:
            f.write(new_notice)
            f.flush()
            os.fsync(f.fileno())
        with open(NOTICE_TIME_FILE, "w", encoding="utf-8") as f:
            f.write(now_time)
            f.flush()
            os.fsync(f.fileno())
        
        st.session_state["last_server_time"] = now_time
    except: pass

# --- 스마트 동기화 로직 ---
def sync_session_state(df):
    if df.empty: return
    
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
    
    server_time = load_notice_time()
    if "last_server_time" not in st.session_state:
        st.session_state["last_server_time"] = server_time
        st.session_state["notice_area"] = load_notice()
    elif st.session_state["last_server_time"] != server_time:
        st.session_state["notice_area"] = load_notice()
        st.session_state["last_server_time"] = server_time

# --- 액션 함수 ---
def update_data_callback(room_name, col_name, session_key):
    new_value = st.session_state.get(session_key)
    if new_value is not None:
        df = load_data()
        if df.empty: return
        idx = get_room_index(df, room_name)
        if df.loc[idx, col_name] != new_value:
            df.loc[idx, col_name] = new_value
            df.loc[idx, 'Last_Update'] = get_korean_time_str()
            save_data(df)

# --- 스타일 헬퍼 함수 ---
def get_status_style(room, df):
    try:
        row = df[df['Room'] == room].iloc[0]
        status = row['Status']
        lunch = row['Lunch']
        bg_color = "#f1f3f4"
        text_color = "#555"
        border_color = "#ddd"
        border_width = "1px"
        
        if "수술" in status:
            bg_color = "#E0F2FE"
            text_color = "#0EA5E9"
            border_color = "#0EA5E9"
        elif "대기" in status:
            bg_color = "#FFF3E0"
            text_color = "#EF6C00"
            border_color = "#EF6C00"
        
        if lunch == "식사+":
            border_color = "#FF4081"
            border_width = "3px"
            if text_color == "#555": 
                text_color = "#000"

        return f"background-color: {bg_color}; color: {text_color}; border: {border_width} solid {border_color};"
    except:
        return "background-color: #f1f3f4; color: #555; border: 1px solid #ddd;"

# --- UI 렌더링 ---
def render_final_card(room_name, df):
    st.markdown(f"<div id='target_{room_name}' style='scroll-margin-top: 100px;'></div>", unsafe_allow_html=True)
    row = df[df['Room'] == room_name].iloc[0]
    status = row['Status']
    lunch_status = row['Lunch']
    
    if "수술" in status:
        bg_color = "#E0F2FE"       
        text_color = "#0EA5E9"     
    elif "대기" in status:
        bg_color = "#FFF3E0"       
        text_color = "#EF6C00"     
    else: 
        bg_color = "#E0E0E0"       
        text_color = "#000000"     

    current_icon = status.split(" ")[0] 

    with st.container(border=True):
        c1, c2 = st.columns([0.6, 1.2], gap="medium")
        with c1:
            st.markdown(f"""
                <div style='
                    width: 100%; font-size: 1.2rem; font-weight: bold;
                    color: {text_color}; background-color: {bg_color};
                    padding: 4px 0px; border-radius: 6px; text-align: center;
                    display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
                '>
                    <span style='margin-right: 3px;'>{current_icon}</span>{room_name}
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

        s1, s2, s3 = st.columns([1, 0.8, 1], gap="small")
        key_m = f"m_{room_name}"
        key_l = f"l_{room_name}"
        key_a = f"a_{room_name}"
        
        s1.text_input("오전", key=key_m, placeholder="오전", label_visibility="collapsed",
                      on_change=update_data_callback, args=(room_name, 'Morning', key_m))
        s2.selectbox("점심", LUNCH_OPTIONS, key=key_l, label_visibility="collapsed",
                      index=LUNCH_OPTIONS.index(lunch_status) if lunch_status in LUNCH_OPTIONS else 0,
                      on_change=update_data_callback, args=(room_name, 'Lunch', key_l))
        s3.text_input("오후", key=key_a, placeholder="오후", label_visibility="collapsed",
                      on_change=update_data_callback, args=(room_name, 'Afternoon', key_a))

        st.markdown(f"""
            <div style='text-align: right; font-size: 10px; color: #aaa; margin-top: 2px;'>
                Update: {row['Last_Update']}
            </div>
            """, unsafe_allow_html=True)

def render_zone(col, title, zone_list, df):
    with col:
        st.markdown(f"<h4 style='margin-bottom: -15px;'>{title}</h4>", unsafe_allow_html=True)
        for room in zone_list:
            render_final_card(room, df)

# --- 메인 실행 ---
st.set_page_config(page_title="JNUH OR", layout="wide")

# [중요] 앱 실행 시 가장 먼저 날짜 리셋 체크
check_daily_reset()

st.markdown("<div id='top'></div>", unsafe_allow_html=True)
st.markdown("""
    <style>
    /* 1. 상단 여백 줄이기 (여기를 조절하세요: 1rem ~ 3rem 추천) */
    .block-container {
        padding-top: 0.1rem !important; 
        padding-bottom: 1rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* 2. 제목 자체의 상단 여백 제거 */
    h3 {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    
    /* 기존 스타일 유지 */
    div[data-testid="column"] > div > div > div[data-testid="stVerticalBlock"] { gap: 0rem !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] { margin-bottom: 0.1rem !important; }
    div[data-testid="stVerticalBlockBorderWrapper"] > div > div > div { gap: 0.1rem !important; }
    h4 { margin-top: 0px !important; margin-bottom: -15px !important; padding-bottom: 0px !important; z-index: 1; position: relative; }
    hr { margin-top: 0.2rem !important; margin-bottom: 0.3rem !important; }
    
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        padding-top: 0px; padding-bottom: 0px; padding-left: 5px; height: 32px; min-height: 32px;
        font-size: 14px; display: flex; align-items: center; border-color: #E0E0E0;
    }
    div[data-testid="stTextInput"] div[data-baseweb="input"] {
        background-color: #FFFFFF !important; border: 1px solid #CCCCCC !important; border-radius: 4px;
        padding-top: 0px; padding-bottom: 0px; height: 32px; min-height: 32px;
    }
    div[data-testid="stTextInput"] input {
        background-color: #FFFFFF !important; color: #000000 !important; font-size: 14px; padding: 0px 5px !important;
    }
    div[data-testid="stTextArea"] textarea {
        background-color: #FFF9C4 !important; color: #333 !important; font-size: 13px !important; line-height: 1.5;
    }
    .link-container { display: flex; width: 100%; justify-content: space-between; gap: 2px; margin-bottom: 5px; }
    .quick-link {
        flex: 1; display: block; text-decoration: none; text-align: center; padding: 8px 0;
        font-size: 11px; font-weight: bold; white-space: nowrap; border-radius: 8px;
        transition: opacity 0.2s; box-sizing: border-box;
    }
    .quick-link:hover { opacity: 0.8; }
    div[data-testid="column"]:nth-of-type(3) button {
        background-color: #E6F2FF !important; color: #0057A4 !important; border: 1px solid #0057A4 !important;
        border-radius: 8px !important; font-weight: bold !important; transition: all 0.3s ease;
        width: auto !important; padding-left: 20px !important; padding-right: 20px !important;
        min-width: 120px !important; font-size: 13px !important;
    }
    div[data-testid="column"]:nth-of-type(3) button p { color: #0057A4 !important; }
    div[data-testid="column"]:nth-of-type(3) button:hover {
        background-color: #CCE4FF !important; border-color: #004080 !important;
    }
    div[data-testid="column"]:nth-of-type(3) button:hover p { color: #004080 !important; }
    
    @media (max-width: 900px) {
        .block-container > div > div > div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: column !important; }
        .block-container > div > div > div[data-testid="stHorizontalBlock"] > div:nth-child(3) { order: 1; margin-bottom: 20px; }
        .block-container > div > div > div[data-testid="stHorizontalBlock"] > div:nth-child(1) { order: 2; }
        .block-container > div > div > div[data-testid="stHorizontalBlock"] > div:nth-child(2) { order: 3; }
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stHorizontalBlock"] { flex-direction: row !important; gap: 20px !important; }
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stHorizontalBlock"] > div { order: unset !important; margin-bottom: 0px !important; }
        div[data-testid="stButton"]:first-of-type {
            position: fixed !important; bottom: 20px !important; left: 80px !important; width: auto !important; z-index: 999999 !important;
            background-color: transparent !important; margin: 0 !important;
        }
        div[data-testid="stButton"]:first-of-type button {
            width: 220px !important; height: 50px !important; font-size: 13px !important; border-radius: 25px !important;
            box-shadow: 0px 4px 15px rgba(0, 87, 164, 0.3) !important; padding: 0 !important;
            background-color: #E6F2FF !important; border: 2px solid #0057A4 !important;
        }
        div[data-testid="stButton"]:first-of-type button p { color: #0057A4 !important; }
        .floating-top-btn {
            position: fixed; bottom: 20px; left: 15px; width: 50px; height: 50px; background-color: #FFFFFF; color: #333;
            border: 2px solid #ddd; border-radius: 15px; text-align: center; line-height: 50px; font-size: 20px;
            font-weight: bold; text-decoration: none; box-shadow: 0px 4px 15px rgba(0,0,0,0.2); z-index: 999999; transition: all 0.2s;
        }
        .floating-top-btn:hover { background-color: #f0f0f0; color: #000; }
        .block-container { padding-bottom: 100px !important; }
    }
    @media (max-width: 600px) {
        div[data-testid="stVerticalBlockBorderWrapper"] { max-width: 95vw; margin: auto; }
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("### 🩺 JNUH OR Dashboard")
st.markdown("---")

df = load_data()
sync_session_state(df)

col_a, col_b, col_notice = st.columns([1, 1, 0.5], gap="small")

render_zone(col_a, "A 구역", ZONE_A, df)
render_zone(col_b, "B / C / 기타", ZONE_B, df)

with col_notice:
    notice_time = load_notice_time()
    if notice_time == "": notice_time = "-"
    
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; margin-top: -5px;">
            <h5 style="margin:0; font-weight: bold; font-size: 1.35rem;">📢 공지사항</h5>
            <span style="font-size: 12px; color: #D32F2F; font-weight: bold;">Update: {notice_time}</span>
        </div>
    """, unsafe_allow_html=True)

    st.text_area(
        "공지사항 내용", key="notice_area", height=200, label_visibility="collapsed",
        placeholder="전달사항을 입력하세요...", on_change=save_notice_callback
    )
    
    if st.button("변경사항 저장", use_container_width=False):
        save_notice_callback()
        save_data(df)
        st.toast("모든 변경사항이 저장되었습니다!", icon="✅")

    st.markdown("<a href='#top' class='floating-top-btn'>🔝</a>", unsafe_allow_html=True)

    st.markdown("<div style='margin-top: -15px; margin-bottom: 5px; font-weight: bold; font-size: 14px;'>🚀 빠른 이동</div>", unsafe_allow_html=True)
    
    links_a = "<div class='link-container'>"
    for room in ZONE_A:
        style = get_status_style(room, df)
        links_a += f"<a href='#target_{room}' class='quick-link' style='{style}' target='_self'>{room}</a>"
    links_a += "</div>"
    
    links_b = "<div class='link-container'>"
    for room in ZONE_B:
        short_name = room.replace("회복실", "회복")
        style = get_status_style(room, df)
        links_b += f"<a href='#target_{room}' class='quick-link' style='{style}' target='_self'>{short_name}</a>"
    links_b += "</div>"
    
    st.markdown(links_a + links_b, unsafe_allow_html=True)
