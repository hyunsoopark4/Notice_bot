# materials_bot.py  –  다중 인코딩 자동 판별판
import os, re, sys, hashlib, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_MSE")
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"
HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 15
md5 = lambda s: hashlib.md5(s.encode()).hexdigest()

def smart_decode(b: bytes) -> str:
    """UTF-8 → CP949 순으로 시도해 첫 성공 인코딩 사용"""
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    # 모두 실패 시 손실 복구
    return b.decode("utf-8", "replace")

def fetch_html() -> str | None:
    try:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
        return smart_decode(r.content)
    except Exception:
        traceback.print_exc()
        return None

def get_latest():
    html = fetch_html()
    if not html:
        return None, None, None

    soup = BeautifulSoup(html, "html.parser")

    # 글 목록 <tbody><tr> or <ul><li>
    for a in soup.find_all("a", href=True):
        href, text = a["href"], a.get_text(strip=True)

        # 고정 공지(공지 텍스트·아이콘) 건너뛰기
        if "공지" in text or a.find("img", alt=lambda v: v and "공지" in v):
            continue
        if not re.search(r"(view|num|idx)=", href):
            continue

        link = urljoin("https://materials.ssu.ac.kr", href)
        m = re.search(r"(num|idx)=(\d+)", link)
        nid = m.group(2) if m else md5(link)
        return nid, text, link

    return None, None, None

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(nid): open(ID_FILE, "w").write(nid)

def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

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
