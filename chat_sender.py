"""
Google Chat API로 메시지 + 첨부파일을 스페이스에 전송하는 모듈.

Webhook은 텍스트/카드만 가능하고 파일 업로드를 지원하지 않으므로,
파일을 채팅에 올리려면 Chat API를 사용해야 한다.

전제 (Google Workspace 관리자 설정 필요):
  1) Google Cloud 프로젝트에서 Google Chat API 활성화
  2) 서비스 계정 생성 + 키(JSON) 발급 + 도메인 전체 위임 사용 설정
  3) Workspace 관리 콘솔에서 해당 서비스 계정 클라이언트 ID에 위임 범위 등록
     - 위임 범위(scope): https://www.googleapis.com/auth/chat.messages.create
  4) 대행할 Workspace 사용자(GOOGLE_CHAT_IMPERSONATE_USER)를 대상 스페이스 멤버로 추가
  5) .env에 GOOGLE_SA_KEY_FILE / GOOGLE_CHAT_SPACE / GOOGLE_CHAT_IMPERSONATE_USER 설정

파일 업로드(media.upload)는 사용자 인증을 요구하므로, 서비스 계정이
GOOGLE_CHAT_IMPERSONATE_USER 사용자를 대행(impersonate)하여 호출한다.
메시지는 봇이 아니라 그 사용자 명의로 전송되므로, 봇 추가가 아니라
"대행 사용자가 스페이스 멤버"인 것이 전제다.
"""

import os
import mimetypes
import logging

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/chat.messages.create"]

_chat_service = None


def _get_service(sa_key_file: str, impersonate_user: str):
    """Chat API 서비스 객체를 (lazy) 생성/캐시"""
    global _chat_service
    if _chat_service is not None:
        return _chat_service

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    if not os.path.exists(sa_key_file):
        raise FileNotFoundError(f"서비스 계정 키 파일 없음: {sa_key_file}")

    creds = service_account.Credentials.from_service_account_file(
        sa_key_file, scopes=SCOPES, subject=impersonate_user
    )
    _chat_service = build("chat", "v1", credentials=creds, cache_discovery=False)
    return _chat_service


def send_message_with_files(
    space: str,
    text: str,
    file_paths: list,
    sa_key_file: str,
    impersonate_user: str,
) -> bool:
    """
    스페이스에 텍스트 + 첨부파일을 전송.
    Chat API의 메시지당 첨부 개수 제한(확인 필요)이 있으므로 여러 파일은 분할 전송한다.
    file_paths가 비어 있으면 텍스트만 전송.
    """
    from googleapiclient.http import MediaFileUpload

    if not space:
        logger.error("GOOGLE_CHAT_SPACE 미설정 — 파일 전송 불가")
        return False

    try:
        service = _get_service(sa_key_file, impersonate_user)
    except Exception as e:
        logger.error(f"Chat API 초기화 실패: {e}")
        return False

    # 첨부파일을 media.upload로 올려 attachmentDataRef를 수집
    attachments = []
    for path in file_paths:
        if not path or not os.path.exists(path):
            continue
        try:
            mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
            media = MediaFileUpload(path, mimetype=mime, resumable=False)
            uploaded = service.media().upload(
                parent=space,
                body={"filename": os.path.basename(path)},
                media_body=media,
            ).execute()
            ref = uploaded.get("attachmentDataRef")
            if ref:
                attachments.append({"attachmentDataRef": ref})
        except Exception as e:
            logger.error(f"파일 업로드 실패 [{path}]: {e}")

    try:
        # Chat API는 메시지당 첨부 1건만 허용될 수 있어(확인 필요),
        # 첫 메시지에 텍스트 + 첫 첨부, 나머지 첨부는 후속 메시지로 전송한다.
        if not attachments:
            service.spaces().messages().create(
                parent=space, body={"text": text}
            ).execute()
            return True

        first = attachments[0]
        service.spaces().messages().create(
            parent=space, body={"text": text, "attachment": [first]}
        ).execute()

        for att in attachments[1:]:
            service.spaces().messages().create(
                parent=space, body={"attachment": [att]}
            ).execute()

        return True
    except Exception as e:
        logger.error(f"Chat 메시지 전송 실패: {e}")
        return False
