# materials_bot.py  –  CP949 인코딩 처리 + 테이블 파싱 확정판
import os, re, sys, hashlib, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

WEBHOOK  = os.getenv("DISCORD_WEBHOOK_MSE")          # Secrets
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"
HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 15
DATE_RE  = re.compile(r"\d{4}[.\-]\d{2}[.\-]\d{2}")
md5 = lambda s: hashlib.md5(s.encode()).hexdigest()

def get_latest():
    r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
    r.encoding = "cp949"            # ← 핵심: EUC-KR/CP949 로 강제 지정
    html = r.text

    soup = BeautifulSoup(html, "html.parser")

    # 테이블: 번호 | 제목 | 작성자 | 날짜
    for tr in soup.select("tbody tr"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue

        # 고정 공지 체크: 첫 번째 td에 '공지'라는 텍스트가 있음
        if "공지" in tds[0].get_text():
            continue

        a = tds[1].find("a", href=True)
        if not a:
            continue

        link  = urljoin("https://materials.ssu.ac.kr", a["href"])
        title = a.get_text(strip=True)

        # 날짜 추출 (마지막 td)
        date_td = tds[-1].get_text(strip=True)
        if not DATE_RE.fullmatch(date_td):
            continue

        # 공지 ID: href 안 num 또는 idx 값, 없으면 링크 md5
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
        sys.exit("❌ DISCORD_WEBHOOK_MSE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 파싱 실패 – 이번 주기 스킵"); return
    if nid == read_last():
        print("⏸ 새 글 없음"); return

    send(f"🔬 **신소재공학과 새 공지**\n{title}\n{link}")
    write_last(nid); print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
