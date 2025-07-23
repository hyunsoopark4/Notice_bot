# notice_bot.py  --- 셀렉터 교정 버전 (바로 덮어쓰기 OK)

import os, sys, json, re, requests
from bs4 import BeautifulSoup

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
if not WEBHOOK_URL:
    try:
        with open("config.json", encoding="utf-8") as f:
            WEBHOOK_URL = json.load(f)["DISCORD_WEBHOOK_URL"]
    except (FileNotFoundError, KeyError):
        sys.exit("DISCORD_WEBHOOK_URL 설정이 없습니다")

NOTICE_URL = "https://scatch.ssu.ac.kr/%EA%B3%B5%EC%A7%80%EC%82%AC%ED%95%AD/"
LAST_NOTICE_FILE = "last_notice_id.txt"

def get_latest_notice():
    resp = requests.get(NOTICE_URL, timeout=10, headers={
        "User-Agent": "Mozilla/5.0"       # 봇 차단 회피용 UA
    })
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # ① <ul class="board-list"> 구조
    link_tag = soup.select_one("ul.board-list li a")
    #    만약 <table> 구조라면 → link_tag = soup.select_one("tbody tr a")

    if not link_tag:
        return None, None, None          # 구조가 또 다르면 여기서 None

    link = link_tag["href"]
    if link.startswith("/"):
        link = f"https://scatch.ssu.ac.kr{link}"

    title = link_tag.get_text(strip=True)

    # 링크 속 num=12345 같은 고유 번호를 notice_id로 사용
    m = re.search(r"[?&]num=(\d+)", link)
    notice_id = m.group(1) if m else link

    return notice_id, title, link

def read_last_id():
    try:
        with open(LAST_NOTICE_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def write_last_id(nid):
    with open(LAST_NOTICE_FILE, "w", encoding="utf-8") as f:
        f.write(str(nid))

def send(msg):
    requests.post(WEBHOOK_URL, json={"content": msg}, timeout=10)

def main():
    last_id = read_last_id()
    notice_id, title, link = get_latest_notice()

    if not notice_id:
        print("❌ 공지 셀렉터 불일치 – 구조를 다시 확인하세요")
        return

    if notice_id != last_id:
        send(f"새 학사 공지 🔔\n{title}\n{link}")
        write_last_id(notice_id)
        print("✅ 새 공지를 디스코드로 전송했습니다")
    else:
        print("⏸  새 공지가 없습니다")

if __name__ == "__main__":
    main()
