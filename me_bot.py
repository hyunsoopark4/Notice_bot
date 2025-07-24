# me_bot.py  ── 날짜 셀 하이픈·점 모두 매칭 버전
import os, re, sys, time, requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote_plus

WEBHOOK = os.getenv("DISCORD_WEBHOOK_ME")

WORKER   = "https://yellow-unit-fd5c.hyunsoopark4.workers.dev/?url="
SRC_URL  = "http://me.ssu.ac.kr/notice/notice01.php"
LIST_URL = WORKER + quote_plus(SRC_URL)

ID_FILE  = "last_me_id.txt"
HEADERS  = {"User-Agent": "Mozilla/5.0"}

TIMEOUT  = (5, 60)
RETRY    = 3

DATE_RE  = re.compile(r"\d{4}[.\-]\d{2}[.\-]\d{2}")   # ← 점·하이픈 모두 OK

def parse_date(t: str) -> datetime:
    return datetime.strptime(t.strip().replace(".", "-"), "%Y-%m-%d")

def fetch_html():
    for i in range(1, RETRY + 1):
        try:
            r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200 and "<html" in r.text.lower():
                print(f"✅ Worker 성공 (try {i})")
                return r.text
            print(f"⚠️ Worker status {r.status_code} (try {i})")
        except requests.RequestException as e:
            print(f"⚠️ Worker 오류 (try {i}) – {e}")
        time.sleep(1)
    return None

def get_latest():
    html = fetch_html()
    if not html:
        return None, None, None

    soup, latest_dt, latest_a = BeautifulSoup(html, "html.parser"), datetime.min, None
    for tr in soup.select("tr"):
        date_td = tr.find("td", string=DATE_RE)
        link_a  = tr.find("a", href=lambda h: h and "wr_id=" in h)
        if not (date_td and link_a):
            continue
        try:
            cur_dt = parse_date(date_td.get_text())
        except ValueError:
            continue
        if cur_dt >= latest_dt:
            latest_dt, latest_a = cur_dt, link_a

    if not latest_a:
        return None, None, None

    link = latest_a["href"]
    if link.startswith("/"):
        link = "https://me.ssu.ac.kr" + link
    wid  = re.search(r"wr_id=(\d+)", link).group(1)
    return wid, latest_a.get_text(strip=True), link

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
        print("🚫 Worker 실패 또는 파싱 실패 – 다음 주기 스킵")
        return

    if wid == read_last():
        print("⏸  새 글 없음")
        return

    send(f"🔧 **기계공학부 새 공지**\n{title}\n{link}")
    write_last(wid)
    print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
