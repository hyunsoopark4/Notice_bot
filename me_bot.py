# me_bot.py  ── A: 날짜 기준 / B: 링크 우선 2단계 탐색
import os, re, sys, time, requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote_plus

WEBHOOK = os.getenv("DISCORD_WEBHOOK_ME")

WORKER  = "https://yellow-unit-fd5c.hyunsoopark4.workers.dev/?url="
SRC     = "http://me.ssu.ac.kr/notice/notice01.php"
LIST_URL = WORKER + quote_plus(SRC)

ID_FILE = "last_me_id.txt"
HEADERS = {"User-Agent": "Mozilla/5.0"}

TIMEOUT = (5, 60)
RETRY   = 3
DATE_RE = re.compile(r"\d{4}[.\-]\d{2}[.\-]\d{2}")

def parse_date(s: str) -> datetime:
    return datetime.strptime(s.replace(".", "-").strip(), "%Y-%m-%d")

def fetch_html():
    for i in range(1, RETRY + 1):
        try:
            r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200:
                print(f"✅ Worker 200 (try {i})"); return r.text
            print(f"⚠️ Worker {r.status_code} (try {i})")
        except requests.RequestException as e:
            print(f"⚠️ Worker err (try {i}) – {e}")
        time.sleep(1)
    return None

def get_latest():
    html = fetch_html()
    if not html: return None, None, None
    soup = BeautifulSoup(html, "html.parser")

    # ── A단계: 날짜 셀 기준
    latest_dt, latest_a = datetime.min, None
    for tr in soup.select("tr"):
        d = tr.find("td", string=DATE_RE)
        a = tr.find("a", href=lambda h: h and "wr_id=" in h)
        if not (d and a): continue
        try:
            cur = parse_date(d.get_text())
        except ValueError:
            continue
        if cur >= latest_dt:
            latest_dt, latest_a = cur, a
    # ── B단계: fallback – wr_id 링크 첫 번째
    if not latest_a:
        latest_a = soup.find("a", href=lambda h: h and "wr_id=" in h)
        if not latest_a:
            return None, None, None

    link = latest_a["href"]
    if link.startswith("/"):
        link = "https://me.ssu.ac.kr" + link
    wid  = re.search(r"wr_id=(\d+)", link).group(1)
    title = latest_a.get_text(strip=True)
    return wid, title, link

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(wid): open(ID_FILE, "w").write(wid)

def send(msg): requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_ME 시크릿이 없습니다")

    wid, title, link = get_latest()
    if not wid:
        print("🚫 파싱 실패 – 다음 주기 스킵"); return
    if wid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"🔧 **기계공학부 새 공지**\n{title}\n{link}")
    write_last(wid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
