import os

from dotenv import load_dotenv
import requests

load_dotenv(override=True)

API_TOKEN = os.getenv("TELEGRAM")
URL = "https://m.bunjang.co.kr"
API_URL = f"https://api.telegram.org/bot{API_TOKEN}/sendMessage"

chat_id = [6546448196, 7745657139]


def check_price(number):
    if number < 0:
        return "새로운 물품🆕"
    elif number < 30000:
        return str(number) + "원😗"
    elif number < 60000:
        return str(number) + "원🙂"
    elif number < 90000:
        return str(number) + "원😀"
    elif number < 150000:
        return str(number) + "원😍"
    else:
        return str(number) + "원🤩"


def send(params):
    # Sending GET request
    response = requests.get(API_URL, params=params)

    # Print the response
    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print("Failed to send message!")
        print(response)


def send_announcement(data, chatId):
    title = data[0]
    predict_earn = round(data[5] - data[1], 2)
    description = f"\n\n가격: {data[1]:,}원\n평균가격: {data[5]:.2f}원\n\n예상 수익: {check_price(predict_earn)}\n\n위치: {data[3]}\n게시글 날짜: {data[2]}\n링크: {URL+data[4]}"

    message = f"{title}\n{description}"

    data = {"chat_id": chatId, "text": message}

    send(data)


def telegram_bot_sent(result_list):
    for data in result_list:
        for chatId in chat_id:
            send_announcement(data, chatId)
