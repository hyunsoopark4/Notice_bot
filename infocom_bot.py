# infocom_bot.py
# 전자정보공학부(학부) 공지 모니터링 봇
# 기능
#   1) Cloudflare Worker 우선 요청, 500/타임아웃 시 r.jina.ai 텍스트 프록시 폴백
#   2) 마지막 전송 글 이후의 새 글을 모두, 오래된 것부터 디스코드로 전송
#   3) 구조 변경 시 디버그 파일 저장
#
# 필요 시크릿
#   DISCORD_WEBHOOK_INFOCOM     디스코드 웹훅
#   INFOCOM_PROXY_URL           선택. 예: https://your-worker.workers.dev/?url=

import os
import re
import sys
import json
import time
import traceback
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, quote

# 시크릿 로드
WEBHOOK = os.getenv("DISCORD_WEBHOOK_INFOCOM")
if not WEBHOOK:
    try:
        with open("config.json", encoding="utf-8") as f:
            WEBHOOK = json.load(f)["DISCORD_WEBHOOK_INFOCOM"]
    except Exception:
        sys.exit("DISCORD_WEBHOOK_INFOCOM 시크릿 또는 config.json 누락")

WORKER = os.getenv("INFOCOM_PROXY_URL", "").rstrip("/")  # 예: https://xxx.workers.dev/?url=

# 상수
BASE        = "https://infocom.ssu.ac.kr"
LIST_PATH   = "/kor/notice/undergraduate.php"
LIST_HTTPS  = BASE + LIST_PATH
LIST_HTTP   = "http://infocom.ssu.ac.kr" + LIST_PATH
RJA_HTTPS   = "https://r.jina.ai/http://infocom.ssu.ac.kr" + LIST_PATH  # r.jina.ai는 http 주소를 권장
RJA_HTTP    = "https://r.jina.ai/https://infocom.ssu.ac.kr" + LIST_PATH # 혹시 몰라 https 원문 버전도 시도

ID_FILE   = "last_infocom_id.txt"
HEADERS   = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://infocom.ssu.ac.kr/",
    "Connection": "keep-alive",
}
TIMEOUT = 25
RETRY   = 3
SLEEP   = 1.5

# 상태 파일 IO
def read_last_id():
    try:
        return open(ID_FILE, encoding="utf-8").read().strip()
    except FileNotFoundError:
        return None

def write_last_id(idx: str):
    with open(ID_FILE, "w", encoding="utf-8") as f:
        f.write(str(idx))

# 링크에서 idx 추출
def extract_idx(href: str) -> str | None:
    try:
        qs = parse_qs(urlparse(href).query)
        if "idx" in qs and qs["idx"]:
            return str(qs["idx"][0])
    except Exception:
        pass
    m = re.search(r"[?&]idx=(\d+)", href or "")
    return m.group(1) if m else None

# 워커 요청
def get_with_worker(url: str) -> requests.Response:
    proxied = f"{WORKER}?url={quote(url, safe='')}"
    return requests.get(proxied, headers=HEADERS, timeout=TIMEOUT)

# 목록 소스 확보: 성공 시 (mode, text) 반환. mode는 html 또는 markdown
def robust_get_list_source():
    print(f"WORKER 설정: {'ON' if WORKER else 'OFF'}")
    # 시도 순서: worker(html) → r.jina.ai(markdown) → https(html) → http(html)
    candidates = []
    if WORKER:
        candidates.append(("worker", LIST_HTTPS))
    candidates.append(("rja", RJA_HTTPS))
    candidates.append(("rja", RJA_HTTP))
    candidates.append(("https", LIST_HTTPS))
    candidates.append(("http", LIST_HTTP))

    for label, url in candidates:
        for attempt in range(1, RETRY + 1):
            try:
                if label == "worker":
                    r = get_with_worker(url)
                else:
                    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if r.status_code == 200 and r.text.strip():
                    mode = "markdown" if label == "rja" else "html"
                    print(f"소스 확보 성공: {label} try {attempt} mode={mode}")
                    return mode, r.text
                print(f"비정상 응답: {label} try {attempt} status {r.status_code}")
            except Exception as e:
                print(f"요청 실패: {label} try {attempt} {e}")
            time.sleep(SLEEP)
    return None, None

# HTML 모드 파서
def parse_html_list(html: str, last_id: str | None):
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.select('a[href*="undergraduate.php"][href*="idx="]')
    if not anchors:
        with open("infocom_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("공지 링크를 찾지 못했습니다. infocom_debug.html 확인")
        return []

    posts = []
    for a in anchors:
        href = a.get("href") or ""
        link = urljoin(BASE, href)
        idx  = extract_idx(link)
        if not idx:
            continue
        if last_id and idx == last_id:
            break
        title = a.get_text(" ", strip=True) or "제목 없음"
        posts.append((idx, title, link))

    posts.reverse()
    return posts

# r.jina.ai 마크다운 모드 파서
def parse_markdown_list(md: str, last_id: str | None):
    """
    r.jina.ai는 페이지를 텍스트로 변환해 [제목](링크) 형태를 많이 유지한다.
    여기서 undergraduate.php 와 idx=숫자를 포함한 링크만 추려서 사용한다.
    """
    posts = []
    seen = set()
    # 우선 [제목](링크) 패턴 우선 파싱
    for m in re.finditer(r"\[([^\]]+)\]\((https?://[^\s)]+undergraduate\.php[^\s)]*idx=\d+[^\s)]*)\)", md, flags=re.I):
        title = m.group(1).strip()
        link  = m.group(2).strip()
        idx   = extract_idx(link)
        if not idx or idx in seen:
            continue
        if last_id and idx == last_id:
            break
        seen.add(idx)
        posts.append((idx, title or "제목 없음", link))

    # 혹시 위에서 못 잡은 경우를 대비해 URL 만 있는 패턴도 추가 스캔
    if not posts:
        for m in re.finditer(r"(https?://[^\s)]+undergraduate\.php[^\s)]*idx=\d+[^\s)]*)", md, flags=re.I):
            link = m.group(1).strip()
            idx  = extract_idx(link)
            if not idx or idx in seen:
                continue
            if last_id and idx == last_id:
                break
            seen.add(idx)
            posts.append((idx, "제목 없음", link))

    posts.reverse()
    return posts

def fetch_new_posts(last_id: str | None):
    mode, text = robust_get_list_source()
    if not text:
        print("목록 요청 실패. 다음 주기 대기")
        return []

    if mode == "markdown":
        return fetch_from_markdown(text, last_id)
    else:
        return parse_html_list(text, last_id)

def fetch_from_markdown(md_text: str, last_id: str | None):
    posts = parse_markdown_list(md_text, last_id)
    if not posts:
        with open("infocom_debug_md.txt", "w", encoding="utf-8") as f:
            f.write(md_text)
        print("마크다운에서 링크를 찾지 못했습니다. infocom_debug_md.txt 확인")
    return posts

def send_to_discord(msg: str):
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    last_id = read_last_id()
    try:
        posts = fetch_new_posts(last_id)
    except Exception:
        traceback.print_exc()
        print("파싱 중 예외. 이번 주기 스킵")
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
