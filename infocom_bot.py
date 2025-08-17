import os
import re
import sys
import json
import traceback
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs

# 디스코드 웹훅 (환경변수 우선, 없으면 config.json 백업)
WEBHOOK = os.getenv("DISCORD_WEBHOOK_INFOCOM")
if not WEBHOOK:
    try:
        with open("config.json", encoding="utf-8") as f:
            WEBHOOK = json.load(f)["DISCORD_WEBHOOK_INFOCOM"]
    except Exception:
        sys.exit("❌ DISCORD_WEBHOOK_INFOCOM 시크릿(또는 config.json) 누락")

# 공지 목록 URL 및 상수
BASE       = "https://infocom.ssu.ac.kr"
LIST_URL   = f"{BASE}/kor/notice/undergraduate.php"
ID_FILE    = "last_infocom_id.txt"
HEADERS    = {"User-Agent": "Mozilla/5.0"}  # 간단한 봇 차단 회피용
TIMEOUT    = 15

def read_last_id():
    """마지막으로 전송한 글의 idx를 읽는다."""
    try:
        return open(ID_FILE, encoding="utf-8").read().strip()
    except FileNotFoundError:
        return None

def write_last_id(idx: str):
    """마지막으로 전송한 글의 idx를 기록한다."""
    with open(ID_FILE, "w", encoding="utf-8") as f:
        f.write(str(idx))

def extract_idx(href: str) -> str | None:
    """글 링크의 쿼리에서 idx 숫자를 뽑아낸다."""
    try:
        qs = parse_qs(urlparse(href).query)
        if "idx" in qs and qs["idx"]:
            return str(qs["idx"][0])
    except Exception:
        pass
    m = re.search(r"[?&]idx=(\d+)", href or "")
    return m.group(1) if m else None

def fetch_new_posts(last_id: str | None):
    """
    목록 페이지에서 앵커들을 훑어 (idx, title, link) 리스트를 만든다.
    last_id 이전 글을 만나면 중단하고, 새 글들만 반환한다.
    반환은 오래된 글부터 전송할 수 있게 역순으로 정렬한다.
    """
    try:
        resp = requests.get(LIST_URL, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        html = resp.text
    except Exception:
        traceback.print_exc()
        sys.exit("🚫 목록 페이지 요청 실패")

    soup = BeautifulSoup(html, "html.parser")

    # 이 사이트는 같은 페이지에서 보기(view)로 연결되는 형태이며,
    # href에 undergraduate.php와 idx 파라미터가 포함되어 있음.
    anchors = soup.select('a[href*="undergraduate.php"][href*="idx="]')
    if not anchors:
        # 구조 변화 진단을 위해 디버그 파일 저장
        with open("infocom_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        sys.exit("🚫 공지 링크를 찾지 못했습니다(셀렉터 불일치). infocom_debug.html 확인")

    new_posts = []
    for a in anchors:
        href = a.get("href")
        link = urljoin(BASE, href)
        idx  = extract_idx(link)
        if not idx:
            continue
        if last_id and idx == last_id:
            break  # 마지막으로 본 글에 도달 → 그 이전은 이미 전송됨

        # 제목은 앵커 텍스트 기준으로 추출
        title = a.get_text(" ", strip=True)
        if not title:
            # 부모 요소에 텍스트가 있을 가능성까지 고려
            title = a.find_parent().get_text(" ", strip=True) if a.find_parent() else "제목 없음"

        new_posts.append((idx, title, link))

    # 최신 → 오래된 순으로 수집되었을 수 있으니 전송은 오래된 것부터
    new_posts.reverse()
    return new_posts

def send_to_discord(msg: str):
    """디스코드 웹훅으로 메시지 전송."""
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)

def main():
    """메인 루틴: 새 글들을 모두 전송하고 마지막 idx 갱신."""
    last_id = read_last_id()
    posts = fetch_new_posts(last_id)

    if not posts:
        print("⏸ 새 공지 없음")
        return

    for idx, title, link in posts:
        send_to_discord(f"🔔 전자정보공학부 새 공지\n{title}\n{link}")
        write_last_id(idx)
        print(f"✅ 전송 완료: {idx} {title}")

if __name__ == "__main__":
    main()
