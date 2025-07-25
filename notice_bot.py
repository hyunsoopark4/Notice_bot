# notice_bot.py  ― 학사공지 + GPT 3줄 요약 (웹훅 변수 = DISCORD_WEBHOOK_URL)
# ─ 웹훅 env 이름을 DISCORD_WEBHOOK_URL 로 통일 ─
import os, re, sys, requests, hashlib, traceback, textwrap
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import openai

# ── 환경 변수 ──────────────────────────────────────────────────
WEBHOOK    = os.getenv("DISCORD_WEBHOOK_URL")      # 웹훅 이름 변경
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_KEY

LIST_URL  = "https://scatch.ssu.ac.kr/%EA%B3%B5%EC%A7%80%EC%82%AC%ED%95%AD"
LAST_ID   = "last_notice_id.txt"
HEADERS   = {"User-Agent": "Mozilla/5.0"}
TIMEOUT   = 15
md5       = lambda s: hashlib.md5(s.encode()).hexdigest()

# ── 최신 글 링크 & ID ─────────────────────────────────────────
def get_latest_link():
    html = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT).text
    soup = BeautifulSoup(html, "html.parser")
    
    # ── 디버그: 위쪽 링크 3개 class·href 출력 ──
    for a in soup.find_all("a", href=True)[:3]:
        print("DEBUG:", a.get("class"), a["href"])

    
    a = soup.select_one("table.board_list a[href*='articleId']")
    if not a:
        return None, None
    link = urljoin("https://scatch.ssu.ac.kr", a["href"])
    aid  = re.search(r"articleId=(\d+)", link).group(1)
    return aid, link

# ── 본문 스크래핑 ───────────────────────────────────────────────
def fetch_content(link):
    html = requests.get(link, headers=HEADERS, timeout=TIMEOUT).text
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("h4.tit").get_text(" ", strip=True)
    body  = soup.select_one("div.board_view").get_text(" ", strip=True)
    return title, textwrap.shorten(body, 4000)

# ── GPT 3줄 요약 ───────────────────────────────────────────────
def gpt_summary(text):
    prompt = (
        "다음 학사 공지 본문을 최대 3줄로 핵심 요약해 주세요.\n"
        "본문:\n" + text
    )
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=120,
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()

def fallback_summary(text):
    short = textwrap.shorten(text, 200, placeholder="…")
    return short + "\n(요약모드 OFF: OPENAI_API_KEY 미설정)"

# ── 상태 파일 IO ──────────────────────────────────────────────
def read_last():
    try: return open(LAST_ID).read().strip()
    except FileNotFoundError: return None

def write_last(n): open(LAST_ID, "w").write(n)

# ── 디스코드 전송 ─────────────────────────────────────────────
def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

# ── 메인 ───────────────────────────────────────────────────────
def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_URL 시크릿이 없습니다")

    aid, link = get_latest_link()
    if not aid:
        print("🚫 목록 파싱 실패"); return
    if aid == read_last():
        print("⏸ 새 글 없음"); return

    title, body = fetch_content(link)
    try:
        summary = gpt_summary(body) if OPENAI_KEY else fallback_summary(body)
    except Exception as e:
        print("⚠️ GPT 요약 실패:", e)
        summary = fallback_summary(body)

    msg = f"📚 **{title}**\n{summary}\n{link}"
    send(msg)
    write_last(aid)
    print("✅ 공지 + 요약 전송 완료")

if __name__ == "__main__":
    main()
