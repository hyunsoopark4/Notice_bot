# notice_bot.py
# 역할: GitHub Actions가 1시간 간격으로 실행할 때
#       새 공지사항이 있으면 디스코드 웹훅으로 알림을 보내는 스크립트

import os
import sys
import json
import requests
from bs4 import BeautifulSoup

# 1) 환경변수에서 웹훅 URL 읽기
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# 2) 로컬 개발용 백업: config.json에
#    {"DISCORD_WEBHOOK_URL": "웹훅주소"} 형태로 넣어 두면 동작
if not WEBHOOK_URL:
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            WEBHOOK_URL = json.load(f)["DISCORD_WEBHOOK_URL"]
    except (FileNotFoundError, KeyError):
        sys.exit("DISCORD_WEBHOOK_URL 환경변수가 없고 config.json도 없습니다")

# 3) 공지사항 페이지 URL
NOTICE_URL = "https://scatch.ssu.ac.kr/%EA%B3%B5%EC%A7%80%EC%82%AC%ED%95%AD/"

# 4) 마지막으로 보낸 공지 ID를 저장해 둘 파일
LAST_NOTICE_FILE = "last_notice_id.txt"


def get_latest_notice():
    """
    공지사항 목록 페이지에서 가장 최신 글의 ID‧제목‧링크를 추출한다.
    사이트 구조가 바뀌면 CSS 선택자를 수정해야 한다.
    """
    resp = requests.get(NOTICE_URL, timeout=10, allow_redirects=True)
    print("DEBUG status_code:", resp.status_code)
    print("DEBUG final_url   :", resp.url[:100])   # 리다이렉트 여부 확인

    # ↓ 실패 로그가 계속 나오면 HTML 일부를 파일로 남겨 Actions 아티팩트로 확인
    with open("debug.html", "w", encoding="utf-8") as f:
        f.write(resp.text[:2000])          # 앞부분만 저장
        
    resp = requests.get(NOTICE_URL, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # 예시: 표 기반 게시판이라 가정하고 첫 행을 선택
    first_row = soup.select_one("table tbody tr")
    if not first_row:
        return None, None, None

    # 글 번호나 data 속성을 ID로 사용
    notice_id = first_row.get("data-uid") or first_row.select_one("td").get_text(strip=True)

    title_tag = first_row.select_one("a")
    title = title_tag.get_text(strip=True)

    link = title_tag["href"]
    if not link.startswith("http"):
        link = f"https://scatch.ssu.ac.kr{link}"

    return notice_id, title, link


def read_last_id():
    try:
        with open(LAST_NOTICE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None


def write_last_id(nid: str):
    with open(LAST_NOTICE_FILE, "w", encoding="utf-8") as f:
        f.write(str(nid))


def send_to_discord(msg: str):
    payload = {"content": msg}
    resp = requests.post(WEBHOOK_URL, json=payload, timeout=10)
    resp.raise_for_status()


def main():
    last_id = read_last_id()
    notice_id, title, link = get_latest_notice()

    if not notice_id:
        print("공지사항을 가져오지 못했습니다")
        return

    # 새 글이면 알림 전송 후 ID 저장
    if notice_id != last_id:
        send_to_discord(f"새 학사 공지: {title}\n{link}")
        write_last_id(notice_id)
    else:
        print("새 공지가 없습니다")


if __name__ == "__main__":
    main()
