# notice_bot.py  ― 학사공지 최신 글 알림 (요약 없이 제목 + 링크만 전송)
#   • 고정 공지·과거 글 문제 없이 "가장 최근 게시" 한 건만 디스코드 전송
#   • GPT·요약 기능 제거 → openai 설치 필요 없음
#   • 웹훅 환경변수: DISCORD_WEBHOOK_URL
# --------------------------------------------------------------
import os, re, sys, hashlib, requests, time
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ── 환경변수 ────────────────────────────────────────────────
WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")  # 디스코드 웹훅 (필수)

SITE   = "https://scatch.ssu.ac.kr"
LIST_URL = f"{SITE}/공지사항"            # 학사공지 목록
ID_FILE  = "last_notice_id.txt"

HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 15
md5     = lambda s: hashlib.md5(s.encode()).hexdigest()

# ── 최신 글 링크 & 제목 추출 ───────────────────────────────
def get_latest():
    j = requests.get(API_URL, timeout=15).json()
    if not j:
        return None, None, None
    post = j[0]
    nid   = str(post["id"])
    title = BeautifulSoup(post["title"]["rendered"], "html.parser").get_text()
    link  = post["link"]
    return nid, title, link
# ── 상태 파일 IO ───────────────────────────────────────────
read_last  = lambda: open(ID_FILE).read().strip() if os.path.exists(ID_FILE) else None
write_last = lambda x: open(ID_FILE, "w").write(x)

# ── 디스코드 전송 ─────────────────────────────────────────
def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

# ── 메인 ─────────────────────────────────────────────────
def main():
    if not WEBHOOK:
        sys.exit("❌  DISCORD_WEBHOOK_URL 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        sys.exit("🚫 목록 파싱 실패 – 페이지 구조 확인 필요")

    if nid == read_last():
        print("⏸ 새 글 없음")
        return

    send(f"📚 **{title}**\n{link}")
    write_last(nid)
    print("✅ 공지 전송 완료")

if __name__ == "__main__":
    main()
