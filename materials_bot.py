# materials_bot.py  –  링크 기반 가장 탄탄한 버전
import os, re, sys, hashlib, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_MSE")            # <- Secrets
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"
HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 15
md5      = lambda s: hashlib.md5(s.encode()).hexdigest()

def smart_decode(b: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try: return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace")

def fetch_html() -> str | None:
    try:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
        return smart_decode(r.content)
    except Exception:
        traceback.print_exc(); return None

def is_notice(tag) -> bool:
    """링크 자신 또는 주변에 '공지' 글자가 들어 있으면 고정 공지로 간주"""
    if "공지" in tag.get_text():                       # 자체 텍스트
        return True
    # 앞뒤 형제/부모 td, div 등에 '공지' 포함 여부
    for sib in list(tag.parents)[:2] + list(tag.previous_siblings)[:2]:
        if hasattr(sib, "get_text") and "공지" in sib.get_text():
            return True
    return False

def get_latest():
    html = fetch_html()
    if not html:
        return None, None, None

    soup = BeautifulSoup(html, "html.parser")

    # 링크 후보: href 안에 'tbl=bbs51'과 'num='(또는 idx=) 가 동시에 존재
    link_candidates = soup.find_all(
        "a",
        href=lambda h: h and "tbl=bbs51" in h and re.search(r"(num|idx)=", h),
    )

    for a in link_candidates:
        if is_notice(a):
            continue  # 고정 공지 skip

        link  = urljoin("https://materials.ssu.ac.kr", a["href"])
        title = a.get_text(" ", strip=True)

        m = re.search(r"(num|idx)=(\d+)", link)
        nid = m.group(2) if m else md5(link)           # 글 고유 ID

        return nid, title, link

    return None, None, None

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(n): open(ID_FILE, "w").write(n)

def send(msg): requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_MSE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 글 링크를 찾지 못했습니다 – 구조가 크게 바뀌었는지 확인 필요")
        return
    if nid == read_last():
        print("⏸ 새 글 없음")
        return

    send(f"🔬 **신소재공학과 새 공지**\n{title}\n{link}")
    write_last(nid)
    print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
