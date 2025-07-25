# notice_bot.py ― 학사공지 RSS + GPT 3줄 요약
import os, re, sys, requests, textwrap, hashlib, traceback, xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import openai

# ── 환경 변수 ───────────────────────────────────────────────
WEBHOOK     = os.getenv("DISCORD_WEBHOOK_URL")      # 디스코드 웹훅
OPENAI_KEY  = os.getenv("OPENAI_API_KEY")           # 선택
openai.api_key = OPENAI_KEY

RSS_URL   = "https://scatch.ssu.ac.kr/feed"         # 학사공지 RSS
ID_FILE   = "last_notice_id.txt"
HEADERS   = {"User-Agent": "Mozilla/5.0"}
TIMEOUT   = 15
md5       = lambda s: hashlib.md5(s.encode()).hexdigest()

# ── 최신 글 링크·제목·본문 추출 ───────────────────────────────
def get_latest_post():
    xml = requests.get(RSS_URL, headers=HEADERS, timeout=TIMEOUT).text
    root = ET.fromstring(xml)
    # 첫 <item> 이 최신 글
    item = root.find("./channel/item")
    if item is None:
        return None, None, None
    title = item.findtext("title", "").strip()
    link  = item.findtext("link", "").strip()
    # 본문 HTML → 텍스트
    desc_html = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "")
    text = BeautifulSoup(desc_html, "html.parser").get_text(" ", strip=True)
    return title, link, textwrap.shorten(text, 4000)

# ── 파일 IO ─────────────────────────────────────────────────
def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(n): open(ID_FILE, "w").write(n)

# ── GPT 요약 ────────────────────────────────────────────────
def gpt_summary(txt):
    prompt = ("다음 학사 공지를 한국어로 최대 3줄로 핵심 요약:\n" + txt)
    r = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=120, temperature=0.3,
    )
    return r.choices[0].message.content.strip()

def fallback(txt):
    return textwrap.shorten(txt, 200) + "\n(요약모드 OFF)"

# ── 디스코드 전송 ───────────────────────────────────────────
def send(msg): requests.post(WEBHOOK, json={"content": msg}, timeout=10)

# ── 메인 ───────────────────────────────────────────────────
def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_URL 시크릿이 없습니다")

    title, link, body = get_latest_post()
    if not link:
        print("🚫 RSS 파싱 실패"); return

    post_id = re.search(r"/(\d+)/?$", link)
    pid = post_id.group(1) if post_id else md5(link)
    if pid == read_last():
        print("⏸ 새 글 없음"); return

    try:
        summary = gpt_summary(body) if OPENAI_KEY else fallback(body)
    except Exception as e:
        print("⚠️ GPT 요약 실패:", e)
        summary = fallback(body)

    send(f"📚 **{title}**\n{summary}\n{link}")
    write_last(pid)
    print("✅ 공지 + 요약 전송 완료")

if __name__ == "__main__":
    main()
