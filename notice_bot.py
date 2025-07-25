# notice_bot.py  ― 학사공지 + GPT 3줄 요약 (테이블 파싱 확정판)
import os, re, sys, requests, hashlib, textwrap, traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import openai

# ── 환경 변수 ────────────────────────────────────────────────
WEBHOOK    = os.getenv("DISCORD_WEBHOOK_URL")      # 학사 디스코드 웹훅
OPENAI_KEY = os.getenv("OPENAI_API_KEY")           # (없어도 동작)
openai.api_key = OPENAI_KEY

BASE       = "https://scatch.ssu.ac.kr"
LIST_URL   = f"{BASE}/공지사항"
ID_FILE    = "last_notice_id.txt"
HEADERS    = {"User-Agent": "Mozilla/5.0"}
TIMEOUT    = 15
md5        = lambda s: hashlib.md5(s.encode()).hexdigest()

# ── 최신 글 링크 & ID ───────────────────────────────────────
def get_latest():
    html = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT).text
    soup = BeautifulSoup(html, "html.parser")

    for tr in soup.select("table.board_list tbody tr"):
        a = tr.find("a", href=True)
        if not a:
            continue
        href = urljoin(BASE, a["href"])
        # ID 추출 우선순위: articleId= | 숫자 끝 | md5
        m = re.search(r"articleId=(\d+)", href) or re.search(r"/(\d+)$", href)
        aid = m.group(1) if m else md5(href)
        return aid, href
    return None, None

# ── 본문 스크래핑 ───────────────────────────────────────────
def fetch_content(link):
    html = requests.get(link, headers=HEADERS, timeout=TIMEOUT).text
    soup = BeautifulSoup(html, "html.parser")
    title = soup.select_one("h4.tit").get_text(" ", strip=True)
    body  = soup.select_one("div.board_view").get_text(" ", strip=True)
    return title, textwrap.shorten(body, 4000)

# ── 요약 ───────────────────────────────────────────────────
def gpt_summary(txt):
    prompt = ("다음 학사 공지를 한국어로 3줄 이하 핵심 요약:\n" + txt)
    r = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=120, temperature=0.3,
    )
    return r.choices[0].message.content.strip()

def fallback(txt):
    return textwrap.shorten(txt, 200) + "\n(요약모드 OFF)"

# ── 상태 파일 ──────────────────────────────────────────────
read_last = lambda: open(ID_FILE).read().strip() if os.path.exists(ID_FILE) else None
write_last = lambda x: open(ID_FILE, "w").write(x)

# ── 디스코드 전송 ─────────────────────────────────────────
def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

# ── 메인 ─────────────────────────────────────────────────
def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_URL 시크릿이 없습니다")

    aid, link = get_latest()
    if not aid:
        print("🚫 목록 파싱 실패"); return
    if aid == read_last():
        print("⏸ 새 글 없음"); return

    title, body = fetch_content(link)
    try:
        summary = gpt_summary(body) if OPENAI_KEY else fallback(body)
    except Exception as e:
        print("⚠️ GPT 요약 실패:", e)
        summary = fallback(body)

    send(f"📚 **{title}**\n{summary}\n{link}")
    write_last(aid)
    print("✅ 공지 + 요약 전송 완료")

if __name__ == "__main__":
    main()
