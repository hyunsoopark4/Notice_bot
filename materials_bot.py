# materials_bot.py – 번호·날짜 제거, 순수 제목만 전송
import os, re, sys, hashlib, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_MSE")
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"
HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 15
md5 = lambda s: hashlib.md5(s.encode()).hexdigest()

def smart_decode(b):
    for enc in ("utf-8", "cp949", "euc-kr"):
        try: return b.decode(enc)
        except UnicodeDecodeError: continue
    return b.decode("utf-8", "replace")

def fetch_html():
    r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
    return smart_decode(r.content)

def get_latest():
    html = fetch_html()
    if not html:
        return None, None, None
    soup = BeautifulSoup(fetch_html(), "html.parser")

    # ── 디버그용: 실패 시 첫 500 글자 출력 ──
    print("DEBUG snippet ↓↓↓")
    print(html[:500])
    print("DEBUG snippet ↑↑↑")
    
    for tr in soup.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue

        # 고정 공지(첫번째 td 텍스트 '공지') 건너뛰기
        if "공지" in tds[0].get_text():
            continue

        title_cell = tds[1]                     # 제목 셀
        a = title_cell.find("a", href=True)
        if not a:
            continue

        title = a.get_text(" ", strip=True)     # 순수 제목
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
        print("🚫 파싱 실패 – 스킵"); return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"🔬 **신소재공학과 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
