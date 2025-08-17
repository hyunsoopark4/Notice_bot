# infocom_bot.py
# 전자정보공학부 학부 공지를 idx로 직접 조회해서
# 마지막으로 보낸 글 이후 것만 빠르게 전송하는 경량판
# 특징
#   실행 예산을 두어 1분 내 종료
#   요청 타임아웃과 재시도를 최소화
#   목록 페이지는 아예 보지 않음
# 사전 준비
#   last_infocom_id.txt 에 최신 idx 번호를 한 줄로 저장

import os, sys, time, re, json, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import quote

# 디스코드 웹훅
WEBHOOK = os.getenv("DISCORD_WEBHOOK_INFOCOM")
if not WEBHOOK:
    try:
        with open("config.json", encoding="utf-8") as f:
            WEBHOOK = json.load(f)["DISCORD_WEBHOOK_INFOCOM"]
    except Exception:
        sys.exit("DISCORD_WEBHOOK_INFOCOM 시크릿 또는 config.json 누락")

# 선택 프록시 워커. 예: https://xxx.workers.dev/?url=
WORKER = os.getenv("INFOCOM_PROXY_URL", "").rstrip("/")

# 상세 페이지 템플릿
VIEW_HTTPS = "https://infocom.ssu.ac.kr/kor/notice/undergraduate.php?idx={idx}&m=v"

# 요청 설정을 공격적으로 짧게
TIMEOUT = (5, 8)      # 연결 5초, 본문 8초
RETRY   = 1           # 경로당 재시도 1회
SLEEP   = 0.8         # 재시도 간격
SCAN_MAX = 8          # 한 번에 확인할 최대 신규 글 수
BUDGET_SEC = 60       # 전체 실행 상한 60초

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": "https://infocom.ssu.ac.kr/",
    "Connection": "keep-alive",
}

ID_FILE = "last_infocom_id.txt"

def read_last() -> int | None:
    try:
        return int(open(ID_FILE, encoding="utf-8").read().strip())
    except Exception:
        return None

def write_last(idx: int):
    with open(ID_FILE, "w", encoding="utf-8") as f:
        f.write(str(idx))

def fetch_via_worker(url: str) -> requests.Response:
    if not WORKER:
        raise RuntimeError("no worker")
    proxied = f"{WORKER}?url={quote(url, safe='')}"
    return requests.get(proxied, headers=HEADERS, timeout=TIMEOUT)

def robust_get(url_https: str) -> str | None:
    # 경로 순서: worker 있으면 worker, 안 되면 https 직접, 마지막으로 http 직접
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

def parse_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    # 흔한 후보를 빠르게 시도
    for sel in (".board_view .title", ".view .title", "h1", "h2", "h3"):
        el = soup.select_one(sel)
        if el:
            t = el.get_text(" ", strip=True)
            if t:
                return t
    ttag = soup.find("title")
    if ttag:
        t = re.sub(r"\s*\|\s*.*$", "", ttag.get_text(" ", strip=True))
        if t:
            return t
    # 텍스트 첫 줄
    txt = soup.get_text("\n", strip=True)
    for ln in txt.splitlines():
        if ln.strip():
            return ln.strip()[:120]
    return None

def post_exists_and_title(idx: int) -> tuple[bool, str | None]:
    url = VIEW_HTTPS.format(idx=idx)
    html = robust_get(url)
    if not html:
        return False, None
    # 존재하지 않을 때 안내 문구가 있을 수 있음
    if "없는 게시물" in html or "잘못된 접근" in html:
        return False, None
    title = parse_title(html)
    return (title is not None), title

def send(msg: str):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    start = time.monotonic()

    last_id = read_last()
    if last_id is None:
        print("초기 last_infocom_id.txt가 없습니다. 이번 주기 스킵")
        return

    found = []
    idx = last_id + 1
    while len(found) < SCAN_MAX and (time.monotonic() - start) < BUDGET_SEC:
        ok, title = post_exists_and_title(idx)
        if not ok:
            # 연속 두세 개가 비어 있을 수 있으므로 조금만 더 확인 후 종료
            # 예산을 아끼기 위해 3칸까지만 탐색
            if idx >= last_id + 3:
                break
            idx += 1
            continue
        found.append((idx, title, VIEW_HTTPS.format(idx=idx)))
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
