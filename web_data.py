from bs4 import BeautifulSoup
import mysql.connector
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import time

from telegram_bot import crawl_and_telegram_alert

# 1. .env 파일 로드
load_dotenv(override=True)


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from bs4 import BeautifulSoup


# Selenium 웹드라이버 설정
def crawl_and_store():
    # Selenium 설정
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--headless")  # Headless 모드
    options.add_argument("--disable-application-cache")  # 캐시 비활성화
    options.add_argument("--disable-dev-shm-usage")         # GPU 사용 안 함
    options.add_argument("--disk-cache-size=0")
    options.add_argument("--incognito")
    service = Service(
        executable_path="./chromedriver-linux64/chromedriver",
        service_log_path='./local/share/selenium/logfile.log'
    )  # chromedriver 경로
    options.add_argument("--user-data-dir=/tmp/selenium_profile")
    driver = webdriver.Chrome(service=service, options=options)
    # 브라우저 쿠키 삭제
    driver.delete_all_cookies()
    driver.execute_cdp_cmd("Network.clearBrowserCache", {})

    # 특정 캐시 파일이나 저장소를 삭제하려면 DevTools 프로토콜 사용 가능
    driver.refresh()
    time.sleep(3)

    # 웹 페이지 로드
    URL = "https://m.bunjang.co.kr/search/products?category_id=600&order=date&q=%EA%B8%89%EC%B2%98%20%EB%AF%B8%EA%B0%9C%EB%B4%89"
    driver.get(URL)
    html_content = driver.page_source

    # BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(html_content, "html.parser")
    data = soup.find_all("div", class_="sc-BngTV fuvCPB")
    # 크롤링 결과 저장할 리스트
    result_list = []

    # 각 div 태그 내의 데이터를 추출
    for div_tag in data:
        # 각 div 태그 내의 a 태그 찾기
        a_tag = div_tag.find("a")

        check_ad = a_tag.find("span", class_="sc-likbZx jEQyru")
        if a_tag and not check_ad:
            # a 태그 내부의 두 번째 div 찾기
            value1 = a_tag.find("div", class_="sc-RcBXQ kWzERy").get_text(strip=True)
            value2 = int(
                a_tag.find("div", class_="sc-iSDuPN cPlkrx")
                .get_text(strip=True)
                .replace(",", "")
            )
            value3 = (
                a_tag.find("div", class_="sc-clNaTc kwurog")
                .find("span")
                .get_text(strip=True)
            )
            if "시간 전" in value3:
                hours = int(value3.replace("시간 전", "").strip())
                timestamp = datetime.now() - timedelta(hours=hours)
            elif "분 전" in value3:
                minutes = int(value3.replace("분 전", "").strip())
                timestamp = datetime.now() - timedelta(minutes=minutes)
            elif "일 전" in value3:
                days = int(value3.replace("일 전", "").strip())
                timestamp = datetime.now() - timedelta(days=days)
            else:
                timestamp = datetime.now()

            div_value4 = a_tag.find("div", class_="sc-fZwumE hFuucq")
            for img in div_value4.find_all("img"):
                img.decompose()

            value4 = div_value4.get_text(strip=True)
            value5 = a_tag.get("href")

            result_list.append((value1, value2, timestamp, value4, value5))

    result_list.reverse()

    # 4. MySQL 기본 연결 (데이터베이스 없이 연결)
    db_config = {
        "host": os.getenv("HOST"),
        "user": os.getenv("USER"),  # MySQL 사용자 이름
        "password": os.getenv("PASSWORD"),  # MySQL 비밀번호
    }

    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    # 5. 데이터베이스 생성 (없으면 생성)
    cursor.execute("CREATE DATABASE IF NOT EXISTS web_data;")
    connection.commit()

    # 6. 데이터베이스 연결 갱신
    db_config["database"] = "web_data"
    connection.close()  # 기존 연결 닫기
    connection = mysql.connector.connect(**db_config)
    cursor = connection.cursor()

    # 7. 테이블 생성
    table_creation_query = """
    CREATE TABLE IF NOT EXISTS web_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        price DECIMAL(10, 2) NOT NULL,
        post_date DATETIME NOT NULL,
        location VARCHAR(255) NOT NULL,
        link VARCHAR(255) NOT NULL
    );
    """
    cursor.execute(table_creation_query)

    # 8. 크롤링한 데이터 삽입
    insert_query = "INSERT INTO web_data (title, price, post_date, location, link) VALUES (%s, %s, %s, %s, %s)"
    select_query = "SELECT COUNT(*) FROM web_data WHERE title = %s AND price = %s AND location = %s"

    telegram_list = []

    for data in result_list:
        # 중복 확인
        cursor.execute(
            select_query,
            (
                data[0],
                data[1],
                data[3],
            ),
        )
        count = cursor.fetchone()[0]

        if count == 0:  # 중복이 없으면 삽입
            cursor.execute(insert_query, (data[0], data[1], data[2], data[3], data[4]))
            print(f"데이터 추가 됨: {data[0]}")

            # telegram_bot 으로 전송
            telegram_list.append(data)
            
    crawl_and_telegram_alert(telegram_list)

    # 커밋 및 종료
    connection.commit()
    cursor.close()
    connection.close()

    print("Complete And Wait 2 min...")


while True:
    crawl_and_store()
    time.sleep(120)  # 5분 (300초) 대기
