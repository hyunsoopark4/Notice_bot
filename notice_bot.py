# notice_bot.py  (복붙 OK)

import os, sys, json, re, requests
from bs4 import BeautifulSoup

# 1. 디스코드 웹훅 읽기 -------------------------------------------------
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
if not WEBHOOK_URL:
    try:
        with open("config.json", encoding="utf-8") as f:
            WEBHOOK_URL = json.load(f)["DISCORD_WEBHOOK_URL"]
    except (FileNotFoundError, KeyError):
        sys.exit("❌ DISCORD_WEBHOOK_URL 설정이 없습니다")

# 2. 게시판 URL & 상태파일 ---------------------------------------------
NOTICE_URL = "https://scatch.ssu.ac.kr/%EA%B3%B5%EC%A7%80%EC%82%AC%ED%95%AD/"
LAST_NOTICE_FILE = "last_notice_id.txt"

# 3. 최신 글 한 건 긁어오기 ---------------------------------------------
def get_latest_notice():
    resp = requests.get(
        NOTICE_URL,
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0"}  # 봇 차단 회피용
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # ★ 여기!  ─────────────────────────────────────
    link_tag = soup.select_one("ul.notice-lists li a")
    # ─────────────────────────────────────────────

    if not link_tag:
        return None, None, None        # 구조가 또 바뀌면 None 반환

    link = link_tag["href"]
    if link.startswith("/"):
        link = "https://scatch.ssu.ac.kr" + link

    title = link_tag.get_text(strip=True)

    # 링크에 ?num=12345 가 들어 있으니 그 숫자를 공지 ID로 사용
    m = re.search(r"[?&]num=(\d+)", link)
    notice_id = m.group(1) if m else link   # 혹시 못 찾으면 링크 자체

    return notice_id, title, link

# 4. 상태 파일 read / write --------------------------------------------
def read_last_id():
    try:
        with open(LAST_NOTICE_FILE, encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def write_last_id(nid):
    with open(LAST_NOTICE_FILE, "w", encoding="utf-8") as f:
        f.write(str(nid))

# 5. 디스코드 전송 -------------------------------------------------------
def send(msg):
    requests.post(WEBHOOK_URL, json={"content": msg}, timeout=10)

# 6. 메인 루틴 ----------------------------------------------------------
def main():
    last_id = read_last_id()
    notice_id, title, link = get_latest_notice()

    if not notice_id:
        print("❌ 공지 셀렉터 불일치 – 구조를 다시 확인하세요")
        return

    if notice_id != last_id:
        send(f"📢 **새 학사 공지**\n{title}\n{link}")
        write_last_id(notice_id)
        print("✅ 새 공지를 디스코드로 전송했습니다")
    else:
        print("⏸  새 공지가 없습니다")

if __name__ == "__main__":
    main()
