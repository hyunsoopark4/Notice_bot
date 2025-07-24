# me_bot.py  ── idx 기반으로 최신 공지 파싱
import os, re, sys, time, hashlib, requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote_plus, urljoin

WEBHOOK = os.getenv("DISCORD_WEBHOOK_ME")

WORKER  = "https://yellow-unit-fd5c.hyunsoopark4.workers.dev/?url="
SRC     = "http://me.ssu.ac.kr/notice/notice01.php"
LIST_URL = WORKER + quote_plus(SRC)

ID_FILE = "last_me_id.txt"
HEADERS = {"User-Agent": "Mozilla/5.0"}

TIMEOUT = (5, 60)
RETRY   = 3
DATE_RE = re.compile(r"\d{4}[.\-]\d{2}[.\-]\d{2}")

def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

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

    # ① 날짜 기반 우선
    latest_dt, latest_a = datetime.min, None
    for tr in soup.select("tr"):
        d = tr.find("td", string=DATE_RE)
        a = tr.find("a", href=True)
        if not (d and a): continue
        try:
            cur = datetime.strptime(d.text.replace(".", "-").strip(), "%Y-%m-%d")
        except ValueError:
            continue
        if cur >= latest_dt: latest_dt, latest_a = cur, a

    # ② 그래도 못 잡으면 목록 첫 a href 사용
    if not latest_a:
        latest_a = soup.find("a", href=True)
        if not latest_a: return None, None, None

    link = urljoin("https://me.ssu.ac.kr", latest_a["href"])
    title = latest_a.get_text(strip=True)
    uid = re.search(r"(idx|wr_id)=(\d+)", link)
    notice_id = uid.group(2) if uid else md5(link)   # idx 있으면 그 값, 없으면 링크 md5
    return notice_id, title, link

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(wid): open(ID_FILE, "w").write(wid)

def send(msg): requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_ME 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 파싱 실패 – 다음 주기 스킵"); return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"🔧 **기계공학부 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
