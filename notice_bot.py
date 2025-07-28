import os, sys, json, re, requests, textwrap, traceback
from bs4 import BeautifulSoup

# ── 환경 변수 ───────────────────────────────────────────────
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
OPENAI_KEY  = os.getenv("OPENAI_API_KEY")     # ← 새로 추가
if not WEBHOOK_URL:
    try:
        with open("config.json", encoding="utf-8") as f:
            WEBHOOK_URL = json.load(f)["DISCORD_WEBHOOK_URL"]
    except Exception:
        sys.exit("❌ DISCORD_WEBHOOK_URL 설정이 없습니다")

if OPENAI_KEY:
    import openai
    openai.api_key = OPENAI_KEY

NOTICE_URL = "https://scatch.ssu.ac.kr/공지사항/"
LAST_FILE  = "last_notice_id.txt"
UA_HEADER  = {"User-Agent": "Mozilla/5.0"}

# ── 상태 파일 I/O ───────────────────────────────────────────
read_last  = lambda: open(LAST_FILE).read().strip() if os.path.exists(LAST_FILE) else None
write_last = lambda x: open(LAST_FILE, "w").write(x)

# ── GPT 요약 (없으면 생략) ───────────────────────────────────
def summarize(txt: str) -> str:
    if not OPENAI_KEY:
        return ""  # 요약 생략
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": "다음 학사 공지를 한국어로 최대 3줄 핵심 요약:\n" + txt
            }],
            max_tokens=120, temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print("GPT 요약 실패:", e)
        return ""

# ── 공지 목록 파싱 ───────────────────────────────────────────
def fetch_new_notices(last_id):
    html = requests.get(NOTICE_URL, headers=UA_HEADER, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    posts = []
    for a in soup.select("ul.notice-lists li a"):
        link = a["href"]
        if link.startswith("/"):
            link = "https://scatch.ssu.ac.kr" + link
        m = re.search(r"[?&]num=(\d+)", link)
        nid = m.group(1) if m else link
        if nid == last_id:
            break
        title = a.get_text(" ", strip=True)

        # 본문 HTML → 텍스트 (요약용)
        try:
            art = requests.get(link, headers=UA_HEADER, timeout=10).text
            body = BeautifulSoup(art, "html.parser").get_text(" ", strip=True)
            body = textwrap.shorten(body, 4000)
        except Exception:
            body = ""

        posts.append((nid, title, link, body))

    return list(reversed(posts))  # 오래된 것부터

# ── 디스코드 전송 ────────────────────────────────────────────
def send(content):
    requests.post(WEBHOOK_URL, json={"content": content}, timeout=10)

# ── 메인 ────────────────────────────────────────────────────
def main():
    last_id = read_last()
    try:
        new_posts = fetch_new_notices(last_id)
    except Exception:
        traceback.print_exc()
        sys.exit("🚫 공지 파싱 실패")

    if not new_posts:
        print("⏸ 새 글 없음"); return

    for nid, title, link, body in new_posts:
        summary = summarize(body)
        msg = f"📢 **새 학사 공지**\n{title}"
        if summary:
            msg += f"\n{summary}"
        msg += f"\n{link}"
        send(msg)
        write_last(nid)
        print(f"✅ 전송: {nid}")

if __name__ == "__main__":
    main()
