# materials_bot.py  – 신소재공학과 게시판 최종판
import os, re, sys, hashlib, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK = os.getenv("DISCORD_WEBHOOK_MSE")          # ▸ 레포 Secrets
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"
HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 20
DATE_RE  = re.compile(r"\d{4}[.\-]\d{2}[.\-]\d{2}")
md5      = lambda s: hashlib.md5(s.encode()).hexdigest()

def save_debug(html: str):
    with open("mse_debug.html", "w", encoding="utf-8") as f:
        f.write(html)

def fetch_html() -> str | None:
    try:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
        r.encoding = "cp949"                      # ← 한글 깨짐 방지
        return r.text
    except Exception:
        traceback.print_exc()
        return None

def get_latest():
    html = fetch_html()
    if not html:
        return None, None, None
    save_debug(html)                              # 항상 저장해 두기

    soup = BeautifulSoup(html, "html.parser")

    # 게시글 링크 후보: <a href*="view" or "bbs51" ...>
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)

        # 고정 공지 건너뛰기 (텍스트·alt)
        if "공지" in text or a.find("img", alt=lambda v: v and "공지" in v):
            continue

        if not re.search(r"(view|bbs51|idx|num)=\d+", href, re.I):
            continue

        link = urljoin("https://materials.ssu.ac.kr", href)
        m = re.search(r"(idx|num)=(\d+)", link)
        nid = m.group(2) if m else md5(link)
        return nid, text, link

    return None, None, None

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(n): open(ID_FILE, "w").write(n)

def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_MSE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 파싱 실패 – mse_debug.html 확인")
        return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"🔬 **신소재공학과 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
