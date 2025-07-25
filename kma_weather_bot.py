# kma_weather_bot.py ─ 기상청 동네예보 우산 알림 (POP ≥ 60 % and PCP ≥ 1 mm)
# • 24 h 안에 ‘강수확률 ≥ 60 %, 강수량 ≥ 1 mm’ 조건을 만족하는
#   3 시간 구간(예보 단위)만 골라 디스코드로 상세 전송
# • 필요 Secrets
#     KMA_API_KEY              # 기상청 Encoding 인증키
#     DISCORD_WEBHOOK_UMBRELLA  # 우산 알림용 Discord Webhook
# --------------------------------------------------------------------
import os, sys, requests, datetime as dt
from urllib.parse import urlencode

WEBHOOK = os.getenv("DISCORD_WEBHOOK_UMBRELLA")
SERVICE_KEY = os.getenv("KMA_API_KEY")

# 서울 종로구 격자 좌표
NX, NY = 60, 127

POP_THRESHOLD  = 0      # 강수확률 ≥ 60 %
PCP_THRESHOLD  = 0.0     # 시간당 강수량 ≥ 1 mm
HOURS_AHEAD    = 24      # 앞으로 24 시간만 검사

KST = dt.timezone(dt.timedelta(hours=9))


# ── base_date / base_time 계산 (2,5,8,11,14,17,20,23) ────────────────
def latest_base():
    now = dt.datetime.now(KST)
    for h in (23, 20, 17, 14, 11, 8, 5, 2):
        if now.hour >= h:
            return now.strftime("%Y%m%d"), f"{h:02}00"
    yest = now - dt.timedelta(days=1)
    return yest.strftime("%Y%m%d"), "2300"


# ── 기상청 API 호출 ────────────────────────────────────────────────
def fetch_items():
    base_date, base_time = latest_base()
    params = {
        "dataType": "JSON",
        "numOfRows": 500,
        "pageNo": 1,
        "base_date": base_date,
        "base_time": base_time,
        "nx": NX,
        "ny": NY,
    }
    url = ("http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
           f"?serviceKey={SERVICE_KEY}&{urlencode(params)}")
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()["response"]["body"]["items"]["item"]


# ── 예보 item → (timestamp, POP, PCP_mm) 리스트로 변환 ─────────────
def parse_forecast(items):
    bucket = {}
    for item in items:
        key = item["fcstDate"] + item["fcstTime"]          # 'YYYYMMDDHHMM'
        bucket.setdefault(key, {})[item["category"]] = item["fcstValue"]

    forecasts = []
    for k, v in bucket.items():
        ts = dt.datetime.strptime(k, "%Y%m%d%H%M").replace(tzinfo=KST)
        pop = int(v.get("POP", "0"))
        pcp_raw = v.get("PCP", "0")
        if pcp_raw in ("", "강수없음"):
            pcp = 0.0
        elif "mm미만" in pcp_raw:
            pcp = 0.5
        else:
            pcp = float(pcp_raw.replace("mm", ""))
        forecasts.append((ts, pop, pcp))
    return sorted(forecasts)


# ── 조건(POP ≥ 60, PCP ≥ 1) 만족 구간 계산 ────────────────────────
def select_rain_segments(forecasts):
    now = dt.datetime.now(KST)
    until = now + dt.timedelta(hours=HOURS_AHEAD)
    segs = []
    for ts, pop, pcp in forecasts:
        if not (now <= ts < until):
            continue
        if pop >= POP_THRESHOLD and pcp >= PCP_THRESHOLD:
            segs.append((ts, pop, pcp))
    return segs


# ── 메시지 포맷 ───────────────────────────────────────────────────
def format_segments(segs):
    lines = []
    for ts, pop, pcp in segs:
        end = ts + dt.timedelta(hours=3)   # 동네예보 시간 단위 = 3 h
        lines.append(f"{ts:%m월 %d일} {ts.hour:02d}시~{end.hour:02d}시 "
                     f"☔ {pcp:.1f} mm / 강수확률 {pop}%")
    return "\n".join(lines)


# ── 메인 ─────────────────────────────────────────────────────────
def main():
    if not (WEBHOOK and SERVICE_KEY):
        sys.exit("❌  DISCORD_WEBHOOK_UMBRELLA 또는 KMA_API_KEY 누락")

    items = fetch_items()
    segs = select_rain_segments(parse_forecast(items))

    if not segs:
        print("☀️  POP < 60% or PCP < 1 mm — 알림 생략")
        return

    msg = "☂️ **오늘 비 예보 상세**\n" + format_segments(segs)
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)
    print("✅  우산 알림 전송 완료")


if __name__ == "__main__":
    main()
