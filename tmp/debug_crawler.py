"""
나라장터 크롤러 진단 스크립트
- headless 모드 OFF (브라우저 직접 확인 가능)
- 단계별 실행으로 어디서 막히는지 확인
- 실행: python debug_crawler.py
"""

import sys
import os
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


def run_debug():
    logger.info("=== 디버그 모드 시작 (브라우저 창이 열립니다) ===")

    options = Options()
    # !! headless 끔 - 브라우저 직접 확인 !!
    # options.add_argument("--headless=new")
    options.add_argument("--window-size=1600,900")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    wait = WebDriverWait(driver, 20)

    try:
        # STEP 1: 접속
        logger.info("STEP 1: 나라장터 접속")
        driver.get("https://www.g2b.go.kr/")
        time.sleep(4)
        logger.info(f"  → URL: {driver.current_url}")
        logger.info(f"  → Title: {driver.title}")

        # STEP 2: 팝업 닫기
        logger.info("STEP 2: 팝업 닫기")
        close_btns = driver.find_elements(By.CSS_SELECTOR, "button.w2window_close")
        logger.info(f"  → w2window_close 버튼 발견: {len(close_btns)}개")
        for btn in close_btns:
            try:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    logger.info("    닫기 버튼 클릭 완료")
                    time.sleep(0.5)
            except Exception as e:
                logger.debug(f"    버튼 클릭 실패: {e}")

        input_btns = driver.find_elements(
            By.XPATH, "//input[@type='button' and @value='닫기']"
        )
        logger.info(f"  → 닫기 input 버튼: {len(input_btns)}개")
        for btn in input_btns:
            try:
                if btn.is_displayed():
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.3)
            except Exception:
                pass
        time.sleep(1)

        # STEP 3: 메뉴 탐색
        logger.info("STEP 3: 입찰 메뉴 탐색")

        # 메뉴 아이디 확인
        bid_menu_ids = [
            "mf_wfm_gnb_wfm_gnbMenu_genDepth1_1_btn_menuLvl1",
            "mf_wfm_gnb_wfm_gnbMenu_wq_uuid_576",
        ]
        for mid in bid_menu_ids:
            el = driver.find_elements(By.ID, mid)
            logger.info(f"  → {mid}: {'발견' if el else '없음'}")

        # 입찰 메뉴 클릭
        try:
            bid_menu = driver.find_element(
                By.ID, "mf_wfm_gnb_wfm_gnbMenu_genDepth1_1_btn_menuLvl1"
            )
            driver.execute_script("arguments[0].click();", bid_menu)
            logger.info("  → 입찰 메뉴 클릭 완료")
            time.sleep(2)

            # depth3 메뉴 확인
            depth3 = driver.find_elements(
                By.ID,
                "mf_wfm_gnb_wfm_gnbMenu_genDepth1_1_genDepth2_0_genDepth3_0_btn_menuLvl3"
            )
            logger.info(f"  → 입찰공고목록 메뉴: {'발견' if depth3 else '없음'}")

            if depth3:
                driver.execute_script("arguments[0].click();", depth3[0])
                logger.info("  → 입찰공고목록 클릭 완료")
                time.sleep(5)
        except Exception as e:
            logger.error(f"  → 메뉴 클릭 실패: {e}")

        # STEP 4: 현재 페이지 상태
        logger.info("STEP 4: 현재 페이지 상태 확인")
        logger.info(f"  → URL: {driver.current_url}")

        search_btn = driver.find_elements(
            By.ID,
            "mf_wfm_container_tacBidPbancLst_contents_tab2_body_btnS0004"
        )
        logger.info(f"  → 검색 버튼: {'발견 ✅' if search_btn else '없음 ❌'}")

        bid_input = driver.find_elements(
            By.ID,
            "mf_wfm_container_tacBidPbancLst_contents_tab2_body_bidPbancNm"
        )
        logger.info(f"  → 공고명 입력창: {'발견 ✅' if bid_input else '없음 ❌'}")

        if not search_btn:
            logger.error("  !! 입찰공고목록 페이지 진입 실패 !!")
            logger.info("  → 현재 페이지 소스 일부:")
            src = driver.page_source
            logger.info(f"  {src[:500]}")
            input("계속하려면 Enter를 누르세요 (브라우저 확인 후)...")
            return

        # STEP 5: 검색 테스트
        logger.info("STEP 5: 'VR' 키워드 검색 테스트")

        inp = bid_input[0]
        driver.execute_script("arguments[0].value = '';", inp)
        inp.clear()
        inp.send_keys("VR")
        time.sleep(0.5)

        btn = search_btn[0]
        driver.execute_script("arguments[0].click();", btn)
        logger.info("  → 검색 버튼 클릭 완료")
        time.sleep(4)

        # STEP 6: 결과 파싱
        logger.info("STEP 6: 검색 결과 파싱")
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tbody = soup.find(
            "tbody",
            {"id": "mf_wfm_container_tacBidPbancLst_contents_tab2_body_gridView1_body_tbody"}
        )

        if tbody:
            rows = tbody.find_all("tr", class_="grid_body_row")
            visible = [r for r in rows if "w2grid_hidedRow" not in r.get("class", [])]
            logger.info(f"  → 전체 행: {len(rows)}개, 표시된 행: {len(visible)}개")

            for i, row in enumerate(visible[:5]):
                title_cell = row.find("td", {"col_id": "bidPbancNm"})
                if title_cell:
                    a = title_cell.find("a")
                    if a:
                        logger.info(f"  [{i+1}] {a.get_text(strip=True)[:60]}")
        else:
            logger.error("  !! 결과 테이블을 찾을 수 없음 !!")
            # 페이지 소스에서 관련 내용 찾기
            if "gridView1" in driver.page_source:
                logger.info("  → gridView1은 페이지에 존재함")
            if "데이터가 없음" in driver.page_source:
                logger.info("  → '데이터가 없음' 메시지 발견")

        logger.info("=== 디버그 완료 ===")
        input("브라우저를 확인하고 Enter를 눌러 종료하세요...")

    except Exception as e:
        logger.error(f"디버그 중 오류: {e}", exc_info=True)
        input("Enter를 눌러 종료...")
    finally:
        driver.quit()


if __name__ == "__main__":
    run_debug()
