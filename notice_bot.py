# notice_bot.py (발췌)

import os
import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 환경변수 우선, 없으면 config.json 백업용
WEBHOOK_URL = os.getenv("https://discord.com/api/webhooks/1397215877254090813/NfGQuTwoGUr8Q694ZUvZTe_sE5q7k0YU5KvF5k_LHeas5hHaDL-vlVUFIc4IqCHDf1ym")

if not WEBHOOK_URL:
    with open("config.json") as f:
        WEBHOOK_URL = json.load(f)["https://discord.com/api/webhooks/1397215877254090813/NfGQuTwoGUr8Q694ZUvZTe_sE5q7k0YU5KvF5k_LHeas5hHaDL-vlVUFIc4IqCHDf1ym"]

NOTICE_URL = "https://scatch.ssu.ac.kr/공지사항"
LAST_NOTICE_FILE = "last_notice_id.txt"

def get_latest_notice():
    # Selenium → BeautifulSoup 로직 그대로 (생략)
    return notice_id, title, link

def read_last_id():
    try:
        with open(LAST_NOTICE_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

def write_last_id(nid):
    with open(LAST_NOTICE_FILE, "w") as f:
        f.write(str(nid))

def send(msg):
    requests.post(WEBHOOK_URL, json={"content": msg})

def main():
    last_id = read_last_id()
    notice_id, title, link = get_latest_notice()

    # 새 글이면 알림
    if notice_id and notice_id != last_id:
        send(f"새 학사 공지\n{title}\n{link}")
        write_last_id(notice_id)

if __name__ == "__main__":
    main()
