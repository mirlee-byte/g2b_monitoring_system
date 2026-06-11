"""
나라장터(G2B) 크롤러 v3
핵심 수정:
1. 검색 후 결과 로딩을 "총건수 텍스트 변화"로 감지 (tbody 행수 변화보다 정확)
2. tr 파싱 시 class 조건 제거 → WebSquare가 다양한 클래스명 사용
3. col_id 기반 파싱 유지 (검증된 방식)
4. 검색 전 입력값 확인 로직 추가
"""

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ── ID 상수 ──
INPUT_ID  = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_bidPbancNm"
BTN_ID    = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_btnS0004"
TBODY_ID  = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_gridView1_body_tbody"
TOTAL_ID  = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_tbxTotCnt"  # 총건수 표시


def get_driver(download_dir: str) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=ko-KR")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("prefs", {
        "download.default_directory": os.path.abspath(download_dir),
        "download.prompt_for_download": False,
    })

    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    driver.implicitly_wait(3)
    return driver


def close_all_popups(driver):
    """팝업 닫기 (0개~다수 모두 처리)"""
    time.sleep(2)
    for _ in range(3):
        closed = 0
        # input[type=button] value=닫기/확인
        for text in ["닫기", "확인", "창닫기"]:
            for btn in driver.find_elements(By.XPATH,
                    f"//input[@type='button' and @value='{text}']"):
                try:
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        closed += 1
                        time.sleep(0.3)
                except Exception:
                    pass
        # w2window_close 버튼
        for btn in driver.find_elements(By.CSS_SELECTOR, "button.w2window_close"):
            try:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    closed += 1
                    time.sleep(0.3)
            except Exception:
                pass
        if closed == 0:
            break
    # JS 강제 숨기기
    driver.execute_script("""
        document.querySelectorAll('.w2window_wrap,[class*="w2window"],.pop_wrap,.modal_wrap')
            .forEach(function(el){ if(el&&el.style){ el.style.display='none'; } });
    """)
    time.sleep(1)
    logger.info("팝업 처리 완료")


def navigate_to_bid_list(driver) -> bool:
    """입찰공고목록 진입 (3가지 방식 순차 시도)"""
    wait = WebDriverWait(driver, 15)

    def check_arrived():
        """검색 버튼 존재 여부로 진입 확인"""
        try:
            driver.find_element(By.ID, BTN_ID)
            return True
        except Exception:
            return False

    # 방식 1: 메뉴 클릭
    try:
        m = wait.until(EC.presence_of_element_located(
            (By.ID, "mf_wfm_gnb_wfm_gnbMenu_genDepth1_1_btn_menuLvl1")))
        driver.execute_script("arguments[0].click();", m)
        time.sleep(2)

        m2 = wait.until(EC.presence_of_element_located(
            (By.ID, "mf_wfm_gnb_wfm_gnbMenu_genDepth1_1_genDepth2_0_genDepth3_0_btn_menuLvl3")))
        driver.execute_script("arguments[0].click();", m2)
        time.sleep(5)

        if check_arrived():
            logger.info("✅ 입찰공고목록 진입 성공 (메뉴 클릭)")
            return True
    except Exception as e:
        logger.warning(f"메뉴 클릭 실패: {e}")

    # 방식 2: JS 이벤트
    try:
        driver.execute_script("""
            var m = document.getElementById(
                'mf_wfm_gnb_wfm_gnbMenu_genDepth1_1_genDepth2_0_genDepth3_0_btn_menuLvl3');
            if(m){ m.click(); m.dispatchEvent(new MouseEvent('click',{bubbles:true})); }
        """)
        time.sleep(5)
        if check_arrived():
            logger.info("✅ 입찰공고목록 진입 성공 (JS 이벤트)")
            return True
    except Exception as e:
        logger.warning(f"JS 이벤트 실패: {e}")

    # 방식 3: 최근본화면 링크 활용
    try:
        recent_links = driver.find_elements(By.XPATH,
            "//*[contains(text(),'입찰공고목록')]")
        for link in recent_links:
            try:
                driver.execute_script("arguments[0].click();", link)
                time.sleep(4)
                if check_arrived():
                    logger.info("✅ 입찰공고목록 진입 성공 (최근화면 링크)")
                    return True
            except Exception:
                pass
    except Exception:
        pass

    logger.error("❌ 입찰공고목록 진입 실패")
    return False


def get_current_total(driver) -> str:
    """현재 총건수 텍스트 반환 (검색 결과 변화 감지용)"""
    try:
        # 총건수 span
        el = driver.find_element(By.ID, TOTAL_ID)
        return el.text.strip()
    except Exception:
        pass
    try:
        # tbody의 tr 수로 대체
        tbody = driver.find_element(By.ID, TBODY_ID)
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        return str(len(rows))
    except Exception:
        return ""


def execute_search(driver, keyword: str) -> bool:
    """키워드 검색 실행 - 결과 로딩 완료까지 대기"""
    wait = WebDriverWait(driver, 10)

    # ── 입력 전 현재 상태 스냅샷 ──
    total_before = get_current_total(driver)

    # ── 입력창 클리어 후 키워드 입력 ──
    try:
        inp = wait.until(EC.element_to_be_clickable((By.ID, INPUT_ID)))

        # 기존 값 완전 제거
        driver.execute_script("arguments[0].value = '';", inp)
        inp.clear()
        time.sleep(0.2)

        # 값 입력
        inp.click()
        inp.send_keys(keyword)
        time.sleep(0.3)

        # 입력값 확인
        actual_val = inp.get_attribute("value")
        if actual_val != keyword:
            # JS fallback
            driver.execute_script(f"""
                var el = arguments[0];
                var setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype,'value').set;
                setter.call(el, '{keyword}');
                el.dispatchEvent(new Event('input', {{bubbles:true}}));
                el.dispatchEvent(new Event('change', {{bubbles:true}}));
            """, inp)
            time.sleep(0.3)
            actual_val = inp.get_attribute("value")

        logger.debug(f"입력값 확인: '{actual_val}'")

    except Exception as e:
        logger.error(f"입력 실패: {e}")
        return False

    # ── 검색 버튼 클릭 ──
    try:
        btn = driver.find_element(By.ID, BTN_ID)
        driver.execute_script("arguments[0].click();", btn)
    except Exception as e:
        logger.error(f"검색 버튼 클릭 실패: {e}")
        return False

    # ── 결과 로딩 대기 (최대 20초) ──
    # 나라장터는 검색 후 tbody를 교체하는 방식
    # "noresult" div 표시 or tbody에 행이 생기면 완료
    NORESULT_ID = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_gridView1_noresult"
    for i in range(20):
        time.sleep(1)
        try:
            # 총건수 변화 감지
            total_after = get_current_total(driver)
            if total_after != total_before:
                logger.debug(f"  {i+1}초 후 결과 변화 감지: '{total_before}'→'{total_after}'")
                break

            # noresult div가 block이면 검색 완료 (결과 없음)
            try:
                nr = driver.find_element(By.ID, NORESULT_ID)
                style = nr.get_attribute("style") or ""
                if "display: block" in style or "display:block" in style:
                    logger.debug(f"  {i+1}초: 검색 결과 없음 확인")
                    break
            except Exception:
                pass

        except Exception:
            pass
    else:
        logger.warning(f"  [{keyword}] 20초 대기 후 결과 미변화")

    time.sleep(1)  # 추가 안정화 대기
    return True


def parse_bid_list(driver, keyword: str) -> list:
    """현재 페이지 입찰공고 목록 파싱"""
    results = []

    # 결과 없음 체크
    NORESULT_ID = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_gridView1_noresult"
    try:
        nr = driver.find_element(By.ID, NORESULT_ID)
        style = nr.get_attribute("style") or ""
        if "display: none" not in style and "visibility: hidden" not in style:
            # 텍스트로 최종 확인
            if "데이터가 없음" in nr.text:
                logger.info(f"[{keyword}] 검색 결과 없음")
                return []
    except Exception:
        pass

    soup = BeautifulSoup(driver.page_source, "html.parser")
    tbody = soup.find("tbody", {"id": TBODY_ID})

    if not tbody:
        logger.warning(f"[{keyword}] tbody를 찾을 수 없음")
        return []

    # ── tr 파싱 (class 조건 없이 모든 tr 처리) ──
    rows = tbody.find_all("tr")
    logger.debug(f"[{keyword}] 전체 tr 수: {len(rows)}")

    for row in rows:
        # 숨김 행 제외
        classes = row.get("class", [])
        if "w2grid_hidedRow" in classes:
            continue
        # 헤더 행 제외 (th가 있으면)
        if row.find("th"):
            continue

        # 공고명 추출
        title_cell = row.find("td", {"col_id": "bidPbancNm"})
        if not title_cell:
            continue
        a_tag = title_cell.find("a")
        title = a_tag.get_text(strip=True) if a_tag else title_cell.get_text(strip=True)
        if not title:
            continue

        def get_cell(col_id):
            c = row.find("td", {"col_id": col_id})
            return c.get_text(strip=True) if c else ""

        bid_no    = get_cell("bidPbancUntyNoOrd")
        org       = get_cell("oderInstUntyGrpNm")
        demand    = get_cell("dmstNm")
        date_str  = get_cell("pbancPstgDt")
        status    = get_cell("pbancSttsNm")
        bid_type  = get_cell("prcmBsneSeCdNm")

        # 취소 공고 제외
        if "취소" in status:
            continue

        # 요약 팝업 버튼 내용
        summary = ""
        sum_cell = row.find("td", {"col_id": "summary"})
        if sum_cell:
            btn = sum_cell.find("button")
            if btn:
                inner = btn.find("div")
                if inner:
                    summary = inner.get_text(separator=" | ", strip=True)

        trindex = row.get("trindex", "")

        results.append({
            "title": title,
            "bid_no": bid_no,
            "org": org,
            "demand_org": demand,
            "date": date_str,
            "status": status,
            "bid_type": bid_type,
            "summary": summary,
            "keyword": keyword,
            "trindex": trindex,
        })

    logger.info(f"[{keyword}] {len(results)}건 파싱")
    return results


def get_bid_detail(driver, bid_info: dict) -> dict:
    """공고 상세 정보 조회 (선택적)"""
    detail = {
        "contract_method": "", "award_method": "",
        "estimated_price": "", "budget": "",
        "bid_deadline": "", "files": [], "detail_text": "",
    }

    # summary에서 가격 파싱
    import re
    summary = bid_info.get("summary", "")
    m = re.search(r"추정가격\s*[:\s]*([\d,]+)원", summary)
    if m:
        detail["estimated_price"] = m.group(1) + "원"
    m = re.search(r"배정예산\s*[:\s]*([\d,]+)원", summary)
    if m:
        detail["budget"] = m.group(1) + "원"
    m = re.search(r"낙찰방법\s*[:\s]*([^\|]+)", summary)
    if m:
        detail["award_method"] = m.group(1).strip()

    # 상세 페이지 클릭 (trindex 기반)
    trindex = bid_info.get("trindex", "")
    if not trindex:
        return detail

    try:
        link_css = (
            f"#mf_wfm_container_tacBidPbancLst_contents_tab2_body_gridView1"
            f"_cell_{trindex}_6 a"
        )
        link = WebDriverWait(driver, 8).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, link_css))
        )
        driver.execute_script("arguments[0].click();", link)
        time.sleep(3)

        handles = driver.window_handles
        if len(handles) > 1:
            driver.switch_to.window(handles[-1])
            time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # 계약방법, 낙찰방법, 추정가격, 배정예산
        for label_text, key in [
            ("계약방법", "contract_method"), ("낙찰방법", "award_method"),
            ("추정가격", "estimated_price"), ("배정예산", "budget"),
        ]:
            lbl = soup.find("label", string=lambda t: t and label_text in t)
            if lbl:
                th = lbl.find_parent("th")
                if th:
                    td = th.find_next_sibling("td")
                    if td:
                        inp = td.find("input")
                        val = inp.get("value", "").strip() if inp else td.get_text(strip=True)
                        if val and not detail.get(key):
                            detail[key] = val

        # 입찰마감일
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            for cell in cells:
                if "입찰서제출" in cell.get_text():
                    end_td = row.find("td", {"col_id": "endDt"})
                    if end_td:
                        detail["bid_deadline"] = end_td.get_text(strip=True)
                    break

        # 첨부파일
        file_tbody = soup.find("tbody", {"id": "wq_uuid_7360_grdFile_body_tbody"})
        if file_tbody:
            for frow in file_tbody.find_all("tr"):
                fname_td = frow.find("td", {"col_id": "orgnlAtchFileNm"})
                fsize_td = frow.find("td", {"col_id": "fileSz"})
                if fname_td:
                    detail["files"].append({
                        "name": fname_td.get_text(strip=True),
                        "size": fsize_td.get_text(strip=True) if fsize_td else "",
                    })

        # 상세 텍스트 (AI 분석용)
        main = soup.find("div", {"id": "mf_wfm_container_mainWframe_pageType"})
        if main:
            detail["detail_text"] = main.get_text(separator="\n", strip=True)[:3000]

    except Exception as e:
        logger.debug(f"상세 조회 실패: {e}")
    finally:
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        else:
            try:
                back = driver.find_element(By.ID, "mf_wfm_container_btnBackList")
                driver.execute_script("arguments[0].click();", back)
            except Exception:
                driver.back()
        time.sleep(2)

    return detail


def run_crawler(keywords: list, download_dir: str) -> list:
    """전체 크롤링 실행"""
    os.makedirs(download_dir, exist_ok=True)
    driver = get_driver(download_dir)
    all_bids = []
    seen = set()

    try:
        # 1. 나라장터 접속
        logger.info("나라장터 접속 중...")
        driver.get("https://www.g2b.go.kr/")
        time.sleep(5)

        # 2. 팝업 닫기
        close_all_popups(driver)

        # 3. 입찰공고목록 진입
        logger.info("입찰공고목록 이동 중...")
        if not navigate_to_bid_list(driver):
            logger.error("입찰공고목록 진입 실패. 종료.")
            return []

        logger.info(f"총 {len(keywords)}개 키워드 검색 시작")

        # 4. 키워드별 검색
        for i, kw in enumerate(keywords):
            logger.info(f"[{i+1}/{len(keywords)}] '{kw}' 검색...")

            # 페이지가 입찰공고목록인지 재확인
            if BTN_ID not in driver.page_source:
                logger.warning(f"[{kw}] 페이지 이탈 감지, 재진입 시도")
                if not navigate_to_bid_list(driver):
                    logger.error(f"[{kw}] 재진입 실패, 스킵")
                    continue

            if not execute_search(driver, kw):
                logger.error(f"[{kw}] 검색 실행 실패")
                continue

            bids = parse_bid_list(driver, kw)
            for bid in bids:
                bid_no = bid.get("bid_no", "")
                key = bid_no or bid.get("title", "")
                if key and key not in seen:
                    seen.add(key)
                    all_bids.append(bid)

            time.sleep(2)

        logger.info(f"총 {len(all_bids)}개 고유 공고 수집")

        # 5. 상세 정보 보완 (최대 10건)
        for bid in all_bids[:10]:
            logger.info(f"상세 조회: {bid.get('title','')[:30]}...")
            detail = get_bid_detail(driver, bid)
            bid.update(detail)
            time.sleep(1)

    except Exception as e:
        logger.error(f"크롤링 오류: {e}", exc_info=True)
    finally:
        driver.quit()

    return all_bids
