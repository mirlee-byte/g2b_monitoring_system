# 나라장터 모니터링 - 컨테이너 이미지
# 매일 10:00(KST)에 main.py 내장 스케줄러가 자동 실행
FROM python:3.12-slim

# 타임존을 KST로 고정 (schedule의 "10:00"이 한국 시각이 되도록)
ENV TZ=Asia/Seoul
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 의존성 먼저 설치 (레이어 캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사 (.dockerignore로 .env·키·로그는 제외됨)
COPY . .

# 로그 버퍼링 비활성화 (docker logs에 즉시 출력)
ENV PYTHONUNBUFFERED=1

# 스케줄러 모드로 상시 실행 → 매일 10:00에 run_monitoring 수행
CMD ["python", "main.py"]
