# infocom_bot.py
# 전자정보공학부(학부) 공지 봇 – 부트스트랩 포함 경량판
# 역할
#   1) last_infocom_id.txt 가 없거나 0, 잘못된 값이면 자동 부트스트랩:
#      상세페이지를 직접 조회하여 최신 idx를 지수탐색+이분탐색으로 찾고 저장
#   2) 이후에는 마지막 idx 이후의 새 글만 빠르게 전송
# 특징
#   목록 페이지를 보지 않으므로 목록 타임아웃에 영향 받지 않음
#   전체 실행 시간 예산을 두어 액션이 오래 붙잡히지 않음
# 환경
#   DISCORD_WEBHOOK_INFOCOM    필수
#   INFOCOM_PROXY_URL          선택. 예: https://xxx.workers.dev/?url=
# 상태파일
#   last_infocom_id.txt

import os, sys, time, re, json, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import quote

# 디스코드 웹훅 로드
WEBHOOK = os.getenv("DISCORD_WEBHOOK_INFOCOM")
if not WEBHOOK:
    try:
        with open("config.json", encoding="utf-8") as f:
            WEBHOOK = json.load(f)["DISCORD_WEBHOOK_INFOCOM"]
    except Exception:
        sys.exit("DISCORD_WEBHOOK_INFOCOM 시크릿 또는 config.json 누락")

# 선택 프록시 워커. 예: https://<subdomain>.workers.dev/?url=
WORKER = os.getenv("INFOCOM_PROXY_URL", "").rstrip("/")

# 상세페이지 URL 템플릿
VIEW_HTTPS = "https://infocom.ssu.ac.kr/kor/notice/undergraduate.php?idx={idx}&m=v"

# 요청 설정
TIMEOUT = (5, 8)        # 연결 5초, 본문 8초
RETRY   = 1             # 경로별 재시도 횟수
SLEEP   = 0.6           # 재시도 간격
BUDGET_SEC = 70         # 전체 실행 상한

# 한 번 실행에서 확인할 최대 신규 글 수
SCAN_MAX = 8

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": "https://infocom.ssu.ac.kr/",
    "Connection": "keep-alive",
}

ID_FILE = "last_infocom_id.txt"

# 마지막 idx 읽기
def read_last() -> int | None:
    try:
        return int(open(ID_FILE, encoding="utf-8").read().strip())
    except Exception:
        return None

# 마지막 idx 기록
def write_last(idx: int):
    with open(ID_FILE, "w", encoding="utf-8") as f:
        f.write(str(idx))

# 워커 경유 GET
def fetch_via_worker(url: str) -> requests.Response:
    if not WORKER:
        raise RuntimeError("no worker")
    proxied = f"{WORKER}?url={quote(url, safe='')}"
    return requests.get(proxied, headers=HEADERS, timeout=TIMEOUT)

# 단일 URL 가져오기. 성공 시 HTML 문자열 반환, 실패 시 None
def get_html(url_https: str) -> str | None:
    routes = []
    if WORKER:
        routes.append(("worker", url_https))
    routes.append(("https", url_https))
    routes.append(("http", url_https.replace("https://", "http://", 1)))

    for label, url in routes:
        for _ in range(RETRY):
            try:
                r = fetch_via_worker(url) if label == "worker" else requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if r.status_code == 200 and r.text.strip():
                    return r.text
            except Exception:
                pass
            time.sleep(SLEEP)
    return None

# HTML에서 제목 추출
def parse_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for sel in (".board_view .title", ".view .title", "h1", "h2", "h3"):
        el = soup.select_one(sel)
        if el:
            t = el.get_text(" ", strip=True)
            if t:
                return t
    ttag = soup.find("title")
    if ttag:
        t = re.sub(r"\s*\\|\\s*.*$", "", ttag.get_text(" ", strip=True))
        if t:
            return t
    txt = soup.get_text("\n", strip=True)
    for ln in txt.splitlines():
        if ln.strip():
            return ln.strip()[:120]
    return None

# 상세페이지 존재여부와 제목
def post_exists_and_title(idx: int) -> tuple[bool, str | None]:
    html = get_html(VIEW_HTTPS.format(idx=idx))
    if not html:
        return False, None
    # 비존재 안내 문구 필터
    if "없는 게시물" in html or "잘못된 접근" in html:
        return False, None
    title = parse_title(html)
    return (title is not None), title

# 부트스트랩: 최신 idx 자동 탐색
def bootstrap_find_latest(start_time: float) -> int | None:
    # 1단계 지수 탐색: 존재하는 최대 영역 상한을 찾기 위해 hi를 2048부터 2배씩 증가
    low_exist = 0
    hi = 2048
    while time.monotonic() - start_time < BUDGET_SEC * 0.6 and hi <= 131072:
        ok, _ = post_exists_and_title(hi)
        if ok:
            low_exist = hi
            hi *= 2
        else:
            break

    if low_exist == 0:
        # 혹시 아주 낮은 구간에만 글이 있는 특수 케이스 대비: 1, 2, 4, 8..256 빠른 스캔
        probe = 1
        while probe <= 256 and time.monotonic() - start_time < BUDGET_SEC * 0.6:
            ok, _ = post_exists_and_title(probe)
            if ok:
                low_exist = probe
                hi = max(512, probe * 2)
                break
            probe *= 2

    if low_exist == 0:
        print("부트스트랩 실패: 존재하는 게시글 구간을 찾지 못했습니다")
        return None

    # 2단계 이분 탐색: [low_exist, hi) 범위에서 존재하는 최대 idx 찾기
    # hi는 현재 '존재하지 않음'이거나 충분히 큰 값
    if hi <= low_exist:
        hi = low_exist + 1
    # hi가 아직 존재한다면 hi를 늘려 비존재 상한을 만든다
    while time.monotonic() - start_time < BUDGET_SEC * 0.8:
        ok, _ = post_exists_and_title(hi)
        if not ok:
            break
        low_exist = hi
        hi *= 2
        if hi > 131072:
            break

    lo, hi = low_exist, max(low_exist + 1, hi)
    while lo + 1 < hi and time.monotonic() - start_time < BUDGET_SEC * 0.95:
        mid = (lo + hi) // 2
        ok, _ = post_exists_and_title(mid)
        if ok:
            lo = mid
        else:
            hi = mid

    # lo가 최신 존재 idx
    print(f"부트스트랩 완료: 최신 idx 추정 {lo}")
    return lo

# 디스코드 전송
def send(msg: str):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    start = time.monotonic()
    last_id = read_last()

    # 부트스트랩 조건: last 파일이 없거나 0 이하
    if not last_id or last_id <= 0:
        latest = bootstrap_find_latest(start)
        if latest is None:
            print("초기화 실패. 다음 주기에 재시도")
            return
        write_last(latest)
        print("최신 idx로 초기화 완료. 이번 주기에는 알림을 보내지 않습니다")
        return

    # 신규 글 스캔
    found = []
    idx = last_id + 1
    # 연속 비존재가 몇 번 나오면 중단
    gaps = 0
    while len(found) < SCAN_MAX and time.monotonic() - start < BUDGET_SEC:
        ok, title = post_exists_and_title(idx)
        if not ok:
            gaps += 1
            if gaps >= 3:
                break
            idx += 1
            continue
        found.append((idx, title or "제목 없음", VIEW_HTTPS.format(idx=idx)))
        gaps = 0
        idx += 1

    if not found:
        print("새 공지 없음")
        return

    # 오래된 것부터 전송
    for i, title, link in found:
        send(f"전자정보공학부 새 공지\n{title}\n{link}")
        write_last(i)
        print(f"전송 완료: {i} {title}")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("예상치 못한 오류. 다음 주기에서 재시도")
