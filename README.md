# 📢 SSU-Notifier Bots

**SSU-Notifier Bots** 는 숭실대학교 학사·학과 공지와 날씨(우산 알림)를
GitHub Actions 위에서 **서버리스**로 실행해  
새로운 글·비 예보가 생기면 지정한 **디스코드 채널**에 자동 전송해 주는 봇 모음 레포입니다.

<div align="center">
  
| Bot 파일 | 대상 사이트 | 실행 주기 (KST) | Discord 채널 |
|----------|-------------|-----------------|--------------|
| `notice_bot.py` | 학사공지 (scatch.ssu.ac.kr) | 매 시 정각 | 📚 school-notice |
| `sw_bot.py` | 소프트웨어학부 | 매 시 정각 | 💻 sw-notice |
| `me_bot.py` | 기계공학부 (Worker 프록시) | 07 – 23시 매 시 | 🔧 me-notice |
| `materials_bot.py` | 신소재공학과 | 07 – 23시 매 시 | 🔬 mse-notice |
| `chemeng_bot.py` | 화학공학과 | 07 – 23시 매 시 | ⚗️ chemeng-notice |
| `ee_bot.py` | 전기공학부 | 07 – 23시 매 시 | ⚡ ee-notice |
| `kma_weather_bot.py` | 기상청 동네예보<br>(서울 종로구) | 매일 06:40 | ☔ umbrella |
  
</div>

---

## ✨ 특징

* **Serverless** – GitHub Actions에서 실행 → 별도 서버·Raspberry Pi 필요 없음  
* **중복 알림 방지** – 글 ID를 파일로 저장·커밋하여 이미 전송한 공지는 스킵  
* **고정 공지 무시** – “공지” 아이콘/텍스트를 자동 필터링  
* **다중 인코딩 지원** – UTF-8, EUC-KR(CP949) 페이지를 자동 판별
* **날씨 조건 설정** – 강수확률 ≥ 60 % & 강수량 ≥ 1 mm 구간만 우산 알림    
* **쉬운 확장** – `*_bot.py` + 워크플로 yml 하나면 새 사이트를 바로 추가 가능

---

## 🏃‍♂️ 빠른 시작

1. **레포 Fork → Clone**  
2. 디스코드 채널마다 웹훅 생성 후  
   `Settings → Secrets and variables → Actions` 에 아래 시크릿 추가  
   | Secret 이름 | 값 |
   |-------------|----|
   | `DISCORD_WEBHOOK_NOTICE` | 학사 |
   | `DISCORD_WEBHOOK_SW` | 소프트 |
   | `DISCORD_WEBHOOK_ME` | 기계 |
   | `DISCORD_WEBHOOK_MSE` | 신소재 |
   | `DISCORD_WEBHOOK_CHEMENG` | 화공 |
   | `DISCORD_WEBHOOK_EE` | 전기 |
   | `DISCORD_WEBHOOK_UMBRELLA` | 우산 |
   | `KMA_API_KEY` | 기상청 Encoding 키 |
