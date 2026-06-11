# 나라장터 입찰 모니터링 시스템

올림플래닛을 위한 나라장터 입찰공고 자동 모니터링 시스템

## 파일 구조

```
g2b_monitor/
├── main.py          # 메인 실행 스크립트
├── crawler.py       # 나라장터 Open API 크롤러
├── analyzer.py      # Claude AI 적격 판단
├── notifier.py      # Google Chat 알림
├── config.py        # 설정 (키워드, 회사 프로필 등)
├── requirements.txt # 패키지 목록
├── test_api.py      # API 연결 테스트
└── .env             # API 키 (직접 생성 필요)
```

## 설치

```bash
pip3 install -r requirements.txt
```

## .env 파일 설정

```
ANTHROPIC_API_KEY=sk-ant-...
G2B_API_KEY=공공데이터포털_디코딩키
```

## 실행

```bash
python3 main.py --test   # Webhook 연결 테스트
python3 main.py --now    # 즉시 1회 실행
python3 main.py          # 스케줄러 시작 (매일 09:30 자동 실행)
python3 test_api.py      # 나라장터 API 연결 테스트
```

## API 발급

- **Anthropic API**: https://console.anthropic.com
- **나라장터 API**: https://www.data.go.kr → "나라장터 입찰공고정보" 검색 → 활용신청 → 디코딩키 사용
