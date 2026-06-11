"""나라장터 Open API 테스트"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
import requests
from datetime import datetime, timedelta

API_KEY = os.environ.get("G2B_API_KEY", "")
print(f"API 키: {API_KEY[:10]}..." if API_KEY else "❌ API 키 없음!")

today = datetime.now()
start = (today - timedelta(days=7)).strftime("%Y%m%d%H%M")
end = today.strftime("%Y%m%d%H%M")

url = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServcPPSSrch"
params = {
    "ServiceKey": API_KEY,
    "numOfRows": "10",
    "pageNo": "1",
    "inqryDiv": "1",
    "inqryBgnDt": start,
    "inqryEndDt": end,
    "bidNtceNm": "VR",
    "type": "json",
}

print(f"\n'VR' 용역 검색 (최근 7일: {start}~{end})")
resp = requests.get(url, params=params, timeout=15)
print(f"HTTP: {resp.status_code}")
print(f"응답: {resp.text[:500]}")

try:
    data = resp.json()
    body = data.get("response", {}).get("body", {})
    total = body.get("totalCount", 0)
    items = body.get("items", [])
    print(f"\n✅ 전체 {total}건")
    if items:
        if isinstance(items, dict):
            items = [items]
        for item in items[:5]:
            print(f"  - {item.get('bidNtceNm','')} / {item.get('ntceInsttNm','')}")
except Exception as e:
    print(f"파싱 오류: {e}")
