# materials_bot.py – 신소재공학과 공지 (tr 테이블 파싱 안전판)
import os, re, sys, hashlib, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK = os.getenv("DISCORD_WEBHOOK_MSE")   # Secrets에 저장
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"
HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 20

md5 = lambda s: hashlib.md5(s.encode()).hexdigest()

DEBUG_SAVE_HTML = True 

def get_latest():
    html = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT).text

     # ── 디버그용: 파싱 실패할 때 HTML 저장 ──
    if DEBUG_SAVE_HTML:
        with open("mse_debug.html", "w", encoding="utf-8") as f:
            f.write(html[:20000])   # 2만 byte면 목록 전체 충분
        print("🔍 mse_debug.html 로 HTML 저장 완료")

    soup = BeautifulSoup(html, "html.parser")

    for tr in soup.select("tbody tr"):
        # 1) 고정 공지(tr 안에 alt=공지 아이콘 또는 '공지' 텍스트) 건너뛰기
        if tr.find("img", alt=lambda v: v and "공지" in v) or "공지" in tr.get_text():
            continue

        a = tr.find("a", href=True)
        if not a:
            continue
        link = urljoin("https://materials.ssu.ac.kr", a["href"])
        title = a.get_text(strip=True)

        # 2) 링크에서 num= 또는 idx= 값 추출, 없으면 해시
        m = re.search(r"(num|idx)=(\d+)", link)
        nid = m.group(2) if m else md5(link)
        return nid, title, link

    return None, None, None

def read_last():
    try:
        return open(ID_FILE).read().strip()
    except FileNotFoundError:
        return None

def write_last(nid):
    with open(ID_FILE, "w") as f:
        f.write(nid)

def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_MSE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 파싱 실패 – 이번 주기 스킵")
        return
    if nid == read_last():
        print("⏸ 새 글 없음")
        return

    send(f"🔬 **신소재공학과 새 공지**\n{title}\n{link}")
    write_last(nid)
    print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
