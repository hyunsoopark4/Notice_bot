# materials_bot.py
# ──────────────────────────────────────────────────────────────
# 신소재공학과 공지(https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51)
# 가장 최신 글 1건을 읽어, 새 글이면 디스코드 웹훅으로 알림.

import os, re, sys, requests, hashlib
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK = os.getenv("DISCORD_WEBHOOK_MSE")      # ← 레포 Secrets에 추가
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"

HEADERS = {"User-Agent": "Mozilla/5.0"}
DATE_RE = re.compile(r"\d{4}[.\-]\d{2}[.\-]\d{2}")

def md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

def parse_date(t: str) -> datetime:
    return datetime.strptime(t.strip().replace(".", "-"), "%Y-%m-%d")

def get_latest():
    html = requests.get(LIST_URL, headers=HEADERS, timeout=15).text
    soup = BeautifulSoup(html, "html.parser")

    latest_a, latest_dt = None, datetime.min

    # 표 구조: <tbody><tr>…</tr></tbody>
    for tr in soup.select("tbody tr"):
        # ① 고정 공지(아이콘/글씨 '공지')는 패스
        if tr.find("td", string=re.compile("공지|Notice", re.I)):
            continue

        # ② 글 링크 & 날짜 찾기
        a = tr.find("a", href=True)
        d = tr.find("td", string=DATE_RE)
        if not a:
            continue

        # 날짜 셀이 없으면 dt를 최소값으로 유지 → 결국 링크 첫 줄 선택
        cur_dt = latest_dt
        if d:
            try:
                cur_dt = parse_date(d.text)
            except ValueError:
                pass

        if cur_dt >= latest_dt:
            latest_a, latest_dt = a, cur_dt

    if not latest_a:
        return None, None, None

    link = urljoin("https://materials.ssu.ac.kr", latest_a["href"])
    title = latest_a.get_text(strip=True)

    # wr_id · idx 등이 없으면 링크 전체 md5 로 중복판단
    m = re.search(r"(wr_id|idx)=(\d+)", link)
    nid = m.group(2) if m else md5(link)

    return nid, title, link

def read_last():
    try: return open(ID_FILE).read().strip()
    except FileNotFoundError: return None

def write_last(nid): open(ID_FILE, "w").write(nid)

def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_MSE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 공지 파싱 실패 – 이번 주기 스킵"); return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"🔬 **신소재공학과 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
