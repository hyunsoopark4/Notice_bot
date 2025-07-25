# chemeng_bot.py  ─ 화학공학과(sub03_01.php) 최신 공지 알림
import os, re, sys, hashlib, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_CHEMENG")          # ← 레포 Secrets
LIST_URL = "http://chemeng.ssu.ac.kr/sub/sub03_01.php"
ID_FILE  = "last_chemeng_id.txt"

HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 20
md5      = lambda s: hashlib.md5(s.encode()).hexdigest()

def smart_decode(b: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try: return b.decode(enc)
        except UnicodeDecodeError: pass
    return b.decode("utf-8", "replace")

def fetch_html() -> str | None:
    try:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
        return smart_decode(r.content)
    except Exception:
        traceback.print_exc(); return None

def get_latest():
    html = fetch_html()
    if not html: return None, None, None
    soup = BeautifulSoup(html, "html.parser")

    # 제목 셀(class name에 'subject' 포함) 우선
    for td in soup.select("td[class*=subject], td[class*=subj]"):
        tr = td.find_parent("tr")

        # 고정 공지: tr 안에 '공지' 글자 또는 alt='공지' 아이콘 존재
        if tr and ("공지" in tr.get_text(strip=True) or
                   tr.find("img", alt=lambda v: v and "공지" in v)):
            continue

        a = td.find("a", href=True)
        if not a:
            continue

        title = a.get_text(" ", strip=True)
        link  = urljoin("http://chemeng.ssu.ac.kr", a["href"])

        m = re.search(r"(idx|num)=(\d+)", link)
        nid = m.group(2) if m else md5(link)        # 글 ID

        return nid, title, link

    return None, None, None

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(nid): open(ID_FILE, "w").write(nid)

def send(msg): requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_CHEMENG 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 공지 파싱 실패 – 구조 확인 필요"); return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"⚗️ **화학공학과 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
