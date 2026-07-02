"""
나라장터 입찰 모니터링 메인 실행 스크립트
매일 10:00에 자동 실행되며, 수동 실행도 가능합니다.

사용법:
  python main.py            # 스케줄러 시작 (백그라운드 실행)
  python main.py --now      # 즉시 1회 실행
  python main.py --test     # 테스트 모드 (Webhook만 테스트)
"""

import os
import sys
from dotenv import load_dotenv
load_dotenv()
import logging
import argparse
import schedule
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    GOOGLE_CHAT_WEBHOOK_URL, SEARCH_KEYWORDS, RUN_TIME,
    DOWNLOAD_DIR, COMPANY_PROFILE, CLAUDE_MODEL,
    MAX_BIDS_PER_RUN, MIN_SCORE_TO_NOTIFY, ANALYZE_MAX_WORKERS
)
from crawler import run_crawler
from analyzer import analyze_bid_eligibility
from notifier import (
    send_google_chat_message, format_bid_message,
    send_summary_message, send_error_message
)
# 첨부파일 실제 업로드(Chat API)는 chat_sender.py 참고 — 도메인 전체 위임 설정 후 사용

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("g2b_monitor.log", encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)


def run_monitoring():
    """메인 모니터링 실행 함수"""
    run_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    logger.info(f"=== 나라장터 모니터링 시작: {run_time} ===")

    results = []

    try:
        # 1단계: 크롤링
        logger.info("📡 나라장터 크롤링 시작...")
        bids = run_crawler(SEARCH_KEYWORDS, DOWNLOAD_DIR)

        if not bids:
            logger.info("검색된 공고가 없습니다.")
            send_summary_message(GOOGLE_CHAT_WEBHOOK_URL, [], run_time)
            return

        # 최대 처리 수 제한
        bids = bids[:MAX_BIDS_PER_RUN]
        logger.info(f"📋 분석할 공고 수: {len(bids)}건 (AI 분석 동시 {ANALYZE_MAX_WORKERS})")

        # 2단계: AI 분석 (병렬) — I/O 대기가 대부분이라 스레드 풀로 동시 처리
        def analyze_one(bid: dict) -> dict:
            try:
                analysis = analyze_bid_eligibility(bid, COMPANY_PROFILE, CLAUDE_MODEL)
                score = analysis.get("score", 0)
                verdict = "✅ 적격" if score >= MIN_SCORE_TO_NOTIFY else "❌ 부적격"
                logger.info(f"🤖 {verdict} (점수: {score}/10): {bid.get('title', '')[:30]}")
                return {**bid, "analysis": analysis}
            except Exception as e:
                logger.error(f"공고 분석 오류 [{bid.get('title', '')[:30]}]: {e}")
                return None

        with ThreadPoolExecutor(max_workers=ANALYZE_MAX_WORKERS) as executor:
            for result in executor.map(analyze_one, bids):
                if result:
                    results.append(result)

        # 3단계: 적격 공고 알림 전송 (점수 높은 순, 순차 전송)
        qualified = sorted(
            [r for r in results if r.get("analysis", {}).get("score", 0) >= MIN_SCORE_TO_NOTIFY],
            key=lambda r: r["analysis"].get("score", 0),
            reverse=True,
        )
        logger.info(f"🔔 적격 공고 {len(qualified)}건 알림 전송 중...")
        for r in qualified:
            message = format_bid_message(r, r["analysis"])
            send_google_chat_message(GOOGLE_CHAT_WEBHOOK_URL, message)

        # 4단계: 일일 요약 전송
        logger.info("📊 일일 요약 전송 중...")
        send_summary_message(GOOGLE_CHAT_WEBHOOK_URL, results, run_time)

    except Exception as e:
        logger.error(f"모니터링 오류: {e}")
        send_error_message(GOOGLE_CHAT_WEBHOOK_URL, str(e))

    logger.info(f"=== 모니터링 완료. 총 {len(results)}건 분석, "
                f"적격 {sum(1 for r in results if r.get('analysis', {}).get('eligible', False))}건 ===")


def test_webhook():
    """Webhook 연결 테스트"""
    logger.info("🧪 Webhook 테스트 중...")
    test_msg = f"""
🔧 *[나라장터 모니터링 시스템 테스트]* {datetime.now().strftime('%Y-%m-%d %H:%M')}

시스템이 정상적으로 설정되었습니다! ✅

설정 정보:
  • 검색 키워드: {len(SEARCH_KEYWORDS)}개
  • 실행 시간: 매일 {RUN_TIME}
  • 최소 적격 점수: {MIN_SCORE_TO_NOTIFY}/10
  • 최대 분석 공고수: {MAX_BIDS_PER_RUN}건
""".strip()

    success = send_google_chat_message(GOOGLE_CHAT_WEBHOOK_URL, test_msg)
    if success:
        logger.info("✅ Webhook 테스트 성공!")
    else:
        logger.error("❌ Webhook 테스트 실패!")
    return success


def main():
    parser = argparse.ArgumentParser(description="나라장터 입찰 모니터링")
    parser.add_argument("--now", action="store_true", help="즉시 1회 실행")
    parser.add_argument("--test", action="store_true", help="Webhook 테스트만 실행")
    args = parser.parse_args()

    if args.test:
        test_webhook()
        return

    if args.now:
        run_monitoring()
        return

    # 스케줄러 모드: 매일 RUN_TIME에 실행
    logger.info(f"🕐 스케줄러 시작: 매일 {RUN_TIME}에 실행됩니다.")
    logger.info("종료하려면 Ctrl+C를 누르세요.")

    schedule.every().day.at(RUN_TIME).do(run_monitoring)

    # 시작 시 테스트 메시지
    test_webhook()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
