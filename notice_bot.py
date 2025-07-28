import os, sys, json, re, requests, traceback
from bs4 import BeautifulSoup

# ── 환경 변수 ──────────────────────────────────────────────
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
if not WEBHOOK_URL:
    try:
        with open("config.json", encoding="utf-8") as f:
            WEBHOOK_URL = json.load(f)["DISCORD_WEBHOOK_URL"]
    except Exception:
        sys.exit("❌ DISCORD_WEBHOOK_URL 설정이 없습니다")

NOTICE_URL = "https://scatch.ssu.ac.kr/공지사항/"
LAST_FILE  = "last_notice_id.txt"
UA_HEADER  = {"User-Agent": "Mozilla/5.0"}

# ── 상태 파일 I/O ─────────────────────────────────────────
def read_last():
    try:
        return open(LAST_FILE, encoding="utf-8").read().strip()
    except FileNotFoundError:
        return None

def write_last(nid):
    with open(LAST_FILE, "w", encoding="utf-8") as f:
        f.write(str(nid))

# ── 공지 목록 파싱 ─────────────────────────────────────────
def fetch_new_notices(last_id):
    """목록 페이지에서 (id,title,link) 튜플을 최신→오래된 순으로 반환.
       last_id 전 글까지 모으면 중단."""
    resp = requests.get(NOTICE_URL, headers=UA_HEADER, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    notices = []
    for a in soup.select("ul.notice-lists li a"):
        link = a["href"]
        if link.startswith("/"):
            link = "https://scatch.ssu.ac.kr" + link
        m = re.search(r"[?&]num=(\d+)", link)
        nid = m.group(1) if m else link
        if nid == last_id:
            break
        title = a.get_text(" ", strip=True)
        notices.append((nid, title, link))

    return list(reversed(notices))  # 오래된 것부터 전송하기 위해 역전환

# ── 디스코드 전송 ─────────────────────────────────────────
def send(msg):
    requests.post(WEBHOOK_URL, json={"content": msg}, timeout=10)

# ── 메인 ──────────────────────────────────────────────────
def main():
    last_id = read_last()
    try:
        new_posts = fetch_new_notices(last_id)
    except Exception:
        traceback.print_exc()
        sys.exit("🚫 공지 파싱 실패")

    if not new_posts:
        print("⏸ 새 공지 없음")
        return

    for nid, title, link in new_posts:
        send(f"📢 **새 학사 공지**\n{title}\n{link}")
        write_last(nid)
        print(f"✅ 전송: {nid} – {title}")

if __name__ == "__main__":
    main()
