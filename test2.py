import asyncio
from datetime import datetime

from aiohttp import ClientSession, BasicAuth

from config import Config
from tg_bot.misc.browser_processing import BrowserProcessing
from tg_bot.misc.utils import Utils


async def main():
    # url = "https://amurbooking.com/oktet/api/v1/vehicle/current-user?page=0&size=10&sort=model,ASC"  # trucks list
    url = "https://amurbooking.com/oktet/api/v1/booking/time-slots?date=2025-11-13"  # get time info
    # url = "https://amurbooking.com/oktet/api/v1/authorization/login"

    headers = {
        "accept": 'application/json, text/plain, */*',
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJhY3Rpdml0aWVzLXNlY3VyZS1hcGkiLCJhdWQiOiJhY3Rpdml0aWVzLXNlY3VyZS1hcHAiLCJzdWIiOiIzNTVmZGZhZC1iNTZkLTQxNjctOTgxNy0xNzRiYWY2ZDkzNGYiLCJleHAiOjE3NjI1NjE2ODYsInJvbCI6W119.V1EEY7BVoPK-feto8g1mgTu9VdMYQwAPP5DCw-TcnRWMVPSlJCzgMeQvL2lYYsUTtmtGy9zm4xFOEM0OzdKS4A",
        "connection": "keep-alive",
        "host": "amurbooking.com",
        "referer": "https://amurbooking.com/booking",
        "sec-ch-ua": '"Not;A=Brand";v="99", "Opera GX";v="123", "Chromium";v="139"',
        "sec-ch-ua-mobile": "?0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "cookie": "language=RU",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 OPR/123.0.0.0"
    }

    payload = {
        "username": "+79638042595",
        "password": "VovanR797$"
    }

    proxy = "http://31.59.236.40:59100"
    proxy_auth = BasicAuth(login="valetinles", password="f5bay87SBb")
    async with ClientSession() as session:
        async with session.get(
                url=url, headers=headers, proxy=proxy, proxy_auth=proxy_auth, timeout=10
        ) as response:
            answer = await response.text()
            print(answer)
            print("headers")
            print(response.headers)


async def main2():
    datetime_of_start = datetime.now(tz=Config.TIMEZONE).strftime(Config.DATETIME_FORMAT)
    logger = await Utils.add_logging(datetime_of_start=datetime_of_start, process_id=0)
    Config.logger = logger

    result = await BrowserProcessing(account_id=1, work_type="temp").run_task()
    print(result)


if __name__ == "__main__":
    asyncio.run(main2())
