# np_bot.py
# ────────── ‘비교과 프로그램’ 최신 글을 확인해
#            새 글이면 디스코드 웹훅(다른 채널)으로 알림

import os, sys, re, json, requests
from bs4 import BeautifulSoup

# 필수 시크릿 (레포 Settings → Secrets → Actions)
ID       = os.getenv("SSU_ID")                 # 학번
PW       = os.getenv("SSU_PW")                 # 포털 비밀번호
WEBHOOK  = os.getenv("DISCORD_WEBHOOK_NP")     # 비교과 전용 채널 웹훅

if not all([ID, PW, WEBHOOK]):
    sys.exit("❌ SSU_ID / SSU_PW / DISCORD_WEBHOOK_NP 시크릿이 필요합니다")

LOGIN_URL = "https://path.ssu.ac.kr/user/login.do"
LIST_URL  = "https://path.ssu.ac.kr/ptfol/imng/icmpNsbjtPgm/findIcmpNsbjtPgmList.do"
LAST_FILE = "last_np_id.txt"

def login_session() -> requests.Session:
    """포털 로그인 후 세션 반환(쿠키 기반). 오류 시 종료."""
    s = requests.Session()
    r = s.post(LOGIN_URL, data={"userId": ID, "userPwd": PW}, timeout=10)
    if r.status_code != 200 or "로그아웃" not in r.text:
        sys.exit("❌ 로그인 실패 – ID/PW 확인")
    return s

def get_latest(session):
    """목록 페이지에서 가장 최신 프로그램 1건의 id·제목·기간·링크 추출."""
    r = session.get(LIST_URL, params={
        "paginationInfo.currentPageNo": 1,
        "sort": "0001",
        "operYySh": "2025",
        "operSemCdSh": "0000",
    }, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    # ※ 실제 구조 맞게 한 번만 확인 후 필요하면 셀렉터 수정
    row = soup.select_one("ul.notice-lists li")          # 첫 li = 최신
    if not row:
        return None

    title  = row.select_one(".notice_col4 a").get_text(strip=True)
    period = row.select_one(".notice_col3").get_text(strip=True)
    link_t = row.select_one(".notice_col4 a")["href"]
    link   = "https://path.ssu.ac.kr" + link_t

    # 링크에 num=******* 들어 있으니 그걸 고유 id로 사용
    m = re.search(r"num=(\d+)", link_t)
    pid = m.group(1) if m else link      # fallback

    return pid, title, period, link

def read_last():
    try:
        return open(LAST_FILE, encoding="utf-8").read().strip()
    except FileNotFoundError:
        return None

def write_last(pid):
    with open(LAST_FILE, "w", encoding="utf-8") as f:
        f.write(pid)

def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    sess      = login_session()
    latest    = get_latest(sess)
    if not latest:
        print("❌ 목록 파싱 실패 – 셀렉터 확인 필요")
        return
    pid, title, period, link = latest

    if pid == read_last():
        print("⏸  새 프로그램 없음")
        return

    send(f"🎓 **새 비교과 프로그램**\n제목: {title}\n모집기간: {period}\n바로가기: {link}")
    write_last(pid)
    print("✅ 새 프로그램 알림 전송 완료")

if __name__ == "__main__":
    main()
