# me_bot.py  (read-timeout 45초 + 2회 재시도)

import os, re, sys, time, requests
from bs4 import BeautifulSoup
from datetime import datetime

WEBHOOK = os.getenv("DISCORD_WEBHOOK_ME")
LIST_URL = (
    "https://yellow-unit-fd5c.hyunsoopark4.workers.dev/"
    "?url=https://me.ssu.ac.kr/notice/notice01.php"
)
ID_FILE = "last_me_id.txt"
HEADERS = {"User-Agent": "Mozilla/5.0"}

TIMEOUT = (5, 45)   # (connect 5 s, read 45 s)
RETRY   = 2         # Worker 실패 재시도 횟수

def parse_date(t): return datetime.strptime(t.strip().replace(".", "-"), "%Y-%m-%d")

def fetch_html():
    for i in range(1, RETRY + 2):
        try:
            r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.text
            print(f"⚠️  Worker status {r.status_code} (try {i})")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Worker 오류(try {i}) – {e}")
        time.sleep(2)
    return None

def get_latest():
    html = fetch_html()
    if not html: return None, None, None
    soup, latest_dt, latest_a = BeautifulSoup(html, "html.parser"), datetime.min, None
    for tr in soup.select("tr"):
        d = tr.find("td", string=re.compile(r"\d{4}.\d{2}.\d{2}"))
        a = tr.find("a", href=lambda h: h and "wr_id=" in h)
        if not (d and a): continue
        try: cur_dt = parse_date(d.get_text())
        except ValueError: continue
        if cur_dt >= latest_dt: latest_dt, latest_a = cur_dt, a
    if not latest_a: return None, None, None
    link = latest_a["href"]
    if link.startswith("/"): link = "https://me.ssu.ac.kr" + link
    wid  = re.search(r"wr_id=(\d+)", link).group(1)
    return wid, latest_a.get_text(strip=True), link

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(w): open(ID_FILE, "w").write(w)

def send(msg): requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK: sys.exit("❌ DISCORD_WEBHOOK_ME 시크릿이 없습니다")
    wid, title, link = get_latest()
    if not wid: print("🚫 Worker 실패 – 다음 주기 스킵"); return
    if wid == read_last(): print("⏸  새 글 없음"); return
    send(f"🔧 **기계공학부 새 공지**\n{title}\n{link}")
    write_last(wid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__": main()
