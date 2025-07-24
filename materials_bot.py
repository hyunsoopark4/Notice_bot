# materials_bot.py  ── 신소재공학과 공지 (공지 고정글 건너뛰기)
import os, re, sys, requests, hashlib
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus

WEBHOOK = os.getenv("DISCORD_WEBHOOK_MSE")
ID_FILE = "last_mse_id.txt"

WORKER  = "https://yellow-unit-fd5c.hyunsoopark4.workers.dev/?url="
SRC_URL = "http://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
LIST_URL = WORKER + quote_plus(SRC_URL)      # 한국 워커 프록시 사용

HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 30
NUM_RE  = re.compile(r"[?&]num=(\d+)")
MD5     = lambda s: hashlib.md5(s.encode()).hexdigest()

def get_latest():
    html = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT).text
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=lambda h: h and "num=" in h and "tbl=bbs51" in h):
        if "공지" in a.get_text(strip=True):       # 고정 공지 패스
            continue
        link = urljoin("https://materials.ssu.ac.kr", a["href"])
        m = NUM_RE.search(link)
        nid = m.group(1) if m else MD5(link)       # num= 있으면 그 값, 없으면 해시
        title = a.get_text(strip=True)[:150]       # 긴 경우 잘라서
        return nid, title, link
    return None, None, None

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(nid): open(ID_FILE, "w").write(nid)

def send(msg): requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_MSE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 파싱 실패 – 스킵"); return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"🔬 **신소재공학과 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
