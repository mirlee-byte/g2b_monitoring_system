# ⚙️ 시스템 엔진 파일 — 설정(키워드·점수·회사정보)은 config.py 에서 바꾸세요. 이 파일은 수정하지 않아도 됩니다.
"""
Google Chat Webhook으로 알림을 전송하는 모듈
"""

import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def send_google_chat_message(webhook_url: str, message: str) -> bool:
    """Google Chat으로 텍스트 메시지 전송"""
    try:
        response = requests.post(
            webhook_url,
            json={"text": message},
            timeout=10
        )
        response.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Google Chat 전송 실패: {e}")
        return False


def _trim_dt(value: str) -> str:
    """'2026-07-07 10:00:00' → '2026-07-07 10:00' (초 단위 절삭)"""
    value = (value or "").strip()
    if len(value) >= 16 and value[10] == " ":
        return value[:16]
    return value or "확인 필요"


def _region_text(flag: str) -> str:
    """지역제한 코드(Y/N)를 사람이 읽는 문구로"""
    flag = (flag or "").strip().upper()
    if flag == "Y":
        return "있음"
    if flag == "N":
        return "없음"
    return flag or "확인 필요"


def format_bid_message(bid_info: dict, analysis: dict) -> str:
    """입찰 공고 알림 메시지 포맷 (간결·전문 톤)"""
    score = analysis.get("score", 0)

    # 적격도 구간 (상태 표시는 단일 색상 점으로 최소화)
    if score >= 8:
        marker, verdict = "🟢", "강력 추천"
    elif score >= 6:
        marker, verdict = "🟢", "참여 권장"
    elif score >= 4:
        marker, verdict = "🟡", "검토 권장"
    else:
        marker, verdict = "🔴", "참여 어려움"

    def bullets(items, n):
        items = [str(x).strip() for x in (items or []) if str(x).strip()][:n]
        return "\n".join(f"• {x}" for x in items) if items else "• 해당 없음"

    key_points_str = bullets(analysis.get("key_points"), 3)
    concerns_str = bullets(analysis.get("concerns"), 2)

    files = bid_info.get("files", [])
    if files:
        def file_line(f):
            name = (f.get("name") or "첨부파일").strip()
            url = (f.get("url") or "").strip()
            size = f"  ({f.get('size')})" if f.get("size") else ""
            # Google Chat 링크 문법: <URL|표시문구>
            return f"• <{url}|{name}>{size}" if url else f"• {name}{size}"
        file_lines = "\n".join(file_line(f) for f in files[:10])
        files_header = f"*첨부파일 ({len(files)}건)*  · 클릭하면 다운로드"
    else:
        file_lines = "• 없음"
        files_header = "*첨부파일*"

    # 예산: 추정가격 + 배정예산을 한 줄로
    estimated = bid_info.get("estimated_price") or "미공개"
    budget = bid_info.get("budget") or "미공개"
    contract = bid_info.get("contract_method", "")
    award = bid_info.get("award_method", "")
    contract_line = " · ".join([v for v in (contract, award) if v]) or "확인 필요"

    link = bid_info.get("detail_url") or "https://www.g2b.go.kr/"

    message = f"""
{marker} *적격 검토: {verdict}*  ·  적격도 {score}/10

*{bid_info.get('title', '')}*

*공고기관*  {bid_info.get('org', '')}
*공고번호*  {bid_info.get('bid_no', '')}
*입찰마감*  {_trim_dt(bid_info.get('bid_deadline', ''))}
*추정가격*  {estimated}  (배정예산 {budget})
*계약방법*  {contract_line}
*지역제한*  {_region_text(bid_info.get('region_limit', ''))}
*매칭키워드*  {bid_info.get('keyword', '')}

*검토 의견*
{analysis.get('reason', '')}

*참여 강점*
{key_points_str}

*유의 사항*
{concerns_str}

*권고*
{analysis.get('recommendation', '')}

{files_header}
{file_lines}

나라장터 공고 보기: {link}
""".strip()

    return message


def send_summary_message(webhook_url: str, results: list[dict], run_time: str) -> bool:
    """일일 요약 메시지 전송"""
    total = len(results)
    eligible_count = sum(1 for r in results if r.get("analysis", {}).get("eligible", False))
    high_score = [r for r in results if r.get("analysis", {}).get("score", 0) >= 6]

    if total == 0:
        message = f"""
*나라장터 일일 입찰 리포트*  ·  {run_time}

오늘 수집 구간에서 관련 입찰 공고가 확인되지 않았습니다.
""".strip()
    else:
        high_score_titles = "\n".join(
            f"{i+1}. {r.get('title', '')[:45]} ({r.get('analysis', {}).get('score', 0)}/10)"
            for i, r in enumerate(high_score[:5])
        )

        message = f"""
*나라장터 일일 입찰 리포트*  ·  {run_time}

*수집 요약*
• 전체 공고  {total}건
• 참여 적합  {eligible_count}건
• 적격도 6 이상  {len(high_score)}건

*주요 공고*
{high_score_titles if high_score_titles else '• 해당 없음'}

세부 내용은 위 개별 알림을 확인해 주세요.
""".strip()

    return send_google_chat_message(webhook_url, message)


def send_error_message(webhook_url: str, error: str) -> bool:
    """오류 알림 전송"""
    message = f"""
*나라장터 모니터링 오류*  ·  {datetime.now().strftime('%Y-%m-%d %H:%M')}

{error}

시스템 점검이 필요합니다.
""".strip()
    return send_google_chat_message(webhook_url, message)
