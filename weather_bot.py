# 역할: 매일 아침(07 시 KST) 오늘 예보에서 강수량이 0 mm 초과인 시간대를 찾아
#       비 오는 날에만 디스코드로 “우산 챙기세요” 알림을 보냅니다.

import os
import sys
import requests
from datetime import datetime, timedelta, timezone
from collections import defaultdict

# ── 환경설정 ──────────────────────────────────────────────────────────────
API_KEY  = os.getenv("KMA_API_KEY")             # 기상청 Encoding 인증키
WEBHOOK  = os.getenv("DISCORD_WEBHOOK_UMBRELLA")
NX, NY   = 60, 127                              # 서울 시청 격자 좌표

if not (API_KEY and WEBHOOK):
    sys.exit("❌ KMA_API_KEY 또는 DISCORD_WEBHOOK_UMBRELLA 시크릿이 없습니다")

# 서울(KST) 기준 현재 시각
KST = timezone(timedelta(hours=9))
now = datetime.now(KST)

# 기상청 단기예보(base_time 05:00) 호출에 쓸 기준 날짜·시간
if now.hour < 5:
    base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
else:
    base_date = now.strftime("%Y%m%d")
base_time = "0500"

URL = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
params = {
    "serviceKey": API_KEY,
    "pageNo": 1,
    "numOfRows": 1000,
    "dataType": "JSON",
    "base_date": base_date,
    "base_time": base_time,
    "nx": NX,
    "ny": NY,
}

def fetch_rain_forecast():
    res = requests.get(URL, params=params, timeout=10)
    res.raise_for_status()
    items = res.json()["response"]["body"]["items"]["item"]
    rain = defaultdict(str)               # {HHMM: "0mm" or "강수없음" or "1mm"}
    for it in items:
        if it["category"] == "PCP":       # 1시간 강수량
            rain[it["fcstTime"]] = it["fcstValue"]
    return rain

def parse_rain_ranges(rain_dict):
    """강수 시간대를 [ (start, end, mm_sum), ... ] 형태로 묶어 반환"""
    times = sorted(rain_dict.keys())
    ranges = []
    cur_start, cur_sum = None, 0.0

    for t in times:
        val = rain_dict[t]
        if val in ("강수없음", "0mm"):
            if cur_start is not None:
                ranges.append((cur_start, prev_t, cur_sum))
                cur_start, cur_sum = None, 0.0
        else:
            mm = 0.0
            if val.endswith("mm"):
                try:
                    mm = float(val.replace("mm", ""))
                except ValueError:
                    pass
            if cur_start is None:
                cur_start = t
            cur_sum += mm
        prev_t = t

    if cur_start is not None:                      # 마지막 구간 닫기
        ranges.append((cur_start, prev_t, cur_sum))
    return ranges

def send_discord(message: str):
    requests.post(WEBHOOK, json={"content": message}, timeout=10)

def main():
    rain = fetch_rain_forecast()
    ranges = parse_rain_ranges(rain)

    if not ranges:
        print("⛅ 오늘은 비 예보가 없습니다")
        return

    date_str = now.strftime("%m월 %d일")
    lines = [f"☔ {date_str} 서울 날씨 요약"]

    for st, et, total in ranges:
        st_h = f"{st[:2]}시"
        et_h = f"{str(int(et[:2])+1).zfill(2)}시"   # 예보는 종료시 시각+1 까지 비슷
        lines.append(f"{st_h} ~ {et_h} 사이 약 {total:.1f} mm의 비 예상")

    lines.append("오늘 외출 시 우산을 챙기세요!")
    send_discord("\n".join(lines))
    print("✅ 우산 알림 전송 완료")

if __name__ == "__main__":
    main()
