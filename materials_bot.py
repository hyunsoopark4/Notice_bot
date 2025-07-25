# materials_bot.py  ― 신소재공학과(bbs51) 최신 공지 알림
#  ● 고정 공지(공지 아이콘/텍스트) 건너뛰기
#  ● 제목 셀(td.subject · td.subj)만 파싱 → 번호·날짜 제외
#  ● UTF-8 / CP949 / EUC-KR 자동 인코딩 판별
#  ● 글 ID = idx(또는 num) 값 → 중복 전송 차단

import os, re, sys, hashlib, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ── 환경 변수 ───────────────────────────────────────────────────
WEBHOOK  = os.getenv("DISCORD_WEBHOOK_MSE")          # ← 레포 Secrets
LIST_URL = "https://materials.ssu.ac.kr/bbs/board.php?tbl=bbs51"
ID_FILE  = "last_mse_id.txt"

# ── 상수 ────────────────────────────────────────────────────────
HEADERS  = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 20
md5      = lambda s: hashlib.md5(s.encode()).hexdigest()

# ── 인코딩 자동 판별 ────────────────────────────────────────────
def smart_decode(b: bytes) -> str:
    for enc in ("utf-8", "cp949", "euc-kr"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", "replace")

def fetch_html() -> str | None:
    try:
        r = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
        return smart_decode(r.content)
    except Exception:
        traceback.print_exc()
        return None

# ── 최신 글 추출 ────────────────────────────────────────────────
def get_latest():
    html = fetch_html()
    if not html:
        return None, None, None

    soup = BeautifulSoup(html, "html.parser")

    # ① 제목 셀(td.subject / td.subj) 순서대로 탐색
    for td in soup.select("td.subject, td.subj"):
        tr = td.find_parent("tr")

        # 고정 공지: tr 안에 alt='공지'·'notice' 이미지 또는 '공지' 텍스트
        if tr and (tr.find("img", alt=lambda v: v and ("공지" in v or "notice" in v.lower()))
                   or "공지" in tr.get_text(strip=True).split()[0]):
            continue

        a = td.find("a", href=True)
        if not a:
            continue

        title = a.get_text(" ", strip=True)
        link  = urljoin("https://materials.ssu.ac.kr", a["href"])

        # 글 고유 ID: idx= 또는 num= 값, 없으면 링크 md5
        m = re.search(r"(idx|num)=(\d+)", link)
        nid = m.group(2) if m else md5(link)

        return nid, title, link

    # ② 예외: subject 셀이 없으면 (모바일·리스트형) href 패턴으로 Fallback
    for a in soup.find_all("a", href=True):
        if not re.search(r"(idx|num)=", a["href"]):
            continue
        if "공지" in a.get_text(strip=True):
            continue
        link  = urljoin("https://materials.ssu.ac.kr", a["href"])
        title = a.get_text(" ", strip=True)
        m = re.search(r"(idx|num)=(\d+)", link)
        nid = m.group(2) if m else md5(link)
        return nid, title, link

    return None, None, None

# ── 상태 파일 read/write ───────────────────────────────────────
def read_last():
    try:
        return open(ID_FILE).read().strip()
    except FileNotFoundError:
        return None

def write_last(nid): open(ID_FILE, "w").write(nid)

# ── 디스코드 전송 ───────────────────────────────────────────────
def send(msg):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

# ── 메인 ───────────────────────────────────────────────────────
def main():
    if not WEBHOOK:
        sys.exit("❌ DISCORD_WEBHOOK_MSE 시크릿이 없습니다")

    nid, title, link = get_latest()
    if not nid:
        print("🚫 공지 파싱 실패 — HTML 구조 확인 필요")
        return

    if nid == read_last():
        print("⏸ 새 글 없음")
        return

    send(f"🔬 **신소재공학과 새 공지**\n{title}\n{link}")
    write_last(nid)
    print("✅ 새 공지 전송 완료")

if __name__ == "__main__":
    main()
