# notice_bot.py ─ 학사공지 RSS + GPT 3줄 요약 (feedparser 견고 버전)
import os, re, sys, requests, textwrap, time, hashlib
import feedparser, openai, html2text
from bs4 import BeautifulSoup

# ── 환경 변수 ─────────────────────────────────────────────
WEBHOOK  = os.getenv("DISCORD_WEBHOOK_URL")       # 디스코드 웹훅
OPENAI_KEY = os.getenv("OPENAI_API_KEY")          # 선택
openai.api_key = OPENAI_KEY

RSS_URL  = "https://scatch.ssu.ac.kr/category/notice/feed"  # ← 학사공지 전용 피드
ID_FILE  = "last_notice_id.txt"

# ── 최신 글 가져오기 ──────────────────────────────────────
def fetch_latest():
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        return None

    # published_parsed 기준 최신 1건
    entry = max(feed.entries,
                key=lambda e: e.published_parsed or time.gmtime(0))

    title = entry.title.strip()
    link  = entry.link.strip()
    guid  = getattr(entry, "id", link).strip()

    # content:encoded > summary > description
    raw_html = ""
    for key in ("content", "summary", "description"):
        if hasattr(entry, key):
            raw_html = (entry.content[0].value if key == "content" else getattr(entry, key))
            break
    body_txt = BeautifulSoup(raw_html, "html.parser").get_text(" ", strip=True)
    body_txt = textwrap.shorten(body_txt, 4000)   # GPT 토큰 안전

    return title, link, guid, body_txt

# ── 요약 ──────────────────────────────────────────────────
def summarize(txt):
    if not OPENAI_KEY:
        return "(요약 생략 – OPENAI_API_KEY 미설정)"

    prompt = "다음 학사 공지 본문을 한국어로 최대 3줄 핵심 요약:\n" + txt
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120, temperature=0.3)
        return res.choices[0].message.content.strip()
    except Exception as e:
        print("GPT 요약 실패:", e)
        return "(요약 실패)"

# ── 파일 IO ──────────────────────────────────────────────
def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None
def write_last(x): open(ID_FILE, "w").write(x)

# ── 디스코드 전송 ────────────────────────────────────────
def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

# ── 메인 ────────────────────────────────────────────────
def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_URL 시크릿이 없습니다")

    post = fetch_latest()
    if not post:
        sys.exit("🚫 RSS 파싱 실패 (entries 없음)")

    title, link, guid, body = post
    if guid == read_last():
        print("⏸ 새 글 없음"); return

    summary = summarize(body)
    send(f"📚 **{title}**\n{summary}\n{link}")
    write_last(guid)
    print("✅ 공지 + 요약 전송 완료")

if __name__ == "__main__":
    main()
