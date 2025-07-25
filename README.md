# 📢 SSU-Notifier Bots

**SSU-Notifier Bots**는 숭실대학교 주요 사이트(학사, 소프트웨어학부, 기계공학부, 신소재공학과)와
기상청·OpenWeatherMap 정보를 주기적으로 확인하여  
새로운 글이나 우산이 필요한 날씨가 감지되면 **디스코드 채널**로 자동 전송해 주는
GitHub Actions 기반 서버리스 봇 모음 레포입니다.

<div align="center">
  
| Bot | Target | Schedule (KST) | Channel |
|-----|--------|----------------|---------|
| `notice_bot` | 학사공지 (scatch.ssu.ac.kr) | 매시 정각 | 📚 school-notice |
| `sw_bot` | 소프트웨어학부 공지 | 매시 정각 | 💻 sw-notice |
| `me_bot` | 기계공학부 공지 | 07 – 23시 매시 | 🔧 me-notice |
| `materials_bot` | 신소재공학과 공지 | 07 – 23시 매시 | 🔬 mse-notice |
| `weather_bot` | 서울 24 h 강수 예보 | 매일 07 시 | ☔ umbrella |
  
</div>

---

## ✨ 특징

* **Serverless** – GitHub Actions에서 실행 → 별도 서버·Raspberry Pi 필요 없음  
* **중복 알림 방지** – 글 ID를 파일로 저장·커밋하여 이미 전송한 공지는 스킵  
* **고정 공지 무시** – “공지” 아이콘/텍스트를 자동 필터링  
* **다중 인코딩 지원** – UTF-8, EUC-KR(CP949) 페이지를 자동 판별  
* **쉬운 확장** – `*_bot.py` + 워크플로 yml 하나면 새 사이트를 바로 추가 가능

---

## 🏃‍♂️ 빠른 시작

1. **레포 Fork → Clone**  
2. 디스코드 채널마다 웹훅 생성 후  
   `Settings → Secrets and variables → Actions` 에 아래 시크릿 추가  
   ```text
   DISCORD_WEBHOOK_NOTICE        # 학사
   DISCORD_WEBHOOK_SW            # 소프트
   DISCORD_WEBHOOK_ME            # 기계
   DISCORD_WEBHOOK_MSE           # 신소재
   DISCORD_WEBHOOK_UMBRELLA      # 우산 알림
   OWM_API_KEY                   # OpenWeatherMap 키
