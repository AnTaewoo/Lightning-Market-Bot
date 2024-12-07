from bs4 import BeautifulSoup

import re
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from telegram_bot_sent import telegram_bot_sent

from konlpy.tag import Okt

from bs4 import BeautifulSoup


def read_text_file(filename):
    data = []
    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            data.append(line)
    data = [word.replace("\n", "") for word in data]
    return data


# 리스트에 저장
stopwordsList = read_text_file(
    "./stopwords.txt"
)
preservedList = read_text_file(
    "./preserved.txt"
)


def export_import_word(text):
    # 특수 문자 제거
    text = re.sub(r"[^가-힣0-9a-zA-Z\s]", "", text)

    # Tokenizer 및 품사 태깅
    okt = Okt()
    tokens = okt.pos(text)

    # 보존어 처리
    important_words = []

    for word, pos in tokens:
        # 보존어는 무조건 포함
        word = word.strip()

        if word in preservedList:
            important_words.append(word)

        # 일반 단어 처리: 명사, 숫자, 혹은 숫자가 포함된 단어
        elif (
            pos == "Noun" or word.isdigit() or any(char.isdigit() for char in word)
        ) and word not in stopwordsList:
            important_words.append(word)

    # 결과를 공백으로 구분하여 반환
    result = " ".join(important_words)
    return result


def crawl_and_telegram_alert(data_list):
    if not data_list:
        return

    # Selenium 설정
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--headless")  # Headless 모드
    options.add_argument("--disable-application-cache")  # 캐시 비활성화
    service = Service(
        executable_path="./chromedriver-linux64/chromedriver"
    )  # chromedriver 경로
    driver = webdriver.Chrome(service=service, options=options)
    # 브라우저 쿠키 삭제
    driver.delete_all_cookies()

    # 특정 캐시 파일이나 저장소를 삭제하려면 DevTools 프로토콜 사용 가능
    driver.refresh()
    time.sleep(3)

    URL = "https://m.bunjang.co.kr/search/products?order=date&q="
    # 웹 페이지 로드

    result_list = []
    for data in data_list:
        if data[1] < 100000:
            continue

        keywordStr = export_import_word(data[0])
        searchURL = URL + keywordStr
        driver.get(searchURL)

        html_content = driver.page_source

        # BeautifulSoup으로 HTML 파싱
        soup = BeautifulSoup(html_content, "html.parser")
        div_data = soup.find_all("div", class_="sc-BngTV fuvCPB")
        # 크롤링 결과 저장할 리스트

        # 각 div 태그 내의 데이터를 추출
        search_data = []
        for index, div_tag in enumerate(div_data):

            # 각 div 태그 내의 a 태그 찾기
            a_tag = div_tag.find("a")
            check_ad = a_tag.find("span", class_="sc-likbZx jEQyru")

            if a_tag and not check_ad and not index == 0:
                value = int(
                    a_tag.find("div", class_="sc-iSDuPN cPlkrx")
                    .get_text(strip=True)
                    .replace(",", "")
                )

                if value > data[1] + 500000:
                    continue

                search_data.append(value)

        if not search_data:
            result = list(data) + [-1] + [searchURL]

            result_list.append(result)
        else:
            if (sum(search_data) / len(search_data)) - data[1] > 30000:
                result = list(data) + [sum(search_data) / len(search_data)] + [searchURL]

                result_list.append(result)

    if result_list:
        print("현재 시세보다 쌈. telegram 공지")

        # telegram_bot_sent로 전송
        telegram_bot_sent(result_list)
    else:
        print("현재 시세보다 비쌈. telegram 공지 안됨")
