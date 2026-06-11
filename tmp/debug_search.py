"""
검색 동작만 집중 디버깅
- 검색 후 DOM 변화를 실시간으로 추적
- 실행: python debug_search.py
"""

import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def run():
    options = Options()
    # headless 끔 - 눈으로 확인
    options.add_argument("--window-size=1600,900")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    )
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=options)

    try:
        # 접속
        logger.info("나라장터 접속...")
        driver.get("https://www.g2b.go.kr/")
        time.sleep(5)

        # 팝업 닫기
        for _ in range(5):
            try:
                btns = driver.find_elements(By.XPATH,
                    "//input[@type='button' and @value='닫기'] | "
                    "//button[contains(@class,'w2window_close')]"
                )
                for b in btns:
                    if b.is_displayed():
                        driver.execute_script("arguments[0].click();", b)
                        time.sleep(0.3)
            except:
                pass
        time.sleep(1)

        # 입찰 메뉴 클릭
        logger.info("입찰 메뉴 클릭...")
        m = driver.find_element(By.ID, "mf_wfm_gnb_wfm_gnbMenu_genDepth1_1_btn_menuLvl1")
        driver.execute_script("arguments[0].click();", m)
        time.sleep(2)

        # 입찰공고목록 클릭
        m2 = driver.find_element(By.ID,
            "mf_wfm_gnb_wfm_gnbMenu_genDepth1_1_genDepth2_0_genDepth3_0_btn_menuLvl3")
        driver.execute_script("arguments[0].click();", m2)
        time.sleep(6)

        # 검색창 확인
        INPUT_ID = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_bidPbancNm"
        BTN_ID = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_btnS0004"

        logger.info("검색창 찾는 중...")
        inp = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, INPUT_ID))
        )
        logger.info(f"검색창 발견! 현재 값: '{inp.get_attribute('value')}'")

        # ── 검색 전 tbody 상태 확인 ──
        TBODY_ID = "mf_wfm_container_tacBidPbancLst_contents_tab2_body_gridView1_body_tbody"
        try:
            tbody_before = driver.find_element(By.ID, TBODY_ID)
            rows_before = tbody_before.find_elements(By.TAG_NAME, "tr")
            logger.info(f"검색 전 tbody 행 수: {len(rows_before)}")
        except:
            logger.warning("검색 전 tbody 없음")

        # ── VR 검색 실행 ──
        logger.info("VR 검색 실행...")

        # 방법 A: 일반 입력
        try:
            driver.execute_script("arguments[0].value = '';", inp)
            inp.clear()
            inp.click()
            inp.send_keys("VR")
            logger.info(f"입력 후 값: '{inp.get_attribute('value')}'")
        except Exception as e:
            logger.error(f"입력 실패: {e}")

            # 방법 B: JavaScript 직접 설정
            logger.info("JS 방식으로 값 설정 시도...")
            driver.execute_script(f"""
                var el = document.getElementById('{INPUT_ID}');
                var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(el, 'VR');
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
            """)
            time.sleep(0.5)
            logger.info(f"JS 설정 후 값: '{inp.get_attribute('value')}'")

        # 검색 버튼 클릭
        btn = driver.find_element(By.ID, BTN_ID)
        logger.info(f"검색 버튼 상태: displayed={btn.is_displayed()}, enabled={btn.is_enabled()}")

        # 클릭 전 tbody 스냅샷
        def get_tbody_html():
            try:
                el = driver.find_element(By.ID, TBODY_ID)
                return el.get_attribute("innerHTML")[:200]
            except:
                return "없음"

        before_html = get_tbody_html()

        driver.execute_script("arguments[0].click();", btn)
        logger.info("검색 버튼 클릭 완료!")

        # ── 결과 변화 추적 (최대 15초) ──
        logger.info("결과 로딩 대기 중...")
        for i in range(15):
            time.sleep(1)
            after_html = get_tbody_html()

            # tbody innerHTML이 변했으면 로딩 완료
            if after_html != before_html and after_html != "없음":
                logger.info(f"✅ {i+1}초 후 결과 변화 감지!")
                break

            # 로딩 인디케이터 확인
            loading = driver.find_elements(By.CSS_SELECTOR,
                ".w2loading_mask, [class*='loading'], [class*='spinner']")
            loading_visible = [l for l in loading if l.is_displayed()]
            logger.info(f"  {i+1}초... 로딩중={len(loading_visible)}개, tbody변화={'있음' if after_html != before_html else '없음'}")

        # ── 결과 파싱 ──
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        tbody = soup.find("tbody", {"id": TBODY_ID})

        if tbody:
            rows = tbody.find_all("tr", class_="grid_body_row")
            visible = [r for r in rows if "w2grid_hidedRow" not in r.get("class", [])]
            logger.info(f"\n검색 결과: 전체 {len(rows)}행, 표시 {len(visible)}행")

            for i, row in enumerate(visible[:10]):
                tc = row.find("td", {"col_id": "bidPbancNm"})
                if tc and tc.find("a"):
                    logger.info(f"  [{i+1}] {tc.find('a').get_text(strip=True)[:60]}")
        else:
            logger.error("tbody 없음! 페이지 소스 일부:")
            src = driver.page_source
            # gridView1 관련 부분 찾기
            idx = src.find("gridView1")
            if idx >= 0:
                logger.info(f"  gridView1 소스: {src[idx:idx+300]}")

        # ── 페이지에 존재하는 모든 tbody id 확인 ──
        logger.info("\n페이지의 모든 tbody:")
        tbodies = driver.find_elements(By.TAG_NAME, "tbody")
        for tb in tbodies:
            tid = tb.get_attribute("id")
            trows = tb.find_elements(By.TAG_NAME, "tr")
            if tid:
                logger.info(f"  id={tid}, 행수={len(trows)}")

        input("\n브라우저를 확인하고 Enter를 눌러 종료...")

    except Exception as e:
        logger.error(f"오류: {e}", exc_info=True)
        input("Enter로 종료...")
    finally:
        driver.quit()

if __name__ == "__main__":
    run()
