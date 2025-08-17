# infocom_bot.py
# 전자정보공학부 학부 공지(undergraduate) 모니터링 봇
# 기능
#   - 새 공지가 여러 개면 마지막으로 보낸 글 이후 전부를 오래된 것부터 전송
#   - GitHub Actions에서 학교 서버 타임아웃을 피하려고 Cloudflare Worker 프록시를 우선 사용
#   - 구조가 바뀌면 디버그 HTML 저장
#
# 필요 시크릿
#   DISCORD_WEBHOOK_INFOCOM      디스코드 웹훅
#   INFOCOM_PROXY_URL            선택. 예: https://your-worker.workers.dev/?url=
#
# 워크플로에서는 위 시크릿을 env로 주입

import os
import re
import sys
import json
import time
import traceback
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, quote

# 디스코드 웹훅 로드
WEBHOOK = os.getenv("DISCORD_WEBHOOK_INFOCOM")
if not WEBHOOK:
    try:
        with open("config.json", encoding="utf-8") as f:
            WEBHOOK = json.load(f)["DISCORD_WEBHOOK_INFOCOM"]
    except Exception:
        sys.exit("DISCORD_WEBHOOK_INFOCOM 시크릿(또는 config.json) 누락")

# 프록시 워커 주소. 예: https://my-worker.user.workers.dev/?url=
WORKER = os.getenv("INFOCOM_PROXY_URL", "").rstrip("/")  # 없으면 빈 문자열

# 상수
BASE       = "https://infocom.ssu.ac.kr"
LIST_PATH  = "/kor/notice/undergraduate.php"
LIST_HTTPS = BASE + LIST_PATH
LIST_HTTP  = "http://infocom.ssu.ac.kr" + LIST_PATH
ID_FILE    = "last_infocom_id.txt"
HEADERS    = {"User-Agent": "Mozilla/5.0"}
TIMEOUT    = 15

def read_last_id():
    try:
        return open(ID_FILE, encoding="utf-8").read().strip()
    except FileNotFoundError:
        return None

def write_last_id(idx: str):
    with open(ID_FILE, "w", encoding="utf-8") as f:
        f.write(str(idx))

def extract_idx(href: str) -> str | None:
    # 글 링크 쿼리의 idx 값을 추출
    try:
        qs = parse_qs(urlparse(href).query)
        if "idx" in qs and qs["idx"]:
            return str(qs["idx"][0])
    except Exception:
        pass
    m = re.search(r"[?&]idx=(\d+)", href or "")
    return m.group(1) if m else None

def get_with_worker(url: str) -> requests.Response:
    # Cloudflare Worker를 통한 프록시 GET
    proxied = f"{WORKER}?url={quote(url, safe='')}"
    return requests.get(proxied, headers=HEADERS, timeout=TIMEOUT)

def robust_get_list_html() -> str | None:
    # 목록 HTML을 최대 3회 재시도. 우선순위: Worker → HTTPS → HTTP
    candidates = []
    if WORKER:
        candidates.append(("worker", LIST_HTTPS))
    candidates.append(("https", LIST_HTTPS))
    candidates.append(("http", LIST_HTTP))

    for label, url in candidates:
        for attempt in range(1, 4):
            try:
                if label == "worker":
                    r = get_with_worker(url)
                else:
                    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if r.status_code == 200 and r.text.strip():
                    print(f"소스 확보 성공: {label} try {attempt}")
                    return r.text
                else:
                    print(f"비정상 응답: {label} try {attempt} status {r.status_code}")
            except Exception as e:
                print(f"요청 실패: {label} try {attempt} {e}")
            time.sleep(1.5)
    return None

def fetch_new_posts(last_id: str | None):
    # 목록에서 (idx, title, link) 튜플을 모으고, last_id 이전에서 중단
    html = robust_get_list_html()
    if not html:
        print("목록 요청 실패. 다음 주기까지 대기")
        return []

    soup = BeautifulSoup(html, "html.parser")

    # undergraduate.php로 가는 링크 중 idx 파라미터가 있는 것만 선택
    anchors = soup.select('a[href*="undergraduate.php"][href*="idx="]')
    if not anchors:
        # 구조가 바뀐 경우를 대비해 디버그 저장
        with open("infocom_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("공지 링크를 찾지 못했습니다. infocom_debug.html 확인")
        return []

    new_posts = []
    for a in anchors:
        href = a.get("href")
        link = urljoin(BASE, href)
        idx  = extract_idx(link)
        if not idx:
            continue
        if last_id and idx == last_id:
            break

        title = a.get_text(" ", strip=True) or "제목 없음"
        new_posts.append((idx, title, link))

    new_posts.reverse()  # 오래된 것부터 전송
    return new_posts

def send_to_discord(msg: str):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    last_id = read_last_id()
    try:
        posts = fetch_new_posts(last_id)
    except Exception:
        traceback.print_exc()
        print("파싱 중 예외 발생. 이번 주기 스킵")
        return

    if not posts:
        print("새 공지 없음")
        return

    for idx, title, link in posts:
        send_to_discord(f"전자정보공학부 새 공지\n{title}\n{link}")
        write_last_id(idx)
        print(f"전송 완료: {idx} {title}")

if __name__ == "__main__":
    main()
