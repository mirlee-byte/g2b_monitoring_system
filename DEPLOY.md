# AWS EC2 배포 가이드 (cron 예약 실행)

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
