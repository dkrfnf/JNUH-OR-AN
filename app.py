import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import time
import requests
from streamlit_autorefresh import st_autorefresh

# --- ntfy 설정 ---
NTFY_TOPIC = "oranda-jnuh-2025-xk9q"  # ← 이 이름을 원하는 대로 바꾸세요 (복잡할수록 보안상 좋음)
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"
# [추가] 중앙 컴퓨터 전용 토픽 (중앙 컴퓨터만 이 토픽을 구독)
NTFY_CENTER_TOPIC = "oranda-center"
NTFY_CENTER_URL = f"https://ntfy.sh/{NTFY_CENTER_TOPIC}"
# [추가] 방별 토픽 코드 (토픽 이름은 영어/숫자만 가능 → 외부는 ext)
ROOM_TOPIC_CODE = {"A1": "a1", "A2": "a2", "A3": "a3", "A4": "a4", "A5": "a5", "A6": "a6", "A7": "a7",
                   "B1": "b1", "B2": "b2", "B3": "b3", "B4": "b4", "C2": "c2", "외부": "ext"}

ROOM_TOPIC_PREFIX = "oranda"   # 방별·중앙 구독 이름 앞부분 (예: oranda-a1, oranda-center)

def get_room_topic(room):
    """방별 구독 이름. 예: oranda-a3"""
    return f"{ROOM_TOPIC_PREFIX}-{ROOM_TOPIC_CODE.get(room, room.lower())}"

def send_ntfy(title: str, message: str, priority: str = "high", url: str = NTFY_URL):
    """ntfy 푸시 알림 발송"""
    try:
        resp = requests.post(
            url,
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,   # urgent / high / default / low
                "Tags": "loudspeaker",  # 🔊 이모지
            },
            timeout=10
        )
        return {
            "ok": resp.ok,
            "status_code": resp.status_code,
            "text": resp.text[:300]
        }
    except Exception as e:
        return {
            "ok": False,
            "status_code": None,
            "text": str(e)
        }

# --- 설정 ---
ZONE_A = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"]
ZONE_B = ["B1", "B2", "B3", "B4", "C2", "외부"]
ALL_ROOMS = ZONE_A + ZONE_B
DATA_FILE = 'or_status_kst.csv'
NOTICE_FILE = 'notice.txt'
NOTICE_TIME_FILE = 'notice_time.txt'
RESET_LOG_FILE = 'reset_log.txt'
OFF_RESIDENT_FILE = 'off_resident.txt'
ARRANGE_DONE_FILE = 'arrange_done.txt'

# 상태 옵션 정의
OP_STATUS = ["▶ 수술", "Ⅱ 대기", "■ 종료"]
# [변경] 교대 및 식사 상태 옵션 통합
SHIFT_OPTIONS = ["--", "오전교대+", "식사+", "오후교대+"]
# 전공의 목록 (--는 제외, 실제 이름만)
RESIDENTS = ["유수란", "임우희", "정우석", "남현우", "이형섭", "이예은", "이준오"]
# [추가] OFF 선택지에서 뺄 사람
OFF_EXCLUDE = ["유수란"]
OFF_OPTIONS = [r for r in RESIDENTS if r not in OFF_EXCLUDE]

# [추가] 밥교대 남은 방 계산 기준
MEAL_EXCLUDE_ROOMS = ["회복실"]            # 밥교대 대상에서 빼는 방 (목록에 없으면 무시됨)
MEAL_DONE_SHIFTS = ["식사+"]               # 밥교대가 끝난 것으로 보는 교대 상태

# 2초 자동 새로고침
st_autorefresh(interval=2000, key="datarefresh")

# --- 시간 관련 함수 ---
def get_korean_datetime():
    utc_now = datetime.utcnow()
    kst_now = utc_now + timedelta(hours=9)
    return kst_now

def get_korean_time_str():
    return get_korean_datetime().strftime("%H:%M")

def get_room_index(df, room_name):
    return df[df['Room'] == room_name].index[0]

# --- 자동 리셋 로직 ---
def load_last_reset_time():
    if not os.path.exists(RESET_LOG_FILE):
        return datetime.min
    try:
        with open(RESET_LOG_FILE, "r", encoding="utf-8") as f:
            timestamp_str = f.read().strip()
            return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    except:
        return datetime.min

def save_current_reset_time(dt_obj):
    try:
        with open(RESET_LOG_FILE, "w", encoding="utf-8") as f:
            f.write(dt_obj.strftime("%Y-%m-%d %H:%M:%S"))
    except: pass

def check_daily_reset():
    now = get_korean_datetime()
    target_reset_time = now.replace(hour=7, minute=0, second=0, microsecond=0)
    
    if now.hour < 7:
        target_reset_time = target_reset_time - timedelta(days=1)
        
    last_reset = load_last_reset_time()
    
    if last_reset < target_reset_time:
        perform_reset(now)

def perform_reset(current_time):
    # [변경] 데이터 컬럼을 Memo, Shift로 변경하여 초기화
    df = pd.DataFrame({
        'Room': ALL_ROOMS,
        'Status': ['▶ 수술'] * len(ALL_ROOMS),
        'Last_Update': [current_time.strftime("%H:%M")] * len(ALL_ROOMS),
        'Memo': [''] * len(ALL_ROOMS),         # 자유 메모
        'Shift': ['--'] * len(ALL_ROOMS),      # 교대/식사 상태
        'Meal_Done': [False] * len(ALL_ROOMS)  # [추가] 오늘 밥교대 했는지 (오후교대로 바뀌어도 유지)
    })

    df.to_csv(DATA_FILE, index=False, encoding='utf-8')
    save_current_reset_time(current_time)

    # 공지사항, OFF 전공의, 어레인지 리셋
    try:
        with open(NOTICE_FILE, "w", encoding="utf-8") as f:
            f.write("")
        with open(NOTICE_TIME_FILE, "w", encoding="utf-8") as f:
            f.write("")
        with open(OFF_RESIDENT_FILE, "w", encoding="utf-8") as f:
            f.write("")
        with open(ARRANGE_DONE_FILE, "w", encoding="utf-8") as f:
            f.write("0")
    except: pass

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.rerun()

# --- 데이터 로드/저장 ---
def load_data():
    for _ in range(5):
        try:
            if not os.path.exists(DATA_FILE):
                now = get_korean_datetime()
                perform_reset(now)
                return pd.read_csv(DATA_FILE, encoding='utf-8')
            
            df = pd.read_csv(DATA_FILE, encoding='utf-8')
            current_rooms = df['Room'].tolist()
            if len(df) != len(ALL_ROOMS) or current_rooms != ALL_ROOMS:
                os.remove(DATA_FILE)
                continue 
            
            # [변경] 구버전 파일 호환성 처리 (컬럼이 없으면 생성)
            if 'Memo' not in df.columns: df['Memo'] = ''
            if 'Shift' not in df.columns: df['Shift'] = '--'
            
            df['Memo'] = df['Memo'].fillna('')
            df['Shift'] = df['Shift'].fillna('--')
            # 이상한 값이 있으면 '--'로 초기화
            df['Shift'] = df['Shift'].apply(lambda x: x if x in SHIFT_OPTIONS else '--')

            # [추가] 밥교대 기록 컬럼 (구버전 파일이면 현재 식사+ 여부로 채움)
            if 'Meal_Done' not in df.columns:
                df['Meal_Done'] = df['Shift'] == '식사+'
            df['Meal_Done'] = df['Meal_Done'].apply(lambda x: str(x).strip().lower() == 'true')

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

def save_notice_callback(send_push: bool = False):
    new_notice = st.session_state.get("notice_area", "")
    now_time = get_korean_time_str()
    try:
        prev_notice = load_notice().strip()
        stripped_notice = new_notice.strip()
        is_new = bool(stripped_notice) and stripped_notice != prev_notice

        with open(NOTICE_FILE, "w", encoding="utf-8") as f:
            f.write(new_notice)
            f.flush()
            os.fsync(f.fileno())
        with open(NOTICE_TIME_FILE, "w", encoding="utf-8") as f:
            f.write(now_time)
            f.flush()
            os.fsync(f.fileno())

        st.session_state["last_server_time"] = now_time

        if send_push:
            if not stripped_notice:
                return {
                    "saved": True,
                    "sent": False,
                    "reason": "empty"
                }

            result = send_ntfy(
                title=f"JNUH OR Notice ({now_time})",
                message=stripped_notice,
                priority="high"
            )
            return {
                "saved": True,
                "sent": result.get("ok", False),
                "is_new": is_new,
                "status_code": result.get("status_code"),
                "response_text": result.get("text", "")
            }

        return {
            "saved": True,
            "sent": False,
            "is_new": is_new
        }
    except Exception as e:
        return {
            "saved": False,
            "sent": False,
            "reason": str(e)
        }

def load_off_residents():
    """여러 명의 OFF 전공의를 리스트로 반환"""
    if not os.path.exists(OFF_RESIDENT_FILE): return []
    try:
        with open(OFF_RESIDENT_FILE, "r", encoding="utf-8") as f:
            val = f.read().strip()
            if not val or val == "--":
                return []
            return [x.strip() for x in val.split(",") if x.strip()]
    except: return []

def save_off_residents(names_list):
    """여러 명의 OFF 전공의를 저장"""
    try:
        with open(OFF_RESIDENT_FILE, "w", encoding="utf-8") as f:
            f.write(",".join(names_list))
            f.flush()
            os.fsync(f.fileno())
    except: pass

def toggle_off_resident(name):
    """클릭 시 토글 (선택/해제)"""
    current_list = load_off_residents()
    if name in current_list:
        current_list.remove(name)
    else:
        current_list.append(name)
    save_off_residents(current_list)

def load_arrange_done():
    """어레인지 완료 상태 로드"""
    if not os.path.exists(ARRANGE_DONE_FILE): return False
    try:
        with open(ARRANGE_DONE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() == "1"
    except: return False

def save_arrange_done(is_done):
    """어레인지 완료 상태 저장"""
    try:
        with open(ARRANGE_DONE_FILE, "w", encoding="utf-8") as f:
            f.write("1" if is_done else "0")
            f.flush()
            os.fsync(f.fileno())
    except: pass

# --- 스마트 동기화 로직 ---
def sync_session_state(df):
    if df.empty: return
    
    for index, row in df.iterrows():
        room = row['Room']
        
        # 수술 상태 동기화
        key_status = f"st_{room}"
        if key_status not in st.session_state or st.session_state[key_status] != row['Status']:
            st.session_state[key_status] = row['Status']
            
        # [변경] 메모 동기화
        key_memo = f"memo_{room}"
        if key_memo not in st.session_state or st.session_state[key_memo] != row['Memo']:
            st.session_state[key_memo] = row['Memo']
            
        # [변경] 교대 상태 동기화
        key_shift = f"shift_{room}"
        if key_shift not in st.session_state or st.session_state[key_shift] != row['Shift']:
            st.session_state[key_shift] = row['Shift']
    
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
            old_value = df.loc[idx, col_name]
            df.loc[idx, col_name] = new_value
            df.loc[idx, 'Last_Update'] = get_korean_time_str()

            # [추가] 밥교대 기록: 식사+가 되면 체크, 식사+에서 오후교대+로 넘어가도 유지
            if col_name == 'Shift':
                if new_value == '식사+':
                    df.loc[idx, 'Meal_Done'] = True
                elif old_value == '식사+' and new_value in ('--', '오전교대+'):
                    # 식사+를 잘못 눌러 되돌린 경우로 보고 기록 취소
                    df.loc[idx, 'Meal_Done'] = False

            save_data(df)

# --- [추가] 방으로 보내기 ---
def send_room_callback(room_name):
    key_msg = f"msg_{room_name}"
    msg = st.session_state.get(key_msg, "").strip()
    if not msg:
        st.session_state["room_result"] = ("warn", f"{room_name}: 보낼 내용을 먼저 입력하세요.")
        return
    now = get_korean_time_str()
    code = ROOM_TOPIC_CODE.get(room_name, room_name.lower()).upper()
    result = send_ntfy(
        title=f"JNUH OR {code} ({now})",   # 제목은 영어만 가능
        message=msg,
        priority="high",
        url=f"https://ntfy.sh/{get_room_topic(room_name)}"
    )
    if result.get("ok"):
        st.session_state[key_msg] = ""
        st.session_state["room_result"] = ("ok", f"{room_name}로 보냈습니다.")
    else:
        st.session_state["room_result"] = ("err", f"{room_name} 발송 실패: {result.get('text', '')}")

# --- [중요] 스타일 헬퍼 함수 (테두리 색상 로직) ---
def get_status_style(room, df):
    try:
        row = df[df['Room'] == room].iloc[0]
        status = row['Status']
        shift = row['Shift']  # [변경] 교대 상태 확인
        
        # 기본 배경/글자색 (수술/대기 상태 기준)
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
        
        # [변경] 교대/식사 상태에 따른 테두리 색상 오버라이드
        if shift == "오전교대+":
            border_color = "#4CAF50" # 녹색
            border_width = "3px"
            if text_color == "#555": text_color = "#000"
        elif shift == "식사+":
            border_color = "#FF4081" # 분홍색
            border_width = "3px"
            if text_color == "#555": text_color = "#000"
        elif shift == "오후교대+":
            border_color = "#1A237E" # 남색
            border_width = "3px"
            if text_color == "#555": text_color = "#000"

        return f"background-color: {bg_color}; color: {text_color}; border: {border_width} solid {border_color};"
    except:
        return "background-color: #f1f3f4; color: #555; border: 1px solid #ddd;"

# --- [추가] 밥교대 남은 방 ---
def get_remaining_meal_rooms(df):
    """종료된 방·제외 방을 빼고, 아직 밥교대가 안 된 방 목록"""
    remaining = []
    if df.empty:
        return remaining
    for room in ALL_ROOMS:
        if room in MEAL_EXCLUDE_ROOMS:
            continue
        row = df[df['Room'] == room]
        if row.empty:
            continue
        row = row.iloc[0]
        if "종료" in str(row['Status']):
            continue
        if row.get('Meal_Done', False) or row['Shift'] in MEAL_DONE_SHIFTS:
            continue
        remaining.append(room)
    return remaining

def render_remaining_meal_box(df):
    remaining = get_remaining_meal_rooms(df)
    if remaining:
        chips = "".join(
            f"<a href='#target_{room}' target='_self' class='meal-chip'>{room}</a>"
            for room in remaining
        )
        html = f"""
            <div class='meal-box'>
                <div class='meal-title'>🍚 밥교대 남은 방 <span class='meal-count'>{len(remaining)}</span></div>
                <div>{chips}</div>
            </div>
        """
    else:
        html = """
            <div class='meal-box meal-done'>
                <div class='meal-title'>🍚 밥교대 완료</div>
            </div>
        """
    st.markdown(html, unsafe_allow_html=True)

# --- UI 렌더링 ---
def render_final_card(room_name, df):
    st.markdown(f"<div id='target_{room_name}' style='scroll-margin-top: 100px;'></div>", unsafe_allow_html=True)
    row = df[df['Room'] == room_name].iloc[0]
    status = row['Status']
    
    # Memo와 Shift 값 가져오기
    current_memo = row['Memo']
    current_shift = row['Shift']
    
    # 카드 헤더 색상 설정
    if "수술" in status:
        bg_color = "#E0F2FE"; text_color = "#0EA5E9"
    elif "대기" in status:
        bg_color = "#FFF3E0"; text_color = "#EF6C00"
    else: 
        bg_color = "#E0E0E0"; text_color = "#000000"

    current_icon = status.split(" ")[0] 

    with st.container(border=True):
        # 상단: 방 이름 + 수술상태 선택
        c1, c2 = st.columns([0.6, 1.2], gap="medium")
        with c1:
            st.markdown(f"""
                <div style='
                    width: 100%; font-size: 1.2rem; font-weight: bold;
                    color: {text_color}; background-color: {bg_color};
                    padding: 2px 0px; border-radius: 6px; text-align: center;
                    display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 5px;
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
            
        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

        # [변경] 하단: 방으로 보내기(왼쪽) + 교대 상태 선택(오른쪽)
        s1, s_btn, s2 = st.columns([1.15, 0.4, 1], gap="small")
        
        key_msg = f"msg_{room_name}"
        key_shift = f"shift_{room_name}"
        
        # 1. 방으로 보낼 메시지 + 보내기 버튼
        s1.text_input("방으로 보내기", key=key_msg, placeholder="방으로 보내기", label_visibility="collapsed")
        s_btn.button("📨", key=f"send_{room_name}", on_click=send_room_callback, args=(room_name,),
                     help=f"{room_name} 컴퓨터로 보내기")
        
        # 2. 교대/식사 상태 (선택)
        s2.selectbox("교대", SHIFT_OPTIONS, key=key_shift, label_visibility="collapsed",
                      index=SHIFT_OPTIONS.index(current_shift) if current_shift in SHIFT_OPTIONS else 0,
                      on_change=update_data_callback, args=(room_name, 'Shift', key_shift))

        st.markdown(f"""
            <div style='text-align: right; font-size: 10px; color: #aaa; margin-top: 2px;'>
                Update: {row['Last_Update']}
            </div>
            """, unsafe_allow_html=True)

def render_zone(col, title, zone_list, df):
    with col:
        st.markdown(f"<h4 style='margin-bottom: 5px;'>{title}</h4>", unsafe_allow_html=True)
        for room in zone_list:
            render_final_card(room, df)

# --- 메인 실행 ---
st.set_page_config(page_title="JNUH OR", layout="wide")

check_daily_reset() # 리셋 체크

st.markdown("<div id='top'></div>", unsafe_allow_html=True)

# CSS 스타일 정의 (기존과 동일하게 유지하되 필요한 부분만 수정)
st.markdown("""
    <style>
    .block-container {
        padding-top: 30px !important;
        padding-bottom: 5rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    h3 { margin-top: 0 !important; padding-top: 2px !important; }
    [data-testid="stVerticalBlock"] { gap: 5px !important; }
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] { gap: 2rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] { margin-bottom: 2px !important; padding: 0px !important; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { padding-top: 6px !important; padding-bottom: 6px !important; }
    h4 { margin-top: 0px !important; margin-bottom: 10px !important; padding-bottom: 0px !important; z-index: 1; position: relative; }
    hr { margin-top: 0.2rem !important; margin-bottom: 0.5rem !important; }
    
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        padding-top: 0px; padding-bottom: 0px; padding-left: 5px; 
        height: 32px; min-height: 32px; font-size: 14px; display: flex; align-items: center; border-color: #E0E0E0;
    }
    div[data-testid="stTextInput"] div[data-baseweb="input"] {
        background-color: #FFFFFF !important; border: 1px solid #CCCCCC !important; border-radius: 4px;
        padding-top: 0px; padding-bottom: 0px; height: 32px; min-height: 32px;
    }
    div[data-testid="stTextInput"] input {
        background-color: #FFFFFF !important; color: #000000 !important; font-size: 14px; padding: 0px 5px !important;
    }
    div[data-testid="stTextArea"] textarea {
        background-color: #FFF9C4 !important; color: #333 !important; font-size: 14px !important; line-height: 1.5;
    }

    .link-container { display: flex; width: 100%; justify-content: space-between; gap: 2px; margin-bottom: 5px; }
    .quick-link {
        flex: 1; display: block; text-decoration: none; text-align: center; padding: 8px 0;
        font-size: 11px; font-weight: bold; white-space: nowrap; border-radius: 8px;
        transition: opacity 0.2s; box-sizing: border-box;
    }
    .quick-link:hover { opacity: 0.8; }

    /* [추가] 밥교대 남은 방 박스 */
    .meal-box {
        background-color: #FFF0F5; border: 2px solid #FF4081; border-radius: 10px;
        padding: 8px 10px; margin-top: 10px; margin-bottom: 22px;
    }
    .meal-box.meal-done { background-color: #E8F5E9; border-color: #4CAF50; }
    .meal-title { font-weight: bold; font-size: 15px; color: #C2185B; margin-bottom: 6px; }
    .meal-done .meal-title { color: #2E7D32; margin-bottom: 0; }
    .meal-count {
        display: inline-block; background-color: #FF4081; color: #FFFFFF; border-radius: 10px;
        padding: 0 8px; font-size: 13px; margin-left: 4px;
    }
    .meal-chip {
        display: inline-block; text-decoration: none !important; background-color: #FFFFFF;
        color: #C2185B !important; border: 1px solid #FF4081; border-radius: 6px;
        padding: 3px 10px; margin: 0 4px 4px 0; font-size: 14px; font-weight: bold;
    }
    .meal-chip:hover { background-color: #FCE4EC; }

    /* OFF 전공의 multiselect 스타일 */
    div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
        background-color: #FFCDD2 !important;
        border: 1px solid #E53935 !important;
        border-radius: 6px !important;
    }
    div[data-testid="stMultiSelect"] span[data-baseweb="tag"] span {
        color: #C62828 !important; font-weight: bold !important;
        font-size: 13px !important;
    }

    div[data-testid="stButton"] button {
        background-color: #E6F2FF !important; color: #0057A4 !important; border: 1px solid #0057A4 !important;
        border-radius: 8px !important; font-weight: bold !important; transition: all 0.3s ease;
        width: auto !important; max-width: fit-content !important; padding: 2px 12px !important;
        min-width: 0 !important; font-size: 12px !important; min-height: 34px !important; line-height: 1.2 !important;
        display: inline-flex !important; justify-content: center !important; align-items: center !important;
    }
    div[data-testid="stButton"] button p { color: #0057A4 !important; font-size: 13px !important; line-height: 1 !important; }
    div[data-testid="stButton"] button:hover { background-color: #CCE4FF !important; border-color: #004080 !important; }
    div[data-testid="stButton"] button:hover p { color: #004080 !important; }



    @media (max-width: 900px) {
        /* 최상위 3열(A|B|공지) → 모바일: 공지 위 전체, A/B 아래 2열 */
        .block-container > div > div > div[data-testid="stHorizontalBlock"] {
            display: grid !important;
            grid-template-columns: 1fr 1fr !important;
            grid-template-rows: auto auto !important;
            column-gap: 8px !important;
            row-gap: 22px !important;
        }
        /* 공지(3번째) → 위, 전체 2열 차지 */
        .block-container > div > div > div[data-testid="stHorizontalBlock"] > div:nth-child(3) {
            grid-column: 1 / span 2 !important;
            grid-row: 1 !important;
        }
        /* A구역(1번째) → 아래 왼쪽 */
        .block-container > div > div > div[data-testid="stHorizontalBlock"] > div:nth-child(1) {
            grid-column: 1 !important;
            grid-row: 2 !important;
        }
        /* B구역(2번째) → 아래 오른쪽 */
        .block-container > div > div > div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
            grid-column: 2 !important;
            grid-row: 2 !important;
        }
        /* 카드 내부 horizontal block은 row 유지 */
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stHorizontalBlock"] { flex-direction: row !important; gap: 6px !important; }
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stHorizontalBlock"] > div { order: unset !important; margin-bottom: 0px !important; }


        .floating-top-btn {
            position: fixed; bottom: 20px; left: 15px; width: 50px; height: 50px; background-color: #FFFFFF; color: #333;
            border: 2px solid #ddd; border-radius: 15px; text-align: center; line-height: 50px; font-size: 20px;
            font-weight: bold; text-decoration: none; box-shadow: 0px 4px 15px rgba(0,0,0,0.2);
            z-index: 99999 !important; pointer-events: auto !important; transition: all 0.2s;
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

# ── 3열 레이아웃: A구역 | B구역 | 공지 (데스크탑 기준) ──
# 모바일에서는 CSS로 재배치: 공지 위 전체 → A/B 2열 아래
col_a, col_b, col_notice = st.columns([1, 1, 0.55], gap="small")

render_zone(col_a, "A 구역", ZONE_A, df)
render_zone(col_b, "B / C / 기타", ZONE_B, df)

# [추가] 방으로 보내기 결과 표시
if "room_result" in st.session_state:
    _kind, _text = st.session_state.pop("room_result")
    if _kind == "ok":
        st.toast(_text, icon="📨")
    else:
        st.toast(_text, icon="⚠️")

with col_notice:
    # [추가] 밥교대 남은 방 (오른쪽 열 맨 위 / 모바일에서는 화면 맨 위)
    render_remaining_meal_box(df)

    # ---------------------------
    # OFF 전공의
    # ---------------------------
    current_off_list = [x for x in load_off_residents() if x in OFF_OPTIONS]

    if "off_select" not in st.session_state:
        st.session_state["off_select"] = current_off_list
    else:
        # 선택지에서 빠진 이름이 남아 있으면 오류가 나므로 정리
        st.session_state["off_select"] = [x for x in st.session_state["off_select"] if x in OFF_OPTIONS]

    def save_off_callback():
        save_off_residents(st.session_state.get("off_select", []))

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
    off_label_col, off_select_col = st.columns([0.18, 0.82])
    with off_label_col:
        st.markdown(
            "<div style='font-weight: bold; color: #C62828; font-size: 17px; padding-top: 4px;'>OFF</div>",
            unsafe_allow_html=True
        )
    with off_select_col:
        st.multiselect(
            "OFF 전공의",
            options=OFF_OPTIONS,
            key="off_select",
            label_visibility="collapsed",
            placeholder="선택...",
            on_change=save_off_callback
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    notice_time = load_notice_time()
    if notice_time == "":
        notice_time = "-"

    # 공지사항 헤더
    notice_title_col, notice_send_col = st.columns([0.72, 0.28], gap="small")
    with notice_title_col:
        st.markdown(f"""
            <div style="padding-top:2px; line-height:1.25; margin-bottom:2px;">
                <div style="font-weight:bold; font-size:1.1rem; white-space:nowrap;">📢 공지사항</div>
                <div style="font-size:11px; color:#D32F2F; font-weight:bold; margin-top:4px;">Update: {notice_time}</div>
            </div>
        """, unsafe_allow_html=True)
    with notice_send_col:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        send_notice = st.button("📣 발송", key="send_notice_btn", use_container_width=True)

    st.text_area(
        "공지사항 내용", key="notice_area", height=120, label_visibility="collapsed",
        placeholder="전달사항을 입력하세요..."
    )

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    save_only = st.button("변경사항 저장", key="save_notice_btn", use_container_width=False)

    if save_only:
        result = save_notice_callback(send_push=False)
        save_data(df)
        if result.get("saved"):
            st.toast("공지사항이 저장되었습니다!", icon="✅")
        else:
            st.error(f"공지 저장 실패: {result.get('reason', 'unknown error')}")

    if send_notice:
        result = save_notice_callback(send_push=True)
        save_data(df)
        if result.get("reason") == "empty":
            st.warning("공지 내용을 먼저 입력하세요.")
        elif result.get("saved") and result.get("sent"):
            code = result.get("status_code")
            st.success(f"공지 저장 및 알림 발송 완료 ({code})")
        elif result.get("saved") and not result.get("sent"):
            code = result.get("status_code")
            detail = result.get("response_text", "")
            st.error(f"공지는 저장됐지만 알림 발송은 실패했습니다. status={code}, detail={detail}")
        else:
            st.error(f"공지 저장 실패: {result.get('reason', 'unknown error')}")

    # ---------------------------
    # [추가] 중앙 컴퓨터로만 보내기 (공지사항에는 저장되지 않음)
    # ---------------------------
    def send_center_callback():
        msg = st.session_state.get("center_msg", "").strip()
        if not msg:
            st.session_state["center_result"] = ("warn", "보낼 내용을 먼저 입력하세요.")
            return
        result = send_ntfy(
            title=f"JNUH OR Center ({get_korean_time_str()})",  # 제목은 영어만 가능 (한글 넣으면 발송 실패)
            message=msg,
            priority="high",
            url=NTFY_CENTER_URL
        )
        if result.get("ok"):
            st.session_state["center_msg"] = ""
            st.session_state["center_result"] = ("ok", "중앙 컴퓨터로 보냈습니다.")
        else:
            st.session_state["center_result"] = ("err", f"발송 실패: status={result.get('status_code')}, {result.get('text', '')}")

    st.markdown("<div style='margin-top: 12px; margin-bottom: 4px; font-weight: bold; font-size: 14px;'>🖥️ 중앙으로 보내기</div>", unsafe_allow_html=True)
    center_input_col, center_btn_col = st.columns([0.72, 0.28], gap="small")
    with center_input_col:
        st.text_input("중앙 메시지", key="center_msg", label_visibility="collapsed", placeholder="중앙 컴퓨터에만 뜹니다")
    with center_btn_col:
        st.button("보내기", key="send_center_btn", on_click=send_center_callback)

    if "center_result" in st.session_state:
        kind, text = st.session_state.pop("center_result")
        if kind == "ok":
            st.toast(text, icon="✅")
        elif kind == "warn":
            st.warning(text)
        else:
            st.error(text)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    st.markdown("<div style='margin-top: 3px; margin-bottom: 8px; font-weight: bold; font-size: 14px;'>🚀 빠른 이동</div>", unsafe_allow_html=True)

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

st.markdown("<a href='#top' class='floating-top-btn'>🔝</a>", unsafe_allow_html=True)
