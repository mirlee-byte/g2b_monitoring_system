# 🔍 나라장터 입찰 모니터링 시스템
> 올림플래닛 VR/XR/메타버스 관련 입찰 자동 탐색 → AI 적격 판단 → Google Chat 알림

---

## 📁 파일 구조

```
g2b_monitor/
├── main.py                      # 메인 실행 파일
├── config.py                    # 설정 (키워드, Webhook URL 등)
├── crawler.py                   # 나라장터 크롤러 (Selenium)
├── analyzer.py                  # Claude AI 적격 판단
├── notifier.py                  # Google Chat 알림
├── requirements.txt             # 패키지 목록
├── setup_scheduler_windows.bat  # Windows 자동 실행 등록
└── downloads/                   # 첨부파일 저장 폴더 (자동 생성)
```

---

## 🚀 설치 방법

### 1. Python 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. Chrome & ChromeDriver 설치
- Chrome 브라우저 설치: https://www.google.com/chrome/
- ChromeDriver: 자동 관리됨 (selenium 4.x 이상)

### 3. Anthropic API 키 설정
```bash
# Windows
set ANTHROPIC_API_KEY=your_api_key_here

# Mac/Linux
export ANTHROPIC_API_KEY=your_api_key_here
```

또는 `.env` 파일 생성:
```
ANTHROPIC_API_KEY=your_api_key_here
```

---

## ▶️ 실행 방법

### 즉시 1회 실행 (테스트)
```bash
python main.py --now
```

### Webhook 연결 테스트만
```bash
python main.py --test
```

### 스케줄러 시작 (매일 09:30 자동 실행)
```bash
python main.py
```

### Windows 작업 스케줄러에 등록 (자동 시작)
`setup_scheduler_windows.bat` 을 **관리자 권한**으로 실행

---

## ⚙️ 설정 변경 (`config.py`)

| 항목 | 기본값 | 설명 |
|------|--------|------|
| `SEARCH_KEYWORDS` | VR, XR, AR, 실감형 등 | 검색할 키워드 목록 |
| `RUN_TIME` | `"09:30"` | 매일 실행 시간 |
| `MIN_SCORE_TO_NOTIFY` | `4` | 알림 발송 최소 점수 (0~10) |
| `MAX_BIDS_PER_RUN` | `20` | 1회 최대 분석 공고 수 |

---

## 📱 Google Chat 알림 예시

```
🔔 [나라장터 입찰 알림] 2026-06-08 09:30

🟢 적격 판단: 강력 추천 (점수: 8/10)

━━━━━━━━━━━━━━━━━━━━━━
📋 공고명: 씨큐리움 실감형 전시 콘텐츠 제작 설치
🏢 공고기관: 국립해양생물자원관
🔑 매칭 키워드: 실감형
💰 추정가격: 909,090,909원

🤖 AI 분석 결과

📝 판단 근거:
  실감형 전시 콘텐츠 제작이 핵심 사업으로, 올림플래닛의
  VR/XR 콘텐츠 개발 역량과 정확히 일치합니다.

✨ 긍정적 요소:
  ✅ 디지털콘텐츠개발서비스 업종 등록 완료
  ✅ NET 신기술인증 보유로 기술력 증명 가능
  ✅ 예산 규모가 참여 가능 범위 내
```

---

## 🛠 문제 해결

**Q: Chrome 드라이버 오류 발생**
```bash
pip install --upgrade selenium webdriver-manager
```

**Q: 나라장터 팝업이 계속 뜸**
- `crawler.py`의 `close_all_popups()` 함수에서 팝업 selector 추가

**Q: AI 분석이 안 됨**
- `ANTHROPIC_API_KEY` 환경변수 확인
- Anthropic 계정 크레딧 확인

---

## 📞 로그 확인
```bash
tail -f g2b_monitor.log
```
