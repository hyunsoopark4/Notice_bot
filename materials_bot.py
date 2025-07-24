# materials_bot.py  –  subject 셀만 대상으로 고정 공지 정확 필터
import os, re, sys, hashlib, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_MSE")               # ← Secrets
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"
HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 15
md5 = lambda s: hashlib.md5(s.encode()).hexdigest()

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

    # 제목 셀(td) 클래스가 subject / subj 로 되어 있음
    for td in soup.select("td.subject, td.subj"):
        # 고정 공지(tr 안에 '공지' 텍스트가 별도 셀로 존재)
        parent_tr = td.find_parent("tr")
        if parent_tr and "공지" in parent_tr.get_text(strip=True).split()[0]:
            continue

        a = td.find("a", href=True)
        if not a: continue

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

def send(msg): requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_MSE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 파싱 실패 – 구조가 바뀌었는지 확인 필요"); return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"🔬 **신소재공학과 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
