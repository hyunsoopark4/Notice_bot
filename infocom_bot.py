# infocom_bot.py
# 역할: 전자정보공학부 학부 공지의 상세페이지를 idx로 직접 조회하여
#       마지막으로 보낸 글 이후의 새 글을 모두 디스코드로 전송
# 특징: 목록 페이지가 타임아웃이어도 동작. Cloudflare Worker와 r.jina.ai 폴백 포함.

import os, re, sys, json, time, requests, traceback
from bs4 import BeautifulSoup
from urllib.parse import quote

# 환경변수 로드
WEBHOOK = os.getenv("DISCORD_WEBHOOK_INFOCOM")   # 디스코드 웹훅
WORKER  = os.getenv("INFOCOM_PROXY_URL", "").rstrip("/")  # 예: https://xxx.workers.dev/?url=

# 상수 정의
BASE_VIEW = "https://infocom.ssu.ac.kr/kor/notice/undergraduate.php?idx={idx}&m=v"
RJA_HTTP  = "https://r.jina.ai/http://infocom.ssu.ac.kr/kor/notice/undergraduate.php?idx={idx}&m=v"
RJA_HTTPS = "https://r.jina.ai/https://infocom.ssu.ac.kr/kor/notice/undergraduate.php?idx={idx}&m=v"

ID_FILE   = "last_infocom_id.txt"
HEADERS   = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": "https://infocom.ssu.ac.kr/",
    "Connection": "keep-alive",
}
TIMEOUT   = (10, 20)   # 연결 10초, 본문 20초
RETRY     = 2          # 각 경로 재시도 횟수
SLEEP     = 1.2        # 재시도 사이 대기
SCAN_MAX  = 30         # 한 번 실행에서 확인할 최대 idx 개수

# 상태파일 읽기
def read_last():
    try:
        return int(open(ID_FILE, encoding="utf-8").read().strip())
    except FileNotFoundError:
        return None
    except Exception:
        return None

# 상태파일 쓰기
def write_last(idx: int):
    with open(ID_FILE, "w", encoding="utf-8") as f:
        f.write(str(idx))

# 워커 경유 요청
def fetch_via_worker(url: str) -> requests.Response:
    if not WORKER:
        raise RuntimeError("no worker")
    proxied = f"{WORKER}?url={quote(url, safe='')}"
    return requests.get(proxied, headers=HEADERS, timeout=TIMEOUT)

# 단일 URL을 여러 경로로 받아오기
def robust_get(url_https: str) -> tuple[str, str] | None:
    # 반환값: (mode, text)  mode는 html 또는 markdown
    routes = []
    if WORKER:
        routes.append(("worker", url_https))
    routes.append(("rja", RJA_HTTP.format(idx=url_https.split("idx=")[1].split("&")[0])))
    routes.append(("rja", RJA_HTTPS.format(idx=url_https.split("idx=")[1].split("&")[0])))
    routes.append(("direct_https", url_https))
    routes.append(("direct_http", url_https.replace("https://", "http://", 1)))

    for label, url in routes:
        for i in range(1, RETRY + 1):
            try:
                if label == "worker":
                    r = fetch_via_worker(url)
                else:
                    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if r.status_code == 200 and r.text.strip():
                    mode = "markdown" if label == "rja" else "html"
                    return mode, r.text
            except Exception:
                pass
            time.sleep(SLEEP)
    return None

# 상세페이지에서 제목 추출
def parse_title_from_html(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    # 여러 후보를 순서대로 시도
    for sel in [
        ".board_view .title", ".view .title", "h1", "h2", "h3", "title"
    ]:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(" ", strip=True)
            if title:
                # <title>에 사이트명이 붙으면 잘라내기
                title = re.sub(r"\s*\|\s*.*$", "", title)
                return title
    # 혹시 본문에 제목만 단독으로 있는 경우
    text = soup.get_text("\n", strip=True)
    line = next((ln for ln in text.splitlines() if ln.strip()), None)
    return line

# r.jina.ai 마크다운에서 제목 추출
def parse_title_from_md(md: str) -> str | None:
    # 헤더 라인 우선
    for m in re.finditer(r"^\s*#{1,6}\s+(.+)$", md, flags=re.M):
        t = m.group(1).strip()
        if t:
            return t
    # 첫 줄 텍스트
    for ln in md.splitlines():
        ln = ln.strip()
        if ln and not ln.startswith("http"):
            return ln[:120]
    return None

# 특정 idx의 글 존재 여부와 제목 가져오기
def fetch_post(idx: int) -> tuple[str, str] | None:
    url = BASE_VIEW.format(idx=idx)
    got = robust_get(url)
    if not got:
        return None
    mode, text = got
    # 존재하지 않는 글은 보통 빈 페이지거나 안내 문구가 뜸
    if "없는 게시물" in text or "잘못된 접근" in text:
        return None
    if mode == "html":
        title = parse_title_from_html(text)
    else:
        title = parse_title_from_md(text)
    if not title:
        return None
    return title, url

# 연속 idx 스캔
def scan_new_posts(start_idx: int) -> list[tuple[int, str, str]]:
    found = []
    for i in range(start_idx, start_idx + SCAN_MAX):
        got = fetch_post(i)
        if got:
            title, url = got
            found.append((i, title, url))
    return found

# 디스코드 전송
def send(msg: str):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

# 메인 루틴
def main():
    if not WEBHOOK:
        sys.exit("DISCORD_WEBHOOK_INFOCOM 시크릿 누락")

    last_id = read_last()
    if last_id is None:
        # 처음 설정이거나 last 파일이 없을 때는 안전을 위해 스킵
        # 브라우저로 최신 글의 idx를 확인해 last_infocom_id.txt에 저장해 주세요.
        print("초기 last_infocom_id.txt가 없습니다. 이번 주기 스킵")
        return

    posts = scan_new_posts(last_id + 1)
    if not posts:
        print("새 공지 없음")
        return

    # 오래된 것부터 전송
    for idx, title, link in posts:
        send(f"전자정보공학부 새 공지\n{title}\n{link}")
        write_last(idx)
        print(f"전송 완료: {idx} {title}")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("예상치 못한 오류. 다음 주기에서 재시도")
