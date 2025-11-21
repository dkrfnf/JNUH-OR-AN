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
NOTICE_FILE = 'notice.txt'  # 공지사항 저장 파일
OP_STATUS = ["▶ 수술", "Ⅱ 대기", "■ 종료"]

# 2초 자동 새로고침
st_autorefresh(interval=2000, key="datarefresh")

# 한국 시간 구하기
def get_korean_time():
    utc_now = datetime.utcnow()
    kst_now = utc_now + timedelta(hours=9)
    return kst_now.strftime("%H:%M")

def get_room_index(df, room_name):
    return df[df['Room'] == room_name].index[0]

# --- 데이터 로드/저장 (수술실 현황) ---
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

# --- 공지사항 로드/저장 ---
def load_notice():
    if not os.path.exists(NOTICE_FILE):
        return ""
    try:
        with open(NOTICE_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""

def save_notice_callback():
    new_notice = st.session_state["notice_area"]
    with open(NOTICE_FILE, "w", encoding="utf-8") as f:
        f.write(new_notice)

# --- 동기화 로직 ---
def sync_session_state(df):
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

    server_notice = load_notice()
    if "notice_area" not in st.session_state:
        st.session_state["notice_area"] = server_notice
    else:
        if st.session_state["notice_area"] != server_notice:
             pass

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
    sync_session_state(df)
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
        bg_color = "#E0E0E0"      
        icon_color = "#000000"    
        text_color = "#000000"    

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
            key_status = f"st_{room_name}"
            st.selectbox(
                "상태", OP_STATUS,
                key=key_status,
                index=OP_STATUS.index(status) if status in OP_STATUS else 0,
                label_visibility="collapsed",
                on_change=update_data_callback, 
                args=(room_name, 'Status', key_status)
            )

        # ★ 중요: 이곳의 s1, s2, s3 순서가 CSS 때문에 뒤섞이지 않도록 수정됨
        s1, s2, s3 = st.columns(3)
        key_m = f"m_{room_name}"
        key_l = f"l_{room_name}"
        key_a = f"a_{room_name}"
        
        s1.text_input("오전", key=key_m, placeholder="", label_visibility="collapsed",
                      on_change=update_data_callback, args=(room_name, 'Morning', key_m))
        s2.text_input("점심", key=key_l, placeholder="", label_visibility="collapsed",
                      on_change=update_data_callback, args=(room_name, 'Lunch', key_l))
        s3.text_input("오후", key=key_a, placeholder="", label_visibility="collapsed",
                      on_change=update_data_callback, args=(room_name, 'Afternoon', key_a))

        st.markdown(f"<p style='text-align: right; font-size: 10px; color: #888; margin-top: 5px; margin-bottom: 0;'>Update: {row['Last_Update']}</p>", unsafe_allow_html=True)

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
    
    div[data-testid="stTextArea"] textarea {
        background-color: #FFF9C4 !important;
        color: #333 !important;
        font-size: 14px !important; 
        font-weight: normal;        
        line-height: 1.5;
        padding-bottom: 10px !important; 
    }
    
    /* ★★★ [저장 버튼 오른쪽 아래 배치] ★★★ */
    /* 공지사항 영역(3번째 메인 컬럼) 내의 버튼 스타일 지정 */
    div[data-testid="column"]:nth-of-type(3) button {
        float: right !important;      /* 오른쪽 정렬 */
        margin-top: -45px !important; /* 위로 끌어올리기 */
        margin-right: 5px !important;
        
        /* 버튼 디자인 */
        background-color: rgba(255, 255, 255, 0.8) !important;
        border: 1px solid #ddd !important;
        border-radius: 8px !important;
        z-index: 99 !important; 
        height: 2.2rem !important;
        width: 2.2rem !important;
        padding: 0px !important;
    }

    /* ★★★ [모바일 레이아웃 수정 - 오전/점심/오후 순서 복구] ★★★ */
    @media (max-width: 640px) {
        
        /* 1. [메인 화면] 공지사항을 맨 위로 */
        /* data-testid="stMainBlock" 바로 아래의 첫번째 HorizontalBlock이 메인 3단 컬럼임 */
        .block-container > div > div > div[data-testid="stHorizontalBlock"] {
            flex-direction: column !important;
        }
        /* 공지사항(3번째) -> 1번 */
        .block-container > div > div > div[data-testid="stHorizontalBlock"] > div:nth-child(3) { 
            order: 1; 
            margin-bottom: 20px; 
        }
        /* A구역(1번째) -> 2번 */
        .block-container > div > div > div[data-testid="stHorizontalBlock"] > div:nth-child(1) { 
            order: 2; 
        }
        /* B구역(2번째) -> 3번 */
        .block-container > div > div > div[data-testid="stHorizontalBlock"] > div:nth-child(2) { 
            order: 3; 
        }

        /* 2. [카드 내부] 오전/점심/오후 순서 섞임 방지 (매우 중요) */
        /* 테두리 박스(stVerticalBlockBorderWrapper) 안에 있는 HorizontalBlock은 순서 변경 금지 */
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stHorizontalBlock"] {
            flex-direction: row !important; /* 가로 정렬 유지 */
        }
        /* 내부 아이템들의 order 속성을 초기화 */
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stHorizontalBlock"] > div {
            order: unset !important;
            margin-bottom: 0px !important;
        }
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
    st.markdown("#### 📢 공지사항")
    st.text_area(
        "공지사항 내용",
        key="notice_area",
        height=200, 
        label_visibility="collapsed",
        placeholder="전달사항을 입력하세요...",
        on_change=save_notice_callback 
    )
    
    # CSS로 위치 조정됨 (오른쪽 아래)
    if st.button("💾", help="저장하기"):
        save_notice_callback()
        st.toast("저장 완료!", icon="✅")

st.markdown("---")

with st.expander("⚙️ 관리자 메뉴 (하루 시작 / 초기화)"):
    st.warning("⚠️ 주의: 모든 수술실의 상태와 입력된 이름이 초기화됩니다.")
    if st.button("🔄 하루 시작 (전체 초기화)", use_container_width=True, type="primary"):
        reset_all_data()
