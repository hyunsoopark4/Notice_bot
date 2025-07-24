# materials_bot.py
# 신소재공학과 공지 가장 최신 글 1건 → 디스코드 알림 + 디버그 html 저장

import os, re, sys, hashlib, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_MSE")          # 레포 Secrets
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"
HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 15

def md5(s): return hashlib.md5(s.encode()).hexdigest()

def get_latest():
    html = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT).text
    # ── html 덤프 저장 (Artifacts로 업로드할 파일) ──
    with open("mse_debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    soup = BeautifulSoup(html, "html.parser")

    for tr in soup.select("tbody tr"):
        # 고정 공지 건너뛰기
        if "공지" in tr.get_text(): continue
        a = tr.find("a", href=True)
        if not a: continue
        link  = urljoin("https://materials.ssu.ac.kr", a["href"])
        title = a.get_text(strip=True)
        m = re.search(r"(num|idx)=(\d+)", link)
        nid = m.group(2) if m else md5(link)
        return nid, title, link
    return None, None, None

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(nid): open(ID_FILE, "w").write(nid)

def send(msg): requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("DISCORD_WEBHOOK_MSE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("파싱 실패 — 스킵"); return
    if nid == read_last():
        print("새 글 없음"); return

    send(f"🔬 신소재공학과 새 공지\n{title}\n{link}")
    write_last(nid)
    print("알림 전송 완료")

if __name__ == "__main__":
    main()
