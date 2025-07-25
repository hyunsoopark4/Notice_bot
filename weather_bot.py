# kma_weather_bot.py ― KMA 동네예보 기반 우산 알림
# ─────────────────────────────────────────────────────────────
# • 앞으로 24 시간 안에 비(PTY≠0) 또는 강수량(PCP≠'강수없음')이
#   예보돼 있으면 한 번만 디스코드 웹훅으로 알림 전송
# • Secrets
#     KMA_API_KEY            기상청(데이터포털) Encoded 서비스 키
#     DISCORD_WEBHOOK_UMBRELLA  우산 알림용 디스코드 웹훅
# • GitHub Actions 예시: kma_weather.yml (아래)
# ─────────────────────────────────────────────────────────────

import os, sys, requests, datetime as dt
from collections import defaultdict
from urllib.parse import urlencode

# ── 환경 설정 ──────────────────────────────────────────────────
WEBHOOK = os.getenv("DISCORD_WEBHOOK_UMBRELLA")
SERVICE_KEY = os.getenv("KMA_API_KEY")          # 인코딩(Encoding) 값
# 서울(종로구) 격자좌표
NX, NY = 60, 127
RAIN_THRESHOLD = 0.0     # mm, 0.0 이상이면 비로 간주

# ── 기상청 base_time 계산 (2,5,8,11,14,17,20,23 시) ───────────
def latest_base():
    KST = dt.timezone(dt.timedelta(hours=9))
    now = dt.datetime.now(KST)
    base_times = [23, 20, 17, 14, 11, 8, 5, 2]        # 시각 역순
    for bt in base_times:
        if now.hour >= bt:
            return now.date(), f"{bt:02d}00"
    # 0~1시 → 전날 23:00
    return now.date() - dt.timedelta(days=1), "2300"

# ── API 요청 & JSON 파싱 ──────────────────────────────────────
def fetch_items():
    base_date, base_time = latest_base()
    params = {
        "serviceKey": SERVICE_KEY,
        "dataType": "JSON",
        "numOfRows": 500,
        "pageNo": 1,
        "base_date": base_date.strftime("%Y%m%d"),
        "base_time": base_time,
        "nx": NX,
        "ny": NY,
    }
    url = ("http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/"
           f"getVilageFcst?{urlencode(params, safe=':')}")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()["response"]["body"]["items"]["item"]

# ── 24 시간 내에 비 구간 추출 ──────────────────────────────────
def build_rain_windows(items):
    KST = dt.timezone(dt.timedelta(hours=9))
    now = dt.datetime.now(KST)
    until = now + dt.timedelta(hours=24)

    # 예보를 시간별로 묶기 {fcstDate+fcstTime: {category: value}}
    hourly = defaultdict(dict)
    for it in items:
        t = it["fcstDate"] + it["fcstTime"]  # 'YYYYMMDDHHMM'
        hourly[t][it["category"]] = it["fcstValue"]

    windows, cur_start = [], None
    for key in sorted(hourly.keys()):
        ts = dt.datetime.strptime(key, "%Y%m%d%H%M").replace(tzinfo=KST)
        if not (now <= ts < until):
            continue
        h = hourly[key]
        pty = int(h.get("PTY", "0"))
        pcp = h.get("PCP", "0")

        # PCP 값 전처리 : ‘강수없음’ / ‘1mm미만’ / ‘30.0mm’
        if pcp in ("", "강수없음"):
            pcp_mm = 0.0
        elif "mm미만" in pcp:
            pcp_mm = 0.1
        else:
            pcp_mm = float(pcp.replace("mm", ""))

        is_rain = (pty != 0) or (pcp_mm >= RAIN_THRESHOLD)

        if is_rain:
            if cur_start is None:
                cur_start = ts
        else:
            if cur_start:
                windows.append((cur_start, ts))
                cur_start = None
    if cur_start:
        windows.append((cur_start, until))
    return windows

# ── 디스코드 전송 ─────────────────────────────────────────────
def fmt_windows(ws):
    out = []
    for s, e in ws:
        out.append(f"{s:%m월 %d일} {s.hour:02d}시~{e.hour:02d}시")
    return ", ".join(out)

def main():
    if not (WEBHOOK and SERVICE_KEY):
        sys.exit("❌  DISCORD_WEBHOOK_UMBRELLA 또는 KMA_API_KEY 시크릿이 없습니다")

    rain_ws = build_rain_windows(fetch_items())
    if not rain_ws:
        print("☀️  우산 불필요 – 메시지 미전송")
        return

    msg = (f"☂️  오늘 서울에 비 소식!\n"
           f"{fmt_windows(rain_ws)} 사이에 우산을 챙기세요.")
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)
    print("✅  우산 알림 전송 완료")

if __name__ == "__main__":
    main()
