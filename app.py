import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import time
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. 설정 및 상수 정의
# ==========================================
ZONE_A = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
ZONE_B = ["B1", "B2", "B3", "B4", "C2", "외부", "회복실"]
ALL_ROOMS = ZONE_A + ZONE_B

DATA_FILE = 'or_status_kst.csv'
NOTICE_FILE = 'notice.txt'
NOTICE_TIME_FILE = 'notice_time.txt'
RESET_LOG_FILE = 'reset_log.txt'

OP_STATUS = ["▶ 수술", "Ⅱ 대기", "■ 종료"]
LUNCH_OPTIONS = ["식사-", "식사+"]

# ==========================================
# 2. 유틸리티 함수 (시간, 파일 입출력)
# ==========================================
def get_korean_now():
    return datetime.utcnow() + timedelta(hours=9)

def get_time_str():
    return get_korean_now().strftime("%H:%M")

def get_date_str():
    return get_korean_now().strftime("%Y-%m-%d")

def load_data():
    """데이터 파일 로드 및 초기화"""
    # 파일이 없으면 생성
    if not os.path.exists(DATA_FILE):
        df = pd.DataFrame({
            'Room': ALL_ROOMS,
            'Status': ['▶ 수술'] * len(ALL_ROOMS),
            'Last_Update': [get_time_str()] * len(ALL_ROOMS),
            'Morning': [''] * len(ALL_ROOMS),
            'Lunch': ['식사-'] * len(ALL_ROOMS),
            'Afternoon': [''] * len(ALL_ROOMS)
        })
        df.to_csv(DATA_FILE, index=False, encoding='utf-8')
        return df

    # 파일 읽기 (실패 시 재시도)
    for _ in range(5):
        try:
            df = pd.read_csv(DATA_FILE, encoding='utf-8')
            # 결측치 처리
            df['Morning'] = df['Morning'].fillna('')
            df['Afternoon'] = df['Afternoon'].fillna('')
            if 'Lunch' not in df.columns: df['Lunch'] = '식사-'
            df['Lunch'] = df['Lunch'].fillna('식사-').apply(lambda x: x if x in LUNCH_OPTIONS else '식사-')
            return df
        except:
            time.sleep(0.1)
    return pd.DataFrame() # 실패 시 빈 DF

def save_data(df):
    """데이터 파일 저장"""
    for _ in range(5):
        try:
            df.to_csv(DATA_FILE, index=False, encoding='utf-8')
            return True
        except:
            time.sleep(0.1)
    return False

def load_text(file_path):
    if not os.path.exists(file_path): return ""
    for _ in range(3):
        try:
            with open(file_path, "r", encoding="utf-8") as f: return f.read()
        except: time.sleep(0.1)
    return ""

def save_text(file_path, content):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            os.fsync(f.fileno())
    except: pass

# ==========================================
# 3. 비즈니스 로직 (동기화, 리셋)
# ==========================================
def sync_state(df):
    """Session State와 데이터프레임 동기화"""
    if df.empty: return

    # 1. 수술실 데이터 동기화
    for _, row in df.iterrows():
        room = row['Room']
        for col, prefix in [('Status', 'st'), ('Morning', 'm'), ('Lunch', 'l'), ('Afternoon', 'a')]:
            key = f"{prefix}_{room}"
            if key not in st.session_state or st.session_state[key] != row[col]:
                st.session_state[key] = row[col]

    # 2. 공지사항 동기화
    srv_time = load_text(NOTICE_TIME_FILE)
    if "last_srv_time" not in st.session_state or st.session_state["last_srv_time"] != srv_time:
        st.session_state["notice_area"] = load_text(NOTICE_FILE)
        st.session_state["last_srv_time"] = srv_time

def check_auto_reset():
    """아침 7시 자동 리셋"""
    if get_time_str() == "07:00":
        last_date = load_text(RESET_LOG_FILE).strip()
        today = get_date_str()
        if last_date != today:
            save_text(RESET_LOG_FILE, today)
            reset_all_data()

def reset_all_data():
    """데이터 초기화"""
    df = load_data()
    if df.empty: return
    df['Status'] = '▶ 수술'
    df['Morning'] = ''
    df['Lunch'] = '식사-'
    df['Afternoon'] = ''
    df['Last_Update'] = get_time_str()
    save_data(df)
    st.rerun()

def on_update(room, col, key):
    """입력 변경 시 콜백"""
    val = st.session_state[key]
    df = load_data()
    idx = df[df['Room'] == room].index[0]
    if df.loc[idx, col] != val:
        df.loc[idx, col] = val
        df.loc[idx, 'Last_Update'] = get_time_str()
        save_data(df)

def on_save_notice():
    """공지사항 저장 콜백"""
    save_text(NOTICE_FILE, st.session_state["notice_area"])
    save_text(NOTICE_TIME_FILE, get_time_str())
    st.session_state["last_srv_time"] = get_time_str()

# ==========================================
# 4. 스타일(CSS) 정의
# ==========================================
def inject_custom_css():
    st.markdown("""
    <style>
    /* 기본 레이아웃 조정 */
    .block-container { padding: 1rem; padding-bottom: 120px; } /* 하단 여백 확보 */
    div[data-testid="stVerticalBlock"] { gap: 0.2rem !important; }
    h4 { margin: 0 0 -15px 0 !important; z-index: 1; position: relative; }
    
    /* 컴포넌트 스타일 단순화 */
    div[data-testid="stSelectbox"] > div > div { min-height: 32px; height: 32px; padding: 0 5px; font-size: 14px; }
    div[data-testid="stTextInput"] > div > div { min-height: 32px; height: 32px; padding: 0; background: #fff; }
    div[data-testid="stTextInput"] input { padding: 0 5px; font-size: 14px; }
    textarea { background: #FFF9C4 !important; color: #333 !important; font-size: 13px !important; }

    /* 빠른 이동 링크 */
    .link-box { display: flex; gap: 2px; margin-bottom: 5px; }
    .q-link { flex: 1; text-align: center; padding: 8px 0; font-size: 11px; font-weight: bold; border-radius: 8px; text-decoration: none; display: block; }
    .q-link:hover { opacity: 0.8; }

    /* [PC 스타일] 저장 버튼 & 관리자 버튼 */
    button { border-radius: 8px !important; font-weight: bold !important; }
    div[data-testid="stButton"] button { background: #E6F2FF; color: #0057A4; border: 1px solid #0057A4; }
    div[data-testid="stExpander"] button { background: #FFEBEE; color: #B71C1C; border: 1px solid #EF9A9A; width: 100%; }

    /* =========================================
       [모바일 전용 스타일] (900px 이하)
       ========================================= */
    @media (max-width: 900px) {
        /* 1. 관리자 메뉴(하루 시작) 숨기기 */
        div[data-testid="stExpander"] { display: none !important; }

        /* 2. 저장 버튼 플로팅 (화면에 남은 유일한 버튼) */
        div[data-testid="stButton"] {
            position: fixed !important;
            bottom: 20px !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: 220px !important;
            z-index: 999999 !important;
        }
        
        div[data-testid="stButton"] button {
            width: 100% !important;
            height: 50px !important;
            border-radius: 25px !important;
            box-shadow: 0px 5px 15px rgba(0, 87, 164, 0.3) !important;
            font-size: 13px !important;
            border: 2px solid #0057A4 !important;
            background-color: #E6F2FF !important;
            color: #0057A4 !important;
        }
        
        /* 3. 레이아웃 스택킹 */
        div[data-testid="column"] { width: 100% !important; flex: 1 1 auto !important; }
        
        /* 4. TOP 버튼 */
        .top-btn { position: fixed; bottom: 20px; left: 15px; width: 50px; height: 50px; background: #fff; border: 2px solid #ddd; border-radius: 15px; text-align: center; line-height: 50px; font-size: 20px; z-index: 999999; text-decoration: none; }
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 5. UI 렌더링 함수
# ==========================================
def get_card_style(status, lunch):
    bg, txt, border = "#f1f3f4", "#555", "1px solid #ddd"
    
    if "수술" in status:
        bg, txt, border = "#E0F2FE", "#0EA5E9", "1px solid #0EA5E9"
    elif "대기" in status:
        bg, txt, border = "#FFF3E0", "#EF6C00", "1px solid #EF6C00"
    
    if lunch == "식사+":
        border = "3px solid #FF4081"
        if txt == "#555": txt = "#000"
        
    return f"background-color:{bg}; color:{txt}; border:{border};"

def render_room_card(room, df):
    st.markdown(f"<div id='target_{room}' style='scroll-margin-top: 100px;'></div>", unsafe_allow_html=True)
    row = df[df['Room'] == room].iloc[0]
    
    # 스타일 결정
    if "수술" in row['Status']: card_bg, card_txt = "#E0F2FE", "#0EA5E9"
    elif "대기" in row['Status']: card_bg, card_txt = "#FFF3E0", "#EF6C00"
    else: card_bg, card_txt = "#E0E0E0", "#000"

    icon = row['Status'].split(" ")[0]

    with st.container(border=True):
        c1, c2 = st.columns([0.6, 1.2])
        c1.markdown(f"<div style='background:{card_bg}; color:{card_txt}; padding:4px; border-radius:6px; text-align:center; font-weight:bold; font-size:1.2rem; white-space:nowrap;'>{icon} {room}</div>", unsafe_allow_html=True)
        
        key_st = f"st_{room}"
        c2.selectbox("상태", OP_STATUS, key=key_st, index=OP_STATUS.index(row['Status']) if row['Status'] in OP_STATUS else 0, label_visibility="collapsed", on_change=on_update, args=(room, 'Status', key_st))

        s1, s2, s3 = st.columns([1, 0.8, 1])
        key_m, key_l, key_a = f"m_{room}", f"l_{room}", f"a_{room}"
        
        s1.text_input("오전", key=key_m, placeholder="오전", label_visibility="collapsed", on_change=on_update, args=(room, 'Morning', key_m))
        s2.selectbox("점심", LUNCH_OPTIONS, key=key_l, label_visibility="collapsed", index=LUNCH_OPTIONS.index(row['Lunch']) if row['Lunch'] in LUNCH_OPTIONS else 0, on_change=on_update, args=(room, 'Lunch', key_l))
        s3.text_input("오후", key=key_a, placeholder="오후", label_visibility="collapsed", on_change=on_update, args=(room, 'Afternoon', key_a))
        
        st.caption(f"Update: {row['Last_Update']}")

def render_links(zone, df):
    html = "<div class='link-box'>"
    for room in zone:
        style = get_card_style(df[df['Room']==room]['Status'].values[0], df[df['Room']==room]['Lunch'].values[0])
        name = room.replace("회복실", "회복")
        html += f"<a href='#target_{room}' class='q-link' style='{style}' target='_self'>{name}</a>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ==========================================
# 6. 메인 실행 블록
# ==========================================
st.set_page_config(page_title="JNUH OR", layout="wide")
check_auto_reset()
st_autorefresh(interval=2000, key="refresh")
inject_custom_css()

st.markdown("<div id='top'></div>", unsafe_allow_html=True)
st.markdown("### 🩺 JNUH OR Dashboard")
st.markdown("---")

df = load_data()
sync_state(df)

# 메인 레이아웃
col1, col2, col3 = st.columns([1, 1, 0.5])

with col1:
    st.markdown("<h4>A 구역</h4>", unsafe_allow_html=True)
    for r in ZONE_A: render_room_card(r, df)

with col2:
    st.markdown("<h4>B / C / 기타</h4>", unsafe_allow_html=True)
    for r in ZONE_B: render_room_card(r, df)

with col3:
    # 공지사항
    t_str = load_text(NOTICE_TIME_FILE) or "-"
    st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center;'><h5>📢 공지사항</h5><span style='font-size:12px; color:red; font-weight:bold;'>{t_str}</span></div>", unsafe_allow_html=True)
    st.text_area("공지", key="notice_area", height=200, label_visibility="collapsed", on_change=on_save_notice)
    
    # 저장 버튼 (모바일에서 플로팅되는 대상)
    if st.button("변경사항 저장", use_container_width=True):
        on_save_notice()
        save_data(df)
        st.toast("저장 완료!", icon="✅")

    # 빠른 이동 & Top
    st.markdown("<a href='#top' class='top-btn'>🔝</a>", unsafe_allow_html=True)
    st.markdown("<b>🚀 빠른 이동</b>", unsafe_allow_html=True)
    render_links(ZONE_A, df)
    render_links(ZONE_B, df)

st.markdown("---")

# 관리자 메뉴 (모바일에서 display:none 처리됨)
with st.expander("⚙️ 관리자 메뉴 (하루 시작)"):
    st.warning("데이터가 초기화됩니다.")
    if st.button("🔄 하루 시작", type="primary"):
        reset_all_data()
