# sw_bot.py – 날짜 기준으로 최신 글 판단 + 중복 알림 방지
import os, re, sys, requests
from bs4 import BeautifulSoup
from datetime import datetime

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_SW")
LIST_URL = "https://sw.ssu.ac.kr/bbs/board.php?bo_table=notice"
ID_FILE  = "last_sw_id.txt"

def parse_date(td_text: str) -> datetime:
    """게시판 날짜 문자열(YYYY-MM-DD) → datetime 객체"""
    return datetime.strptime(td_text.strip(), "%Y-%m-%d")

def get_latest():
    """표 전체에서 날짜가 가장 최근인 글 1건을 반환"""
    html = requests.get(LIST_URL, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    latest = None
    latest_dt = datetime.min

    for tr in soup.select("tr"):
        # 날짜 셀 찾기 (td에 'date'가 포함된 클래스)
        date_td = tr.find("td", class_=lambda c: c and "date" in c)
        link_a  = tr.find("a", href=lambda h: h and "wr_id=" in h)
        if not (date_td and link_a):
            continue

        try:
            cur_dt = parse_date(date_td.get_text())
        except ValueError:
            continue

        if cur_dt >= latest_dt:          # 최신 날짜 갱신
            latest_dt = cur_dt
            latest    = link_a

    if not latest:
        return None, None, None

    link = latest["href"]
    if link.startswith("/"):
        link = "https://sw.ssu.ac.kr" + link
    title = latest.get_text(strip=True)
    wr_id = re.search(r"wr_id=(\d+)", link).group(1)
    return wr_id, title, link

def read_last():
    try:
        return open(ID_FILE).read().strip()
    except FileNotFoundError:
        return None

def write_last(wid: str):
    with open(ID_FILE, "w") as f:
        f.write(wid)

def send(msg: str):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_SW 시크릿이 없습니다")

    wid, title, link = get_latest()
    if not wid:
        print("❌ 최신 글 파싱 실패")
        return

    if wid == read_last():
        print("⏸  새 글 없음")
        return

    send(f"📝 **소프트웨어학부 새 공지**\n{title}\n{link}")
    write_last(wid)
    print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
