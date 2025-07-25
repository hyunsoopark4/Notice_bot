# materials_bot.py — board_list 테이블 첫 글만 추출 (최소·안정 버전)
import os, re, sys, hashlib, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_MSE")              # ▸ Secrets
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"
HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 20
md5 = lambda s: hashlib.md5(s.encode()).hexdigest()

def smart_decode(b: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try: return b.decode(enc)
        except UnicodeDecodeError: pass
    return b.decode("utf-8", "replace")

DEBUG = True

def fetch_html() -> str | None:
    try:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
        html = smart_decode(r.content)

        if DEBUG:                      # ★ 첫 1000자 콘솔에 출력
            print("\n=== HTML HEAD ===")
            print(html[:1000])
            print("=== HTML HEAD END ===\n")

        return html
    except Exception:
        traceback.print_exc()
        return None

def get_latest():
    html = fetch_html()
    if not html: return None, None, None
    soup = BeautifulSoup(html, "html.parser")

    table = soup.find("table", class_=lambda c: c and "board_list" in c)
    if not table:
        return None, None, None

    for tr in table.select("tbody tr"):
        # 고정 공지: tr 에 alt='공지' 또는 'ico_notice' 이미지가 있으면 continue
        if tr.find("img", alt=lambda v: v and ("공지" in v or "notice" in v.lower())):
            continue
        a = tr.find("a", href=True)
        if not a:
            continue

        title = a.get_text(" ", strip=True)
        link  = urljoin("https://materials.ssu.ac.kr", a["href"])
        m = re.search(r"(num|idx)=(\d+)", link)
        nid = m.group(2) if m else md5(link)
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
        sys.exit("❌ DISCORD_WEBHOOK_MSE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 글을 찾지 못했습니다 – 게시판 HTML 구조가 또 바뀐 듯합니다"); return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"🔬 **신소재공학과 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
