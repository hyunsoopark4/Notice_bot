# sw_bot.py
# 소프트웨어학부 공지(https://sw.ssu.ac.kr/bbs/board.php?bo_table=notice)에서
# 가장 최신 글 1건을 읽어, 새 글이면 디스코드 웹훅으로 알림

import os, re, sys, requests
from bs4 import BeautifulSoup

WEBHOOK = os.getenv("DISCORD_WEBHOOK_SW")      # 레포 Secrets에 넣을 값
LIST_URL = "https://sw.ssu.ac.kr/bbs/board.php?bo_table=notice"
ID_FILE = "last_sw_id.txt"                     # 가장 최근 글 ID 저장

def get_latest():
    html = requests.get(LIST_URL, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    a = soup.find("a", href=lambda h: h and "wr_id=" in h)   # 첫 글 링크
    if not a:
        return None, None, None

    link = a["href"]
    if link.startswith("/"):
        link = "https://sw.ssu.ac.kr" + link
    title = a.get_text(strip=True)
    wr_id = re.search(r"wr_id=(\d+)", link).group(1)
    return wr_id, title, link

def read_last():
    try:
        return open(ID_FILE).read().strip()
    except FileNotFoundError:
        return None

def write_last(wr_id):
    with open(ID_FILE, "w") as f:
        f.write(wr_id)

def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_SW 시크릿이 없습니다")

    wr_id, title, link = get_latest()
    if not wr_id:
        print("❌ 공지 파싱 실패")
        return

    if wr_id == read_last():
        print("⏸ 새 글 없음")
        return

    send(f"📝 **소프트웨어학부 새 공지**\n{title}\n{link}")
    write_last(wr_id)
    print("✅ 디스코드 전송 완료")

if __name__ == "__main__":
    main()
