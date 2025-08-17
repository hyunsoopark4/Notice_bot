# infocom_bot.py — Worker 우선, 연결 튼튼판
# 역할: 전자정보공학부(학부) 공지 최신 글들을 마지막 전송 이후 모두 디스코드로 전송
# 주의: INFOCOM_PROXY_URL 시크릿(예: https://<your>.workers.dev/?url=) 설정 시 Worker 우선 사용

import os, re, sys, json, time, traceback, requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, quote

WEBHOOK = os.getenv("DISCORD_WEBHOOK_INFOCOM")
if not WEBHOOK:
    try:
        with open("config.json", encoding="utf-8") as f:
            WEBHOOK = json.load(f)["DISCORD_WEBHOOK_INFOCOM"]
    except Exception:
        sys.exit("❌ DISCORD_WEBHOOK_INFOCOM 누락")

WORKER = os.getenv("INFOCOM_PROXY_URL", "").rstrip("/")  # 예: https://xxx.workers.dev/?url=

BASE       = "https://infocom.ssu.ac.kr"
LIST_PATH  = "/kor/notice/undergraduate.php"
LIST_HTTPS = BASE + LIST_PATH
LIST_HTTP  = "http://infocom.ssu.ac.kr" + LIST_PATH

ID_FILE    = "last_infocom_id.txt"
# 헤더 보강: 일부 서버가 Accept/Language/Referer 없으면 차단
HEADERS    = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://infocom.ssu.ac.kr/",
    "Connection": "keep-alive",
}
TIMEOUT    = 25
RETRY      = 3
SLEEP      = 1.5

def read_last_id():
    try:
        return open(ID_FILE, encoding="utf-8").read().strip()
    except FileNotFoundError:
        return None

def write_last_id(idx: str):
    with open(ID_FILE, "w", encoding="utf-8") as f:
        f.write(str(idx))

def extract_idx(href: str) -> str | None:
    try:
        qs = parse_qs(urlparse(href).query)
        if "idx" in qs and qs["idx"]:
            return str(qs["idx"][0])
    except Exception:
        pass
    m = re.search(r"[?&]idx=(\d+)", href or "")
    return m.group(1) if m else None

def get_with_worker(url: str) -> requests.Response:
    proxied = f"{WORKER}?url={quote(url, safe='')}"
    return requests.get(proxied, headers=HEADERS, timeout=TIMEOUT)

def robust_get_list_html() -> str | None:
    print(f"WORKER 설정: {'ON' if WORKER else 'OFF'}")
    candidates = []
    if WORKER:
        candidates.append(("worker", LIST_HTTPS))
    candidates.append(("https", LIST_HTTPS))
    candidates.append(("http", LIST_HTTP))

    for label, url in candidates:
        for attempt in range(1, RETRY + 1):
            try:
                r = get_with_worker(url) if label == "worker" else requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                if r.status_code == 200 and r.text.strip():
                    print(f"소스 확보 성공: {label} try {attempt}")
                    return r.text
                print(f"비정상 응답: {label} try {attempt} status {r.status_code}")
            except Exception as e:
                print(f"요청 실패: {label} try {attempt} {e}")
            time.sleep(SLEEP)
    return None

def fetch_new_posts(last_id: str | None):
    html = robust_get_list_html()
    if not html:
        print("목록 요청 실패. 다음 주기 대기")
        return []

    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.select('a[href*="undergraduate.php"][href*="idx="]')
    if not anchors:
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

    new_posts.reverse()
    return new_posts

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
        send_to_discord(f"🔔 전자정보공학부 새 공지\n{title}\n{link}")
        write_last_id(idx)
        print(f"✅ 전송: {idx} {title}")

if __name__ == "__main__":
    main()
