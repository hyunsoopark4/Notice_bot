# me_bot.py  (타임아웃·재시도·헤더 보강)
import os, re, sys, time, requests
from bs4 import BeautifulSoup
from datetime import datetime

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_ME")
LIST_URL = "https://me.ssu.ac.kr/notice/notice01.php"
ID_FILE  = "last_me_id.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:124.0) Gecko/20100101 Firefox/124.0"
}
TIMEOUT = 20          # 초 ― 10초 → 20초
RETRY   = 3           # 최대 재시도 횟수

def parse_date(txt: str) -> datetime:
    txt = txt.strip().replace(".", "-")
    return datetime.strptime(txt, "%Y-%m-%d")

def safe_get(url):
    for i in range(RETRY):
        try:
            return requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        except requests.exceptions.RequestException as e:
            print(f"⚠️  연결 실패({i+1}/{RETRY})… {e}")
            time.sleep(2)
    return None

def get_latest():
    resp = safe_get(LIST_URL)
    if not resp or resp.status_code != 200:
        return None, None, None

    soup = BeautifulSoup(resp.text, "html.parser")
    latest_a, latest_dt = None, datetime.min

    for tr in soup.select("tr"):
        date_td = tr.find("td", string=re.compile(r"\d{4}.\d{2}.\d{2}"))
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
    title = latest_a.get_text(strip=True)
    wr_id = re.search(r"wr_id=(\d+)", link).group(1)
    return wr_id, title, link

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(wid):
    with open(ID_FILE, "w") as f: f.write(wid)

def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_ME 시크릿이 없습니다")

    wid, title, link = get_latest()
    if not wid:
        print("🚫 사이트 접속 실패 또는 글 파싱 실패 – 이번 실행 스킵")
        return

    if wid == read_last():
        print("⏸  새 글 없음")
        return

    send(f"🔧 **기계공학부 새 공지**\n{title}\n{link}")
    write_last(wid)
    print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
