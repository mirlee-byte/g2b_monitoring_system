"""
나라장터 입찰공고 크롤러 - 공공데이터포털 Open API 방식
Base URL: https://apis.data.go.kr/1230000/ad/BidPublicInfoService

핵심 파라미터 (문서 확인):
- inqryDiv: 1=등록일시, 2=입찰공고번호 (필수)
- inqryBgnDt / inqryEndDt: YYYYMMDDHHMM (inqryDiv=1 일때 필수)
- bidNtceNm: 입찰공고명 (옵션, 부분일치 검색)
- PPSSrch 엔드포인트: 공고명 검색 지원
"""

import os
import time
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

G2B_API_KEY = os.environ.get("G2B_API_KEY", "")
G2B_API_BASE = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"

def get_date_range():
    """
    검색 기간: 어제 09:30 ~ 오늘 09:29
    매일 09:30 실행 기준으로 정확히 24시간치 공고를 커버
    어제 09:30 이후 올라온 공고는 모두 포함됨
    """
    now = datetime.now()
    end   = now.replace(hour=9, minute=29, second=0, microsecond=0)
    start = (now - timedelta(days=1)).replace(hour=9, minute=30, second=0, microsecond=0)
    return start.strftime("%Y%m%d%H%M"), end.strftime("%Y%m%d%H%M")


def fetch_bids_by_keyword(keyword: str, num_rows: int = 100) -> list:
    """
    PPSSrch 엔드포인트로 공고명 키워드 검색
    용역/물품 두 가지 타입으로 검색
    """
    start_dt, end_dt = get_date_range()
    results = []

    endpoints = [
        ("용역", "getBidPblancListInfoServcPPSSrch"),
        ("물품", "getBidPblancListInfoThngPPSSrch"),
        ("기타", "getBidPblancListInfoEtcPPSSrch"),
    ]

    for bid_type, endpoint in endpoints:
        url = f"{G2B_API_BASE}/{endpoint}"
        params = {
            "ServiceKey": G2B_API_KEY,   # 대문자 S (문서 확인)
            "numOfRows": str(num_rows),
            "pageNo": "1",
            "inqryDiv": "1",             # 1=등록일시 기준
            "inqryBgnDt": start_dt,
            "inqryEndDt": end_dt,
            "bidNtceNm": keyword,
            "type": "json",
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            body = data.get("response", {}).get("body", {})
            total = body.get("totalCount", 0)
            items = body.get("items", [])

            if not items:
                logger.debug(f"[{keyword}/{bid_type}] 결과 없음")
                continue

            if isinstance(items, dict):
                items = [items]

            logger.info(f"[{keyword}/{bid_type}] {len(items)}건 / 전체 {total}건")

            for item in items:
                bid = parse_bid_item(item, keyword, bid_type)
                if bid:
                    results.append(bid)

        except Exception as e:
            logger.error(f"[{keyword}/{bid_type}] API 오류: {e}")

        time.sleep(0.3)

    return results


def parse_bid_item(item: dict, keyword: str, bid_type: str) -> dict:
    title = item.get("bidNtceNm", "").strip()
    if not title:
        return None

    if "취소" in item.get("ntceKindNm", "") or "취소" in title:
        return None

    bid_no = item.get("bidNtceNo", "")
    bid_seq = item.get("bidNtceOrd", "000")

    def fmt_price(val):
        if not val:
            return ""
        try:
            return f"{int(float(val)):,}원"
        except Exception:
            return str(val)

    estimated = fmt_price(item.get("presmptPrce", ""))
    budget = fmt_price(item.get("asignBdgtAmt", ""))

    org = item.get("ntceInsttNm", "")
    demand_org = item.get("dminsttNm", "")
    post_dt = item.get("bidNtceDt", "")
    close_dt = item.get("bidClseDt", "")
    contract_method = item.get("cntrctCnclsMthdNm", "")
    award_method = item.get("sucsfbidMthdNm", "")
    region_limit = item.get("cmmnSpldmdCorpRgnLmtYn", "")
    industry_limit = item.get("indstrytyLmtYn", "")

    # 첨부파일 목록 (ntceSpecFileNm1~10)
    files = []
    for i in range(1, 11):
        fname = item.get(f"ntceSpecFileNm{i}", "")
        furl = item.get(f"ntceSpecDocUrl{i}", "")
        if fname:
            files.append({"name": fname, "url": furl})

    detail_url = item.get("bidNtceUrl", "") or item.get("bidNtceDtlUrl", "")

    detail_text = (
        f"{title}\n"
        f"공고기관: {org}\n수요기관: {demand_org}\n"
        f"추정가격: {estimated}\n배정예산: {budget}\n"
        f"계약방법: {contract_method}\n낙찰방법: {award_method}\n"
        f"지역제한: {region_limit}\n업종제한여부: {industry_limit}\n"
        f"공고일: {post_dt}\n마감일: {close_dt}\n"
    )

    return {
        "title": title,
        "bid_no": f"{bid_no}-{bid_seq}",
        "org": org,
        "demand_org": demand_org,
        "date": f"{post_dt} ~ {close_dt}",
        "bid_deadline": close_dt,
        "contract_method": contract_method,
        "award_method": award_method,
        "estimated_price": estimated,
        "budget": budget,
        "region_limit": region_limit,
        "industry_limit": industry_limit,
        "bid_type": bid_type,
        "keyword": keyword,
        "detail_url": detail_url,
        "summary": f"추정가격: {estimated} | 낙찰: {award_method} | 마감: {close_dt}",
        "detail_text": detail_text,
        "files": files,
    }


def run_crawler(keywords: list, download_dir: str = "./downloads") -> list:
    if not G2B_API_KEY:
        logger.error("❌ G2B_API_KEY 미설정! .env에 G2B_API_KEY=디코딩키 추가 필요")
        return []

    all_bids = []
    seen = set()

    logger.info(f"나라장터 Open API 검색 시작 ({len(keywords)}개 키워드)")
    logger.info(f"검색 기간: {get_date_range()[0]} ~ {get_date_range()[1]}")

    for i, keyword in enumerate(keywords):
        logger.info(f"[{i+1}/{len(keywords)}] '{keyword}' 검색 중...")
        bids = fetch_bids_by_keyword(keyword)

        new_count = 0
        for bid in bids:
            key = bid.get("bid_no", "") or bid.get("title", "")
            if key and key not in seen:
                seen.add(key)
                all_bids.append(bid)
                new_count += 1

        if new_count > 0:
            logger.info(f"  → 신규 {new_count}건 (누적 {len(all_bids)}건)")

        time.sleep(0.5)

    logger.info(f"✅ 총 {len(all_bids)}개 고유 공고 수집")
    return all_bids
