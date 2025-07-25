# weather_bot.py  –  One Call 2.5 엔드포인트 사용판
import os, sys, requests, datetime as dt

WEBHOOK = os.getenv("DISCORD_WEBHOOK_UMBRELLA")
OWM_KEY = os.getenv("OWM_API_KEY")
LAT, LON = 37.5665, 126.9780      # 서울 시청
THRESH_MM = 0.1
HOURS_SPAN = 24

def fetch_forecast():
    url = ("https://api.openweathermap.org/data/2.5/onecall"  # ← 3.0 → 2.5
           f"?lat={LAT}&lon={LON}"
           f"&exclude=current,minutely,daily,alerts"
           f"&units=metric&appid={OWM_KEY}")
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()["hourly"][:HOURS_SPAN]

def find_rain_windows(hourly):
    windows, cur = [], None
    for h in hourly:
        rain = h.get("rain", {}).get("1h", 0)
        ts = dt.datetime.fromtimestamp(h["dt"]) + dt.timedelta(hours=9)
        if rain >= THRESH_MM:
            if cur is None:
                cur = ts
        elif cur:
            windows.append((cur, ts))
            cur = None
    if cur:
        windows.append((cur, cur + dt.timedelta(hours=1)))
    return windows

def fmt(ws):
    return ", ".join(f"{s:%m월 %d일} {s.hour:02d}시~{e.hour:02d}시" for s, e in ws)

def main():
    if not (WEBHOOK and OWM_KEY):
        sys.exit("시크릿 DISCORD_WEBHOOK_UMBRELLA 또는 OWM_API_KEY 가 없습니다")

    rain_slots = find_rain_windows(fetch_forecast())
    if not rain_slots:
        print("☀️ 우산 불필요 – 메시지 전송 안 함")
        return

    msg = f"☂️ 오늘 서울에 비 소식!\n{fmt(rain_slots)} 사이에 우산을 챙기세요."
    requests.post(WEBHOOK, json={"content": msg}, timeout=10)
    print("✅ 우산 알림 전송 완료")

if __name__ == "__main__":
    main()
