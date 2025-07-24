# me_bot.py
# Cloudflare Worker(한국 IP) 프록시 URL만 호출해서
# 기계공학부 최신 공지를 가져오고, 새 글일 때만 디스코드로 알림.

import os, re, sys, requests
from bs4 import BeautifulSoup
from datetime import datetime

# ── 환경변수 / 상수 ────────────────────────────────────────────────
WEBHOOK  = os.getenv("DISCORD_WEBHOOK_ME")                 # 디스코드 웹훅
# ① 아래 URL을 **본인 워커 주소**로 바꿔 주세요
LIST_URL = (
    "https://me-proxy.<subdomain>.workers.dev/"
    "?url=https://me.ssu.ac.kr/notice/notice01.php"
)
ID_FILE  = "last_me_id.txt"
HEADERS  = {"User-Agent": "Mozilla/5.0"}

TIMEOUT  = 15      # 초

# ── 헬퍼 함수 ─────────────────────────────────────────────────────
def parse_date(txt: str) -> datetime:
    return datetime.strptime(txt.strip().replace(".", "-"), "%Y-%m-%d")

def get_latest():
    """게시 날짜가 가장 최신인 글 1건(wr_id, 제목, 링크) 반환"""
    r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
    if r.status_code != 200:
        print(f"🚫 Worker 응답 오류 {r.status_code}")
        return None, None, None

    soup = BeautifulSoup(r.text, "html.parser")
    latest_link, latest_dt = None, datetime.min

    for tr in soup.select("tr"):
        date_td = tr.find("td", string=re.compile(r"\d{4}.\d{2}.\d{2}"))
        link_a  = tr.find("a", href=lambda h: h and "wr_id=" in h)
        if not (date_td and link_a):
            continue
        try:
            cur_dt = parse_date(date_td.get_text())
        except ValueError:
            continue
        if cur_dt >= latest_dt:
            latest_dt, latest_link = cur_dt, link_a

    if not latest_link:
        return None, None, None

    link = latest_link["href"]
    if link.startswith("/"):
        link = "https://me.ssu.ac.kr" + link
    title = latest_link.get_text(strip=True)
    wid = re.search(r"wr_id=(\d+)", link).group(1)
    return wid, title, link

def read_last():
    try:
        return open(ID_FILE).read().strip()
    except FileNotFoundError:
        return None

def write_last(wid):
    with open(ID_FILE, "w") as f:
        f.write(wid)

def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

# ── 메인 루틴 ─────────────────────────────────────────────────────
def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_ME 시크릿이 없습니다")

    wid, title, link = get_latest()
    if not wid:
        print("⏸  글을 가져오지 못했습니다 – 다음 주기 대기")
        return

    if wid == read_last():
        print("⏸  새 글 없음")
        return

    send(f"🔧 **기계공학부 새 공지**\n{title}\n{link}")
    write_last(wid)
    print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
