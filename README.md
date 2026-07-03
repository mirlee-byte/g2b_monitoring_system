# 나라장터 입찰 모니터링 시스템

올림플래닛(VR/AR/XR/메타버스 전문기업)을 위한 나라장터 입찰공고 자동 모니터링 시스템입니다.
매일 정해진 시각에 관련 입찰공고를 수집하고, Claude AI로 적격 여부를 판단한 뒤 Google Chat으로 알림을 보냅니다.

---

## 시스템 흐름

```
나라장터 Open API
      ↓  키워드 검색 (병렬)
  입찰공고 수집 → 중복 제거
      ↓  Claude AI 분석 (0~10점, 병렬)
  기준 점수 이상 공고
      ↓
  Google Chat 알림 + 일일 요약
```

---

## 파일 구조

```
g2b_monitor/
├── config.py         ⭐ 담당자가 수정하는 설정 (키워드·점수·회사정보)
├── main.py           실행 진입점 (스케줄러 / 즉시실행 / 테스트)
├── requirements.txt  필요 패키지 목록
├── README.md         이 문서
├── .env              API 키 (직접 생성, git 제외)
└── src/              시스템 엔진 (수정 불필요)
    ├── crawler.py    · 나라장터 Open API 크롤러
    ├── analyzer.py   · Claude AI 적격 판단
    └── notifier.py   · Google Chat 알림
```

> 👤 담당자는 **`config.py` 하나만** 열면 됩니다. `src/` 폴더는 건드리지 않아도 됩니다.

---

## 설치 및 실행

### 1. 패키지 설치
```bash
pip install -r requirements.txt
```

### 2. .env 파일 생성
프로젝트 루트에 `.env` 파일을 만들고 아래 3개 값을 입력합니다.
```
ANTHROPIC_API_KEY=sk-ant-여기에_Anthropic_API_키
G2B_API_KEY=여기에_공공데이터포털_디코딩키
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/...
```

### 3. 실행
```bash
python main.py --test    # Google Chat 연결 테스트
python main.py --now     # 즉시 1회 실행
python main.py           # 스케줄러 시작 (매일 config.py의 RUN_TIME에 자동 실행)
```

---

## API 키 발급

| 키 | 발급처 |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys → Create Key |
| `G2B_API_KEY` | https://www.data.go.kr → "나라장터 입찰공고정보" 검색 → 활용신청 → **디코딩키** 사용 |
| `GOOGLE_CHAT_WEBHOOK_URL` | Google Chat 스페이스 → 앱 및 통합 → Webhook 추가 |

> `G2B_API_KEY`는 반드시 **디코딩(Decoding) 인증키**를 사용하세요. 인코딩키를 넣으면 인증 오류가 납니다.

---

## 설정 변경 안내 (담당자용)

모든 설정은 **`config.py`** 파일 하나에서 바꿉니다. 파일을 열면 번호가 매겨진 섹션과 설명(주석)이 있으니 그대로 따라 고치면 됩니다. 수정 후에는 프로그램을 다시 실행해야 반영됩니다.

| 바꾸고 싶은 것 | `config.py`에서 고칠 곳 |
|---|---|
| 검색 키워드 추가/삭제 | **1. 검색 키워드** — 줄 추가(끝에 쉼표), 또는 앞에 `#` 붙여 제외 |
| 알림 기준을 넓게/좁게 | **2.** `MIN_SCORE_TO_NOTIFY` (숫자 ↓ = 더 많이 알림) |
| 하루 분석 건수 상한 | **2.** `MAX_BIDS_PER_RUN` |
| 실행 시각 변경 | **3.** `RUN_TIME` (예: `"09:00"`) |
| 회사 업종·인증·실적 최신화 | **4.** `COMPANY_PROFILE` |

**편집 규칙**: ① 따옴표 `""` 와 쉼표 `,` 는 그대로 두고 글자만 바꾼다 ② 맨 앞에 `#` 있는 줄은 지우지 않는다 ③ 숫자는 따옴표 없이, 글자는 따옴표 안에.

---

## 검색 기간

매일 실행 시 **어제 실행시각 ~ 오늘 실행 직전**(약 24시간) 구간에 올라온 공고를 수집합니다.
기본값은 `RUN_TIME = "10:00"` 기준 **어제 10:00 ~ 오늘 09:59**입니다.
