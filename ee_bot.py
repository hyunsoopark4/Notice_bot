# ee_bot.py  ― 전기공학부(sub05_01) 최신 공지 알림
# 1. 고정 공지([공지], '공지') 제외
# 2. 링크에 ?idx= / ?num= 값이 있는 첫 글을 최신 글로 간주
# 3. DUP 방지용 ID 파일(last_ee_id.txt) 저장

import os, re, sys, hashlib, traceback, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_EE")                # ← Secrets
LIST_URL = "http://ee.ssu.ac.kr/sub/sub05_01.php"
ID_FILE  = "last_ee_id.txt"

HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 20
md5      = lambda s: hashlib.md5(s.encode()).hexdigest()
IDX_RE   = re.compile(r"[?&](idx|num)=(\d+)", re.I)

def smart_decode(b: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try: return b.decode(enc)
        except UnicodeDecodeError: pass
    return b.decode("utf-8", "replace")

def fetch_html():
    try:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
        return smart_decode(r.content)
    except Exception:
        traceback.print_exc(); return None

def is_notice(title: str) -> bool:
    return bool(re.match(r"\s*\[?공지\]?", title))

def get_latest():
    html = fetch_html()
    if not html: return None, None, None
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=IDX_RE):
        title = a.get_text(" ", strip=True)
        if is_notice(title):
            continue
        link = urljoin("http://ee.ssu.ac.kr", a["href"])
        m = IDX_RE.search(link)
        nid = m.group(2) if m else md5(link)
        return nid, title, link
    return None, None, None

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(n): open(ID_FILE, "w").write(n)

def send(msg): requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_EE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 공지 파싱 실패"); return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"⚡ **전기공학부 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
