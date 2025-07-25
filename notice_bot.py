import os, re, sys, requests, textwrap, hashlib, datetime as dt, email.utils
import xml.etree.ElementTree as ET
import openai
from bs4 import BeautifulSoup

# ── 환경변수 ───────────────────────────────────────────────────
WEBHOOK   = os.getenv("DISCORD_WEBHOOK_URL")       # 디스코드 웹훅 (필수)
OPENAI_KEY = os.getenv("OPENAI_API_KEY")           # GPT 요약 (선택)
openai.api_key = OPENAI_KEY

# 카테고리 전용 RSS (slug 확인: /category/notice/feed or /category/공지사항/feed)
RSS_URL   = "https://scatch.ssu.ac.kr/category/notice/feed"
ID_FILE   = "last_notice_id.txt"

HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 15
md5 = lambda s: hashlib.md5(s.encode()).hexdigest()

# ── RSS 파싱 ──────────────────────────────────────────────────
def latest_item():
    xml = requests.get(RSS_URL, headers=HEADERS, timeout=TIMEOUT).text
    root = ET.fromstring(xml)
    latest = None
    latest_date = dt.datetime.min.replace(tzinfo=dt.timezone.utc)

    for item in root.findall("./channel/item"):
        pub_raw = item.findtext("pubDate", "")
        try:
            pub_dt = email.utils.parsedate_to_datetime(pub_raw)
        except Exception:
            continue
        if pub_dt > latest_date:
            latest_date = pub_dt
            latest = item
    return latest

def get_post():
    item = latest_item()
    if not item:
        return None, None, None, None

    title = item.findtext("title", "").strip()
    link  = item.findtext("link", "").strip()
    guid  = item.findtext("guid", link).strip() or link

    # 본문 HTML → 텍스트
    html = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "")
    body = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    body = textwrap.shorten(body, 4000)            # GPT 토큰 안전용
    return title, link, guid, body

# ── GPT 3 줄 요약 ─────────────────────────────────────────────
def summarize(txt):
    if not OPENAI_KEY:
        return "(요약 생략 – OPENAI_API_KEY 미설정)"

    prompt = "다음 학사 공지를 한국어로 **최대 3줄** 핵심 요약:\n" + txt
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

# ── 상태 파일 ────────────────────────────────────────────────
def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None
def write_last(g): open(ID_FILE, "w").write(g)

# ── 디스코드 전송 ────────────────────────────────────────────
def send(msg): requests.post(WEBHOOK, json={"content": msg}, timeout=10)

# ── 메인 ─────────────────────────────────────────────────────
def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_URL 시크릿이 없습니다")

    title, link, guid, body = get_post()
    if not link:
        print("🚫 RSS 파싱 실패"); return
    if guid == read_last():
        print("⏸ 새 글 없음"); return

    summary = summarize(body)
    send(f"📚 **{title}**\n{summary}\n{link}")
    write_last(guid)
    print("✅ 공지 + 요약 전송 완료")

if __name__ == "__main__":
    main()
