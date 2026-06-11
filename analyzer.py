"""
Claude AI를 사용하여 입찰 공고의 적격성을 분석하는 모듈
"""

import os
import json
import logging
import anthropic

logger = logging.getLogger(__name__)


def analyze_bid_eligibility(bid_info: dict, company_profile: str, model: str) -> dict:
    """
    입찰 공고 적격성 AI 분석

    반환:
    {
        "score": int (0~10),
        "eligible": bool,
        "reason": str,
        "key_points": list[str],
        "concerns": list[str],
        "recommendation": str
    }
    """
    client = anthropic.Anthropic()

    # 분석할 공고 정보 구성
    bid_text = f"""
## 입찰 공고 정보

- **공고명**: {bid_info.get('title', '')}
- **입찰공고번호**: {bid_info.get('bid_no', '')}
- **공고기관**: {bid_info.get('org', '')}
- **게시/마감일**: {bid_info.get('date', '')}
- **계약방법**: {bid_info.get('contract_method', '')}
- **낙찰방법**: {bid_info.get('award_method', '')}
- **지역제한**: {bid_info.get('region_limit', '')}
- **업종제한**: {bid_info.get('industry_limit', '')}
- **추정가격**: {bid_info.get('estimated_price', '')}
- **배정예산**: {bid_info.get('budget', '')}
- **입찰마감일**: {bid_info.get('bid_deadline', '')}
- **검색키워드**: {bid_info.get('keyword', '')}

## 요약 정보
{bid_info.get('summary', '없음')}

## 상세 내용 (일부)
{bid_info.get('detail_text', '상세 내용 없음')[:2000]}

## 첨부파일 목록
{json.dumps([f.get('name', '') for f in bid_info.get('files', [])], ensure_ascii=False)}
"""

    prompt = f"""당신은 공공 입찰 전문가입니다. 아래 회사 정보와 입찰 공고를 분석하여 이 회사가 해당 입찰에 참여할 수 있는지 적격성을 판단해주세요.

# 회사 정보
{company_profile}

# 분석할 입찰 공고
{bid_text}

# 분석 요청사항
1. **적격 점수 (0~10점)**: 이 회사가 해당 입찰에 적합한지 점수로 평가 (10점=완벽히 적합, 0점=전혀 부적합)
2. **참여 가능 여부**: True/False
3. **핵심 이유**: 점수를 준 핵심 이유 3가지
4. **우려 사항**: 참여 시 주의해야 할 사항
5. **권고 사항**: 참여 여부 및 전략 제안

다음 JSON 형식으로만 응답하세요. 다른 텍스트 없이 순수 JSON만 출력:
{{
    "score": <0~10 정수>,
    "eligible": <true/false>,
    "reason": "<점수를 준 핵심 근거 요약 (2~3문장)>",
    "key_points": ["<긍정적 포인트1>", "<긍정적 포인트2>", "<긍정적 포인트3>"],
    "concerns": ["<우려사항1>", "<우려사항2>"],
    "recommendation": "<참여 권고/비권고 이유와 전략 (2~3문장)>"
}}"""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2000,  # 1000 → 2000으로 증가 (한국어 응답 잘림 방지)
            messages=[{"role": "user", "content": prompt}]
        )

        result_text = response.content[0].text.strip()

        # ── JSON 추출 ──
        # 1. ```json ... ``` 블록 추출
        if "```" in result_text:
            parts = result_text.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    result_text = part
                    break

        # 2. { } 블록만 추출
        if not result_text.startswith("{"):
            start = result_text.find("{")
            end = result_text.rfind("}") + 1
            if start >= 0 and end > start:
                result_text = result_text[start:end]

        result = json.loads(result_text.strip())
        return result

    except json.JSONDecodeError as e:
        logger.error(f"AI 응답 JSON 파싱 실패: {e}")
        return {
            "score": 0,
            "eligible": False,
            "reason": "분석 오류",
            "key_points": [],
            "concerns": ["AI 분석 중 오류 발생"],
            "recommendation": "수동으로 검토 필요"
        }
    except Exception as e:
        logger.error(f"AI 분석 오류: {e}")
        return {
            "score": 0,
            "eligible": False,
            "reason": f"오류: {str(e)}",
            "key_points": [],
            "concerns": [],
            "recommendation": "수동으로 검토 필요"
        }


def analyze_file_content(file_path: str, company_profile: str, model: str) -> str:
    """
    다운로드된 첨부파일 내용을 AI로 분석 (PDF 등)
    """
    client = anthropic.Anthropic()

    # PDF 파일인 경우 텍스트 추출
    file_text = ""
    try:
        if file_path.endswith(".pdf"):
            import subprocess
            result = subprocess.run(
                ["pdftotext", file_path, "-"],
                capture_output=True, text=True, timeout=30
            )
            file_text = result.stdout[:3000]
        elif file_path.endswith((".txt", ".md")):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                file_text = f.read(3000)
    except Exception as e:
        logger.debug(f"파일 읽기 오류: {e}")
        return ""

    if not file_text.strip():
        return ""

    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""다음은 입찰 공고 첨부파일 내용입니다. 
회사 입장에서 참여 가능성을 판단할 핵심 정보를 3~5줄로 요약해주세요.

# 회사 핵심 역량
VR/AR/XR/메타버스/3D콘텐츠/디지털콘텐츠 개발 전문 기업 (올림플래닛)
소프트웨어사업자(디지털콘텐츠개발서비스), 멀티미디어디자인 업종 보유

# 파일 내용
{file_text}

핵심 요약 (한국어):"""
            }]
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"파일 분석 오류: {e}")
        return ""
