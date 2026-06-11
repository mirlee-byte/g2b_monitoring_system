# 🏛️ 나라장터 입찰 모니터링 시스템

올림플래닛(VR/AR/XR/메타버스 전문기업)을 위한 나라장터 입찰공고 자동 모니터링 시스템입니다.

매일 오전 9시 30분에 자동 실행되어 관련 입찰공고를 수집하고, Claude AI로 적격 여부를 판단한 뒤 Google Chat으로 알림을 전송합니다.

---

## ⚙️ 시스템 흐름

```
나라장터 Open API
       ↓ 키워드 검색 (13개)
  입찰공고 수집
       ↓ 중복 제거
  Claude AI 분석 (0~10점)
       ↓ 4점 이상
  Google Chat 알림
```

---

## 📁 파일 구조

```
g2b_monitor/
├── main.py          # 메인 실행 (스케줄러 / 즉시실행 / 테스트)
├── crawler.py       # 나라장터 Open API 크롤러
├── analyzer.py      # Claude AI 적격 판단
├── notifier.py      # Google Chat Webhook 알림
├── config.py        # 설정 (키워드, 회사 프로필, 모델 등)
├── requirements.txt # 필요 패키지
├── test_api.py      # 나라장터 API 연결 테스트
├── .env             # API 키 모음 (직접 생성 필요, git 제외)
└── .gitignore
```

---

## 🚀 설치 및 실행

### 1. 패키지 설치

```bash
pip3 install -r requirements.txt
```

### 2. .env 파일 생성

프로젝트 루트에 `.env` 파일을 직접 만들고 아래 내용을 입력합니다.

```
ANTHROPIC_API_KEY=sk-ant-여기에_Anthropic_API_키
G2B_API_KEY=여기에_공공데이터포털_디코딩키
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/...
```

### 3. API 키 연결 테스트

```bash
python3 test_api.py       # 나라장터 API 테스트
python3 main.py --test    # Google Chat Webhook 테스트
```

### 4. 실행

```bash
python3 main.py --now    # 즉시 1회 실행
python3 main.py          # 스케줄러 시작 (매일 09:30 자동 실행)
```

---

## 🔑 API 키 발급

| 키 | 발급 방법 |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys → Create Key |
| `G2B_API_KEY` | https://www.data.go.kr → "나라장터 입찰공고정보" 검색 → 활용신청 → **디코딩키** 사용 |
| `GOOGLE_CHAT_WEBHOOK_URL` | Google Chat 스페이스 → 앱 및 통합 → Webhook 추가 |

---

## 🔍 검색 키워드 (13개)

`config.py`에서 수정 가능합니다.

```
VR, XR, AR, 실감형, 메타버스, 확장현실, 가상현실,
혼합현실, 디지털트윈, 실감미디어, 몰입형, 3D콘텐츠, 디지털콘텐츠
```

---

## 📊 적격 판단 기준

Claude AI가 0~10점으로 점수를 매기며, **4점 이상**이면 Google Chat으로 알림이 옵니다.

높은 점수를 받는 공고 조건:
- 공고명에 VR/AR/XR/메타버스/실감형 등 키워드 포함
- 업종이 소프트웨어사업자, 디지털콘텐츠개발서비스에 해당
- 용역 형태 (콘텐츠 개발, 플랫폼 구축 등)

---

## 📅 검색 기간

매일 실행 시 **어제 09:30 ~ 오늘 09:29** 구간의 공고를 수집합니다.
