import asyncio

from aiohttp import BasicAuth, ClientSession

from tg_bot.db_models.quick_commands import DbBooking
from tg_bot.misc.browser_processing import BrowserProcessing
from tg_bot.misc.models import WorkTypes


async def main():
    await BrowserProcessing(work_type=WorkTypes.BOOKING_PROCESSING, account_id=2, new_process=True).run_task()


async def main2():
    # auth_token = await BrowserProcessing(account_id=2, new_process=True, work_type="test").run_task()

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 OPR/123.0.0.0"
    headers = {
        "accept": 'application/json, text/plain, */*',
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "authorization": "",
        "connection": "keep-alive",
        "host": "amurbooking.com",
        "referer": "https://amurbooking.com/booking",
        "sec-ch-ua": '"Not;A=Brand";v="99", "Opera GX";v="123", "Chromium";v="139"',
        "sec-ch-ua-mobile": "?0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "cookie": "language=RU",
        "user-agent": user_agent
    }

    proxy = "http://31.59.236.40:59100"
    proxy_auth =  BasicAuth(login="valetinles", password="f5bay87SBb")

    async with ClientSession() as session:
        async with session.get(
                url="https://amurbooking.com/oktet/api/v1/booking/time-slots?date=2025-11-18",
                headers=headers, proxy=proxy, proxy_auth=proxy_auth, timeout=20
        ) as response:
            print(f"code = {response.status}")
            print(await response.text())


if __name__ == "__main__":
    asyncio.run(main())
