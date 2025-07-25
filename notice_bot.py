import os, sys, time, textwrap, hashlib, requests, feedparser, openai
from bs4 import BeautifulSoup

# ── 환경 변수 ─────────────────────────────────────────────
WEBHOOK      = os.getenv("DISCORD_WEBHOOK_URL")        # 필수
OPENAI_KEY   = os.getenv("OPENAI_API_KEY")             # 선택
openai.api_key = OPENAI_KEY

SITE_BASE = "https://scatch.ssu.ac.kr"
CATEGORY_PAGE = f"{SITE_BASE}/공지사항"      # 카테고리 URL (한글 가능)
FALLBACK_FEED = f"{SITE_BASE}/feed"         # 사이트 전체 RSS
ID_FILE = "last_notice_id.txt"

# ── RSS URL 탐색 ──────────────────────────────────────────
def find_feed_url():
    try:
        html = requests.get(CATEGORY_PAGE, timeout=15).text
        soup = BeautifulSoup(html, "html.parser")
        alt = soup.find("link", rel="alternate",
                        attrs={"type": "application/rss+xml"})
        if alt and "feed" in alt.get("href", ""):
            return alt["href"]
    except Exception as e:
        print("feed link 찾기 실패:", e)
    return FALLBACK_FEED

# ── 최신 글 가져오기 ──────────────────────────────────────
def latest_post(feed_url):
    feed = feedparser.parse(feed_url)
    if not feed.entries:
        return None
    entry = max(feed.entries,
                key=lambda e: e.published_parsed or time.gmtime(0))
    title = entry.title.strip()
    link  = entry.link.strip()
    guid  = getattr(entry, "id", link)

    raw = getattr(entry, "content", [{}])[0].get("value") \
          or getattr(entry, "summary", "") \
          or getattr(entry, "description", "")
    txt = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    txt = textwrap.shorten(txt, 4000)
    return title, link, guid, txt

# ── 요약 ─────────────────────────────────────────────────
def summarize(txt):
    if not OPENAI_KEY:
        return "(요약 생략 – OPENAI_API_KEY 미설정)"
    prompt = "다음 학사 공지 본문을 한국어로 최대 3줄로 요약:\n" + txt
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120, temperature=0.3,
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        print("GPT 요약 실패:", e)
        return "(요약 실패)"

# ── 상태 파일 ────────────────────────────────────────────
read_last  = lambda: open(ID_FILE).read().strip() if os.path.exists(ID_FILE) else None
write_last = lambda g: open(ID_FILE, "w").write(g)

# ── 디스코드 전송 ────────────────────────────────────────
def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

# ── 메인 ─────────────────────────────────────────────────
def main():
    if not WEBHOOK:
        sys.exit("❌  DISCORD_WEBHOOK_URL 시크릿 누락")

    feed_url = find_feed_url()
    print("사용 RSS:", feed_url)

    post = latest_post(feed_url)
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
