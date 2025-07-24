import os, re, sys, requests
from bs4 import BeautifulSoup
from datetime import datetime

WEBHOOK = os.getenv("DISCORD_WEBHOOK_ME")                # 시크릿에 추가
LIST_URL = "https://me.ssu.ac.kr/notice/notice01.php"
ID_FILE = "last_me_id.txt"                               # 상태 저장

def parse_date(text: str) -> datetime:
    text = text.strip().replace(".", "-")                # 2025.07.24 → 2025-07-24
    return datetime.strptime(text, "%Y-%m-%d")

def get_latest():
    """표 전체에서 날짜가 가장 최근인 글 하나(wr_id, 제목, 링크) 반환"""
    html = requests.get(LIST_URL, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    latest_link, latest_dt = None, datetime.min

    # 학과 사이트는 보통 <tr>에 글이 들어 있음
    for tr in soup.select("tr"):
        # 날짜 셀(보통 <td class=date> 또는 날짜포맷 텍스트) 찾기
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
    wr_id = re.search(r"wr_id=(\d+)", link).group(1)
    return wr_id, title, link

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

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_ME 시크릿이 없습니다")

    wid, title, link = get_latest()
    if not wid:
        print("❌ 최신 글 파싱 실패")
        return

    if wid == read_last():
        print("⏸  새 글 없음")
        return

    send(f"🔧 **기계공학부 새 공지**\n{title}\n{link}")
    write_last(wid)
    print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
