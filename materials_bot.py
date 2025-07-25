# materials_bot.py — 번호·날짜 완전 제거 확정판
import os, re, sys, hashlib, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_MSE")
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"
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

def clean_title(raw: str) -> str:
    """앞쪽 ‘번호’·날짜, 뒷쪽 날짜 패턴 제거"""
    # 앞번호  or  앞날짜(2025.06) 제거
    title = re.sub(r"^(?:\d+\s*|20\d{2}[.\-]\d{2}\s*)+", "", raw).strip()
    # 뒤날짜 2025-06-25 제거
    title = re.sub(r"\s*20\d{2}[.\-]\d{2}[.\-]\d{2}$", "", title).strip()
    return title

def get_latest():
    html = fetch_html()
    if not html: return None, None, None
    soup = BeautifulSoup(html, "html.parser")

    for tr in soup.select("tbody tr"):
        # 고정 공지 skip
        first_td = tr.find("td")
        if first_td and "공지" in first_td.get_text(strip=True):
            continue

        subj_td = tr.find("td", class_=lambda c: c and "subject" in c)
        if not subj_td: continue
        a = subj_td.find("a", href=True)
        if not a: continue

        raw_title = a.get_text(" ", strip=True)
        title = clean_title(raw_title)           # ← 불순물 제거
        link  = urljoin("https://materials.ssu.ac.kr", a["href"])

        m = re.search(r"(idx|num)=(\d+)", link)
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
        sys.exit("❌ DISCORD_WEBHOOK_MSE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 공지 파싱 실패"); return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"🔬 **신소재공학과 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
