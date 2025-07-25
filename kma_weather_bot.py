# kma_weather_bot.py  –  기상청 우산 알림 (이중 인코딩 버그 수정판)
import os, sys, requests, datetime as dt
from collections import defaultdict
from urllib.parse import urlencode

WEBHOOK = os.getenv("DISCORD_WEBHOOK_UMBRELLA")   # 디스코드 웹훅
SERVICE_KEY = os.getenv("KMA_API_KEY")            # 기상청 Encoding 키

LAT_NX, LAT_NY = 60, 127          # 서울 종로구 격자
THRESH_MM = 0.0                   # 0.0mm 이상이면 비
HOURS_AHEAD = 24                  # 앞으로 24시간

# ── base_date / base_time 계산 (동네예보 표준 2,5,8,11,14,17,20,23시) ──
def latest_base():
    KST = dt.timezone(dt.timedelta(hours=9))
    now = dt.datetime.now(KST)
    for h in (23, 20, 17, 14, 11, 8, 5, 2):
        if now.hour >= h:
            return now.strftime("%Y%m%d"), f"{h:02}00"
    # 0 – 1시 구간은 전날 23시 예보 사용
    yest = now - dt.timedelta(days=1)
    return yest.strftime("%Y%m%d"), "2300"

# ── 동네예보 데이터 조회 ───────────────────────────────────────────
def fetch_items():
    base_date, base_time = latest_base()
    params = {
        "dataType": "JSON",
        "numOfRows": 500,
        "pageNo": 1,
        "base_date": base_date,
        "base_time": base_time,
        "nx": LAT_NX,
        "ny": LAT_NY,
    }
    url = ("http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
           f"?serviceKey={SERVICE_KEY}&{urlencode(params)}")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    try:
        return r.json()["response"]["body"]["items"]["item"]
    except Exception:
        # 디버그용: 잘못된 응답 본문 출력
        print("### KMA raw response ###")
        print(r.text[:500])
        print("########################")
        raise

# ── 24 h 이내 비 구간 계산 ────────────────────────────────────────
def build_rain_windows(items):
    KST = dt.timezone(dt.timedelta(hours=9))
    now = dt.datetime.now(KST)
    until = now + dt.timedelta(hours=HOURS_AHEAD)

    hourly = defaultdict(dict)
    for it in items:
        tkey = it["fcstDate"] + it["fcstTime"]      # 'YYYYMMDDHHMM'
        hourly[tkey][it["category"]] = it["fcstValue"]

    windows, cur = [], None
    for k in sorted(hourly.keys()):
        ts = dt.datetime.strptime(k, "%Y%m%d%H%M").replace(tzinfo=KST)
        if not (now <= ts < until):
            continue
        h = hourly[k]
        pty = int(h.get("PTY", "0"))
        pcp_raw = h.get("PCP", "강수없음")

        if pcp_raw in ("", "강수없음"):
            pcp = 0.0
        elif "mm미만" in pcp_raw:
            pcp = 0.1
        else:
            pcp = float(pcp_raw.replace("mm", ""))

        is_rain = (pty != 0) or (pcp >= THRESH_MM)

        if is_rain and cur is None:
            cur = ts
        elif not is_rain and cur:
            windows.append((cur, ts))
            cur = None
    if cur:
        windows.append((cur, until))
    return windows

def fmt(ws):
    return ", ".join(f"{s:%m월 %d일} {s.hour:02d}시~{e.hour:02d}시" for s, e in ws)

# ── 메인 루틴 ────────────────────────────────────────────────────
def main():
    if not (WEBHOOK and SERVICE_KEY):
        sys.exit("❌  DISCORD_WEBHOOK_UMBRELLA 또는 KMA_API_KEY 누락")

    rain_ws = build_rain_windows(fetch_items())
    if not rain_ws:
        print("☀️  우산 불필요 – 전송 안 함")
        return

    msg = f"☂️  오늘 서울에 비 소식!\n{fmt(rain_ws)} 사이에 우산을 챙기세요."
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)
    print("✅  우산 알림 전송 완료")

if __name__ == "__main__":
    main()
