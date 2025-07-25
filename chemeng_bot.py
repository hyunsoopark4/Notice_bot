# chemeng_bot.py — 화학공학과(sub03_01) 공지 알림 (링크 패턴 기반)
import os, re, sys, hashlib, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_CHEMENG")          # ← Secrets
LIST_URL = "http://chemeng.ssu.ac.kr/sub/sub03_01.php"
ID_FILE  = "last_chemeng_id.txt"

HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 20
md5      = lambda s: hashlib.md5(s.encode()).hexdigest()

def smart_decode(b: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace")

def fetch_html():
    try:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
        return smart_decode(r.content)
    except Exception:
        traceback.print_exc(); return None

def is_notice(text: str) -> bool:
    """고정 공지 여부: [공지] · '공지' 단어가 제목 앞쪽에 있으면 True"""
    return bool(re.match(r"\s*\[?공지\]?", text))

def get_latest():
    html = fetch_html()
    if not html:
        return None, None, None

    soup = BeautifulSoup(html, "html.parser")

    # a href 에 ?idx= 또는 ?num= 가 포함된 링크를 위에서부터 탐색
    pattern = re.compile(r"[?&](idx|num)=\d+", re.I)

    for a in soup.find_all("a", href=pattern):
        title = a.get_text(" ", strip=True)
        if is_notice(title):
            continue                             # 고정 공지 skip

        link = urljoin("http://chemeng.ssu.ac.kr", a["href"])
        m = re.search(pattern, link)
        nid = m.group(0).split("=")[-1] if m else md5(link)
        return nid, title, link

    return None, None, None

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(n): open(ID_FILE, "w").write(n)

def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_CHEMENG 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 공지 파싱 실패 — 사이트 구조가 예상과 다른 듯합니다"); return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"⚗️ **화학공학과 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
