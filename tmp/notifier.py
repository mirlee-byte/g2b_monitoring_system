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


def format_bid_message(bid_info: dict, analysis: dict) -> str:
    """입찰 공고 알림 메시지 포맷"""
    score = analysis.get("score", 0)
    eligible = analysis.get("eligible", False)

    # 점수에 따른 이모지
    if score >= 8:
        score_emoji = "🟢"
        verdict = "강력 추천"
    elif score >= 6:
        score_emoji = "🟡"
        verdict = "참여 권장"
    elif score >= 4:
        score_emoji = "🟠"
        verdict = "검토 필요"
    else:
        score_emoji = "🔴"
        verdict = "참여 어려움"

    # 핵심 포인트
    key_points = analysis.get("key_points", [])
    key_points_str = "\n".join([f"  ✅ {p}" for p in key_points[:3]]) if key_points else "  없음"

    # 우려 사항
    concerns = analysis.get("concerns", [])
    concerns_str = "\n".join([f"  ⚠️ {c}" for c in concerns[:2]]) if concerns else "  없음"

    # 파일 목록
    files = bid_info.get("files", [])
    files_str = "\n".join([f"  📎 {f.get('name', '')} ({f.get('size', '')})" for f in files[:5]])
    if not files_str:
        files_str = "  없음"

    message = f"""
🔔 *[나라장터 입찰 알림]* {datetime.now().strftime('%Y-%m-%d %H:%M')}

{score_emoji} *적격 판단: {verdict}* (점수: {score}/10)

━━━━━━━━━━━━━━━━━━━━━━
📋 *공고명*: {bid_info.get('title', '')}
🏢 *공고기관*: {bid_info.get('org', '')}
🔢 *공고번호*: {bid_info.get('bid_no', '')}
🔑 *매칭 키워드*: {bid_info.get('keyword', '')}
📅 *게시/마감*: {bid_info.get('date', '')}
⏰ *입찰 마감*: {bid_info.get('bid_deadline', '확인 필요')}

💰 *예산 정보*
  • 추정가격: {bid_info.get('estimated_price', '미공개')}
  • 배정예산: {bid_info.get('budget', '미공개')}

📌 *계약 정보*
  • 계약방법: {bid_info.get('contract_method', '')}
  • 낙찰방법: {bid_info.get('award_method', '')}
  • 지역제한: {bid_info.get('region_limit', '없음')}

━━━━━━━━━━━━━━━━━━━━━━
🤖 *AI 분석 결과*

📝 *판단 근거*:
  {analysis.get('reason', '')}

✨ *긍정적 요소*:
{key_points_str}

⚠️ *주의 사항*:
{concerns_str}

💡 *권고 사항*:
  {analysis.get('recommendation', '')}

━━━━━━━━━━━━━━━━━━━━━━
📁 *첨부파일*:
{files_str}

🔗 나라장터: https://www.g2b.go.kr/
""".strip()

    return message


def send_summary_message(webhook_url: str, results: list[dict], run_time: str) -> bool:
    """일일 요약 메시지 전송"""
    total = len(results)
    eligible_count = sum(1 for r in results if r.get("analysis", {}).get("eligible", False))
    high_score = [r for r in results if r.get("analysis", {}).get("score", 0) >= 6]

    if total == 0:
        message = f"""
📊 *[나라장터 일일 입찰 리포트]* {run_time}

오늘은 관련 입찰 공고가 발견되지 않았습니다.
다음 실행 시간까지 대기합니다.
""".strip()
    else:
        high_score_titles = "\n".join([
            f"  {i+1}. {r.get('title', '')[:40]}... (점수: {r.get('analysis', {}).get('score', 0)}/10)"
            for i, r in enumerate(high_score[:5])
        ])

        message = f"""
📊 *[나라장터 일일 입찰 리포트]* {run_time}

📈 *오늘의 검색 결과 요약*
  • 전체 발견 공고: {total}건
  • 참여 적합 공고: {eligible_count}건
  • 높은 점수(6점↑): {len(high_score)}건

🏆 *주요 추천 공고*:
{high_score_titles if high_score_titles else '  없음'}

상세 정보는 위의 개별 알림을 확인해주세요.
""".strip()

    return send_google_chat_message(webhook_url, message)


def send_error_message(webhook_url: str, error: str) -> bool:
    """오류 알림 전송"""
    message = f"""
⚠️ *[나라장터 모니터링 오류]* {datetime.now().strftime('%Y-%m-%d %H:%M')}

오류 내용: {error}

시스템을 확인해주세요.
""".strip()
    return send_google_chat_message(webhook_url, message)
