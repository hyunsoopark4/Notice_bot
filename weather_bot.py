# weather_bot.py ─ 비 오는 날만 우산 알림
import os, sys, requests, datetime as dt

WEBHOOK = os.getenv("DISCORD_WEBHOOK_UMBRELLA")  # 디스코드 웹훅
OWM_KEY = os.getenv("OWM_API_KEY")               # OpenWeather API 키
LAT, LON = 37.5665, 126.9780                     # 서울 시청 좌표

THRESH_MM = 0.1       # 시강수량 ≥ 0.1 mm 이면 “우산 챙기세요”
HOURS_SPAN = 24        # 앞으로 24 시간 예보만 검사

def fetch_forecast():
    url = ("https://api.openweathermap.org/data/3.0/onecall?"
           f"lat={LAT}&lon={LON}&exclude=current,minutely,daily,alerts&units=metric&appid={OWM_KEY}")
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()["hourly"][:HOURS_SPAN]

def find_rain_windows(hourly):
    windows = []
    cur_start = None
    for h in hourly:
        rain_mm = h.get("rain", {}).get("1h", 0)
        ts = dt.datetime.fromtimestamp(h["dt"]) + dt.timedelta(hours=9)  # UTC→KST
        if rain_mm >= THRESH_MM:
            if cur_start is None:
                cur_start = ts
        else:
            if cur_start:
                windows.append((cur_start, ts))
                cur_start = None
    if cur_start:
        windows.append((cur_start, cur_start + dt.timedelta(hours=1)))
    return windows

def format_windows(ws):
    out = []
    for s, e in ws:
        mm = s.minute
        out.append(f"{s:%m월 %d일} {s.hour:02d}시~{e.hour:02d}시")
    return ", ".join(out)

def main():
    if not (WEBHOOK and OWM_KEY):
        sys.exit("❌  DISCORD_WEBHOOK_UMBRELLA 또는 OWM_API_KEY 시크릿이 없습니다")

    windows = find_rain_windows(fetch_forecast())

    if not windows:      # 비 예보 없으면 침묵
        print("☀️  우산 불필요 – 메시지 미전송")
        return

    msg = (f"☂️  오늘 서울에 비 소식!\n"
           f"{format_windows(windows)} 사이에 우산이 필요할 수 있어요.")
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)
    print("✅  우산 알림 전송 완료")

if __name__ == "__main__":
    main()
