# me_bot.py  ── 한국 프록시 다중 시도 버전
import os, re, sys, time, random, requests
from bs4 import BeautifulSoup
from datetime import datetime

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_ME")
LIST_URL = "https://me.ssu.ac.kr/notice/notice01.php"
ID_FILE  = "last_me_id.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:124.0) Gecko/20100101 Firefox/124.0"
}
TIMEOUT = 15        # 프록시 품질 고려해 15초
TRIES   = 2         # 프록시별 재시도 2회

# ⚠️ 무료 공개 한국 프록시 샘플(2025-07 갱신) 8개
PROXIES = [
    "http://146.56.43.43:3128",
    "http://146.56.43.1:80",
    "http://61.100.180.198:8080",
    "http://121.138.83.94:3128",
    "http://58.180.224.188:80",
    "http://210.179.83.199:3128",
    "http://58.230.28.92:80",
    "http://152.70.252.193:3128",
]

def parse_date(txt: str) -> datetime:
    return datetime.strptime(txt.strip().replace(".", "-"), "%Y-%m-%d")

def fetch_html():
    random.shuffle(PROXIES)  # 매 실행마다 순서 섞기
    for px in PROXIES:
        for attempt in range(1, TRIES + 1):
            try:
                r = requests.get(
                    LIST_URL,
                    headers=HEADERS,
                    timeout=TIMEOUT,
                    proxies={"http": px, "https": px},
                )
                if r.status_code == 200 and "<html" in r.text.lower():
                    print(f"✅  프록시 {px} 성공")
                    return r.text
            except requests.exceptions.RequestException as e:
                print(f"⚠️  {px} 실패({attempt}/{TRIES}) – {e}")
        print(f"🛑  {px} 포기, 다음 프록시로…")
    return None

def get_latest():
    html = fetch_html()
    if not html:
        return None, None, None

    soup = BeautifulSoup(html, "html.parser")
    latest_link, latest_dt = None, datetime.min

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
            latest_dt, latest_link = cur_dt, link_a

    if latest_link:
        link = latest_link["href"]
        if link.startswith("/"):
            link = "https://me.ssu.ac.kr" + link
        title = latest_link.get_text(strip=True)
        wid = re.search(r"wr_id=(\d+)", link).group(1)
        return wid, title, link
    return None, None, None

def read_last():
    try:
        return open(ID_FILE).read().strip()
    except FileNotFoundError:
        return None

def write_last(wid):
    with open(ID_FILE, "w") as f:
        f.write(wid)

def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_ME 시크릿이 없습니다")

    wid, title, link = get_latest()
    if not wid:
        print("🚫 모든 프록시 실패 – 이번 주기 스킵")
        return

    if wid == read_last():
        print("⏸  새 글 없음")
        return

    send(f"🔧 **기계공학부 새 공지**\n{title}\n{link}")
    write_last(wid)
    print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
