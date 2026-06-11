"""
analyzer 단독 테스트 - API 키 없이도 어떤 오류가 나는지 확인
실행: python test_analyzer.py
"""
import os, sys, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

from config import COMPANY_PROFILE, CLAUDE_MODEL
from analyzer import analyze_bid_eligibility

# 테스트용 가상 공고 (실제로 적격이어야 할 것)
test_bid = {
    "title": "2026년 VR 기반 실감형 안전교육 콘텐츠 개발",
    "bid_no": "20260608-TEST-001",
    "org": "한국산업안전보건공단",
    "demand_org": "한국산업안전보건공단",
    "date": "2026-06-08 ~ 2026-06-30",
    "contract_method": "일반경쟁",
    "award_method": "최저가낙찰",
    "estimated_price": "150,000,000원",
    "budget": "165,000,000원",
    "bid_deadline": "2026-06-25",
    "keyword": "VR",
    "summary": "VR 기반 실감형 안전교육 콘텐츠 개발 용역",
    "detail_text": "소프트웨어개발, VR 콘텐츠, 실감형 교육, 디지털콘텐츠개발서비스",
    "files": [{"name": "입찰공고문.pdf", "size": "1.2MB"}],
    "industry_limit": "소프트웨어사업자 (디지털콘텐츠개발서비스)",
}

print("=" * 50)
print("API 키 환경변수 확인:")
api_key = os.environ.get("ANTHROPIC_API_KEY", "")
if api_key:
    print(f"  ✅ API 키 설정됨 (앞 10자: {api_key[:10]}...)")
else:
    print("  ❌ ANTHROPIC_API_KEY 환경변수 없음!")
    print("  → .env 파일 또는 set 명령어로 키 설정 필요")
    
    # .env 파일 확인
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        print(f"  → .env 파일 발견, 읽는 중...")
        with open(env_file) as f:
            for line in f:
                if "ANTHROPIC_API_KEY" in line:
                    val = line.strip().split("=", 1)[-1].strip().strip('"').strip("'")
                    os.environ["ANTHROPIC_API_KEY"] = val
                    print(f"  ✅ .env에서 키 로드 (앞 10자: {val[:10]}...)")
                    break
    else:
        print("  → .env 파일도 없음")

print()
print("테스트 공고로 AI 분석 실행 중...")
print(f"모델: {CLAUDE_MODEL}")
print()

result = analyze_bid_eligibility(test_bid, COMPANY_PROFILE, CLAUDE_MODEL)

print("=" * 50)
print("분석 결과:")
print(f"  점수: {result.get('score')}/10")
print(f"  적격: {result.get('eligible')}")
print(f"  이유: {result.get('reason')}")
print(f"  권고: {result.get('recommendation')}")