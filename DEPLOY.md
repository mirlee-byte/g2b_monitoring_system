# 배포 가이드

배포 방식은 두 가지다. **A. 기존 서버에 Docker 컨테이너로 배포**(공유 인스턴스 권장) 또는
**B. 전용 EC2에 cron으로 배포**. 회사 공유 서버라면 A를 권장한다 — 호스트의 파이썬 환경과
crontab을 건드리지 않고 격리되기 때문이다.

---

# A. Docker 컨테이너 배포 (기존 인스턴스)

`main.py` 내장 스케줄러를 이용해 컨테이너를 상시 띄워두고, 컨테이너가 매일 10:00(KST)에
스스로 `run_monitoring`을 실행한다. 호스트 crontab 수정이 필요 없다.

## 준비

- 대상 인스턴스에 Docker(+ Compose plugin)가 설치돼 있어야 한다: `docker --version`, `docker compose version`.
- 코드를 인스턴스로 가져온다: `git clone https://github.com/mirlee-byte/g2b_monitoring_system.git ~/g2b_monitor && cd ~/g2b_monitor`.
- `.env`를 인스턴스에 직접 생성(또는 scp). **`.env`와 `service_account.json`은 `.dockerignore`로 이미지에서 제외**되며, 런타임에 `env_file`로만 주입된다 — 절대 이미지에 굽지 않는다.

## 실행 (Compose 권장)

```bash
cd ~/g2b_monitor
docker compose up -d --build      # 빌드 후 백그라운드 상시 실행
docker compose logs -f            # 로그 확인 (기동 시 Webhook 테스트 메시지 1건 전송됨)
```

컨테이너는 `restart: unless-stopped`라 호스트 재부팅 후에도 자동 기동된다. 타임존은
이미지에 `Asia/Seoul`로 고정돼 있어 스케줄러의 "10:00"이 한국 시각이다.

## 즉시 1회 테스트 / 중지

```bash
docker compose run --rm g2b-monitor python main.py --now    # 지금 1회 실행
docker compose down                                          # 중지·제거
```

## Compose 없이 docker CLI만 쓸 때

```bash
docker build -t g2b-monitor .
docker run -d --name g2b-monitor --restart unless-stopped \
  --env-file .env -e TZ=Asia/Seoul \
  --log-opt max-size=10m --log-opt max-file=3 \
  g2b-monitor
```

## 코드 업데이트 반영

```bash
git pull && docker compose up -d --build
```

> 참고: 스케줄러 모드는 기동 시 Google Chat에 "시스템 테스트" 메시지를 1건 보낸다.
> 컨테이너가 재시작될 때마다 이 메시지가 오는 게 거슬리면 [main.py](main.py)의
> `main()`에서 `test_webhook()` 호출을 제거하면 된다.

---

# B. 전용 EC2 배포 (cron 예약 실행)

하루 1회(매일 10:00 KST) 실행되는 작업이므로 상시 서버 프로세스 대신 cron으로 운영한다.

## 1. EC2 인스턴스 준비

- 타입: `t3.micro`(프리티어 가능)면 충분. DB를 두지 않으므로 추가 스토리지 불필요.
- OS: Ubuntu 22.04 LTS 권장.
- 보안그룹: 인바운드는 본인 IP에서의 SSH(22)만 허용. 아웃바운드는 전체 허용
  (나라장터 API·Anthropic API·Google Chat API 호출에 필요).
- **타임존**: 인스턴스 기본은 UTF다. 한국 10:00에 돌리려면 아래 둘 중 하나.
  - 인스턴스 타임존을 KST로: `sudo timedatectl set-timezone Asia/Seoul`
  - 또는 UTC 기준 cron에 `0 1 * * *` (10:00 KST = 01:00 UTC) 사용.

## 2. 코드 배포 & 환경 구성

```bash
sudo apt update && sudo apt install -y python3-venv git
git clone <레포지토리 URL> ~/g2b_monitor
cd ~/g2b_monitor
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

`.env` 파일을 EC2에 직접 생성한다(레포에 포함하지 말 것):

```
ANTHROPIC_API_KEY=...
G2B_API_KEY=...
GOOGLE_CHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/...
# 파일 첨부(Chat API)용 — 3절 참고
GOOGLE_SA_KEY_FILE=/home/ubuntu/g2b_monitor/service_account.json
GOOGLE_CHAT_SPACE=spaces/AAAAxxxxxxx
GOOGLE_CHAT_IMPERSONATE_USER=someone@olimplanet.com
```

서비스 계정 키 파일(`service_account.json`)은 SCP 등으로 안전하게 올린다.
권한은 `chmod 600 service_account.json`. 절대 git에 커밋하지 않는다(.gitignore에 이미 포함).

## 3. Google Chat 파일 업로드 설정 (관리자 작업)

파일 첨부는 Webhook으로 불가능하므로 Chat API + 도메인 전체 위임이 필요하다.
media.upload는 사용자 인증을 요구하므로(확인 필요), 서비스 계정이 실제 Workspace
사용자를 대행하는 구조다. 메시지는 봇이 아니라 그 사용자 명의로 전송된다.

1. **GCP 프로젝트**: Google Cloud Console에서 프로젝트 생성 → **Google Chat API** 활성화.
2. **서비스 계정**: 서비스 계정 생성 → JSON 키 발급(EC2에 올릴 파일) →
   "도메인 전체 위임 사용 설정". 발급된 서비스 계정의 **클라이언트 ID(숫자)**를 기록.
3. **위임 등록**: Workspace 관리 콘솔 → 보안 → API 제어 → **도메인 전체 위임** →
   위 클라이언트 ID 추가, 범위에 `https://www.googleapis.com/auth/chat.messages.create` 등록.
4. **대행 사용자**: 메시지를 보낼 명의가 될 Workspace 사용자 1명을 정하고
   (예: 본인 계정 또는 전용 서비스 메일박스), 그 사용자를 **대상 Chat 스페이스의 멤버**로 추가.
5. **스페이스 ID 확보**: 대상 스페이스에서 리소스명 `spaces/XXXXXXX`를 확인
   (스페이스 URL 끝부분 또는 Chat API spaces.list 호출).
6. `.env`에 `GOOGLE_SA_KEY_FILE`(키 파일 경로), `GOOGLE_CHAT_SPACE`(spaces/...),
   `GOOGLE_CHAT_IMPERSONATE_USER`(대행 사용자 이메일) 입력.

> 관리자 권한이 없으면 이 방식은 불가하며, 그 경우 메시지에 나라장터 다운로드 링크만
> 넣는 Webhook 방식으로 대체해야 한다.

## 4. 동작 확인

```bash
cd ~/g2b_monitor && . .venv/bin/activate
python main.py --test    # Google Chat Webhook 연결 확인
python main.py --now     # 즉시 1회 실행 (실제 수집·분석·전송)
```

## 5. cron 등록

```bash
crontab -e
```

KST 타임존으로 맞춘 경우:

```
0 10 * * * cd /home/ubuntu/g2b_monitor && /home/ubuntu/g2b_monitor/.venv/bin/python main.py --now >> /home/ubuntu/g2b_monitor/cron.log 2>&1
```

UTC 인스턴스라면 `0 1 * * *`(10:00 KST)로 변경.

> `main.py` 인자 없이 실행하면 내부 `schedule` 무한루프가 돌지만,
> cron 방식에서는 `--now`로 1회만 실행하므로 무한루프는 사용하지 않는다.

## 6. 운영 메모

- 로그: `g2b_monitor.log`(앱 로그) + `cron.log`(cron 표준출력). 주기적으로 로테이션 권장.
- 다운로드 파일은 `downloads/<공고번호>/`에 쌓이므로 디스크 정리 cron을 따로 두거나
  전송 후 삭제하도록 보완 가능(현재는 보존).
- DB는 두지 않으므로 "이미 알림 보낸 공고" 중복 알림 방지는 검색 윈도우(24시간)로만 보장된다.
