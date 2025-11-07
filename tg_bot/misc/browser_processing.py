import asyncio
import json
from copy import deepcopy
from typing import Optional, Union

from aiohttp import ClientSession, BasicAuth
from playwright.async_api import Page, Browser, async_playwright, ProxySettings

from config import Config
from tg_bot.db_models.db_gino import connect_to_db
from tg_bot.db_models.quick_commands import DbAccount
from tg_bot.misc.models import ProxyData, WorkTypes


class BrowserProcessing:
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36 OPR/123.0.0.0"
    DEFAULT_HEADERS = {
        "accept": 'application/json, text/plain, */*',
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "connection": "keep-alive",
        "host": "amurbooking.com",
        "sec-ch-ua": '"Not;A=Brand";v="99", "Opera GX";v="123", "Chromium";v="139"',
        "sec-ch-ua-mobile": "?0",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "cookie": "language=RU",
        "user-agent": USER_AGENT
    }
    AIOHTTP_SESSION: Optional[ClientSession] = None

    ACCOUNT_ID: Optional[int] = None
    ACCOUNT_PHONE: Optional[str] = None
    ACCOUNT_PASSWORD: Optional[str] = None
    ACCOUNT_AUTH_TOKEN: Optional[str] = None
    ACCOUNT_PROXY: Optional[ProxyData] = None

    WORK_TYPE: Optional[str] = None

    PL_OBJ = None
    PL_BROWSER: Optional[Browser] = None
    PL_CONTEXT = None
    PL_PAGE: Optional[Page] = None

    def __init__(self, account_id: int, work_type: str):
        self.AIOHTTP_SESSION = ClientSession()
        self.ACCOUNT_ID = account_id
        self.WORK_TYPE = work_type

    async def run_task(self):
        await connect_to_db(remove_data=False)

        db_account = await DbAccount(db_id=self.ACCOUNT_ID).select()
        self.ACCOUNT_PHONE = db_account.phone
        self.ACCOUNT_PASSWORD = db_account.password
        self.ACCOUNT_AUTH_TOKEN = db_account.auth_token

        host, port, username, password = db_account.proxy.split(":")
        self.ACCOUNT_PROXY = ProxyData(host=host, port=port, username=username, password=password)

        if self.WORK_TYPE == WorkTypes.GET_TRUCKS_LIST:
            return await self.get_trucks_info()

    async def get_trucks_info(self, retries: int = 3):
        headers = deepcopy(self.DEFAULT_HEADERS)
        headers["referer"] = "https://amurbooking.com/lk"

        if not self.ACCOUNT_AUTH_TOKEN:
            if not await self.auth():
                return False

        headers["authorization"] = self.ACCOUNT_AUTH_TOKEN

        async with self.AIOHTTP_SESSION.get(
                url="https://amurbooking.com/oktet/api/v1/vehicle/current-user?page=0&size=10&sort=model,ASC",
                headers=headers,
                proxy=f"http://{self.ACCOUNT_PROXY.host}:{self.ACCOUNT_PROXY.port}",
                proxy_auth=BasicAuth(login=self.ACCOUNT_PROXY.username, password=self.ACCOUNT_PROXY.password) \
                        if self.ACCOUNT_PROXY.username else None,
                timeout=20
        ) as response:
            if response.status == 200:
                answer = json.loads(await response.text())
                return [f"{car_data['model']} / {car_data['registrationPlate']}" for car_data in answer["content"]]

            elif response.status == 401:
                Config.logger.error(f"Не удалось получить данные о грузовиках! Пробую пройти авторизацию...")
                await self.auth()

            else:
                Config.logger.error(
                    f"Не удалось получить данные о грузовиках!"
                    f"\nкод={response.status}\nответ: {await response.text()}"
                )

            if retries:
                await asyncio.sleep(5)
                return await self.get_trucks_info(retries=retries - 1)

            Config.logger.error(
                f"Попытки для получения данных о грузовиках закончились!"
                f"\nкод={response.status}\nответ: {await response.text()}"
            )
            return False

    async def auth(self, retries: int = 3) -> bool:
        headers = deepcopy(self.DEFAULT_HEADERS)
        headers["referer"] = "https://amurbooking.com/user/login"

        payload = {
            "username": self.ACCOUNT_PHONE,
            "password": self.ACCOUNT_PASSWORD
        }

        async with self.AIOHTTP_SESSION.post(
                url="https://amurbooking.com/oktet/api/v1/authorization/login",
                headers=headers, data=payload,
                proxy=f"http://{self.ACCOUNT_PROXY.host}:{self.ACCOUNT_PROXY.port}",
                proxy_auth=BasicAuth(login=self.ACCOUNT_PROXY.username, password=self.ACCOUNT_PROXY.password) \
                        if self.ACCOUNT_PROXY.username else None,
                timeout=20
        ) as response:
            auth_token = None
            if response.status == 200:
                auth_token = response.headers.get("Authorization")
                if auth_token.strip().startswith("Bearer "):
                    self.ACCOUNT_AUTH_TOKEN = auth_token
                    await DbAccount(db_id=self.ACCOUNT_ID).update(auth_token=self.ACCOUNT_AUTH_TOKEN)

                    Config.logger.info(f"Успешно вошел в аккаунт №{self.ACCOUNT_ID}!")
                    return True

            if retries:
                Config.logger.error(f"Не удалось войти в аккаунт!\nКод: {response.status}\nauth_token: {auth_token}")
                await asyncio.sleep(5)
                return await self.auth(retries=retries - 1)

            Config.logger.error("Попытки для входа в аккаунт закончились!")
            return False

    async def get_new_browser_obj(self) -> bool:
        Config.logger.info("Пробую получить новый браузер...")

        if self.PL_BROWSER is not None:
            await self.PL_BROWSER.close()
            Config.logger.info("Закрыл старый браузер")

        if self.PL_OBJ is not None:
            await self.PL_OBJ.stop()
            Config.logger.info("Остановил старый playwright_obj")

        self.PL_OBJ = await async_playwright().start()
        Config.logger.info("Запустил новый экземпляр playwright_obj")

        # if self.PROXY is None:
        #     await self.get_new_proxy()

        proxy_arg = {"server": f"http://{self.ACCOUNT_PROXY.host}:{self.ACCOUNT_PROXY.port}"}
        if self.ACCOUNT_PROXY.username and self.ACCOUNT_PROXY.password:
            proxy_arg["username"] = self.ACCOUNT_PROXY.username
            proxy_arg["password"] = self.ACCOUNT_PROXY.password

        self.PL_BROWSER = await self.PL_OBJ.chromium.launch(headless=bool(Config.HEADLESS), proxy=proxy_arg)
        Config.logger.info("Запустил новый браузер")

        self.PL_CONTEXT = await self.PL_BROWSER.new_context(
            locale="ru",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.6367.207 Safari/537.36"
        )
        Config.logger.info("Запустил новый контекст браузера")

        self.PL_PAGE = await self.PL_CONTEXT.new_page()
        Config.logger.info("Открыл рабочую вкладку")

        return True
