from typing import Optional
from multiprocessing import Queue

from playwright.async_api import Browser, Page, async_playwright

from config import Config
from tg_bot.misc.models import ProxyData


class BrowserProcessing:
    ACCOUNT_ID: Optional[int] = None
    ACCOUNT_PHONE: Optional[str] = None
    ACCOUNT_PASSWORD: Optional[str] = None
    PROXY: Optional[ProxyData] = None

    WORK_TYPE: Optional[str] = None
    QUEUE_OUT: Optional[Queue] = None

    PL_OBJ = None
    PL_BROWSER: Optional[Browser] = None
    PL_CONTEXT = None
    PL_PAGE_WORKER: Optional[Page] = None

    def __init__(self, work_type: str, account_id: Optional[int] = None, queue_out: Optional[Queue] = None):
        self.WORK_TYPE = work_type
        self.ACCOUNT_ID = account_id
        self.QUEUE_OUT = queue_out

    async def auth(self) -> bool:
        await self.PL_PAGE_WORKER.evaluate("localStorage.clear()")
        await self.PL_PAGE_WORKER.goto("https://amurbooking.com/user/login", timeout=20000)

        locator = self.PL_PAGE_WORKER.locator('oktet-phone-input#username input[type="text"]')
        await locator.wait_for(state='visible', timeout=2500)
        await locator.fill("+79638042595")

        password_input = self.PL_PAGE_WORKER.locator('oktet-password-input#password input[type="password"]')
        await password_input.wait_for(state="visible", timeout=2500)
        await password_input.fill("VovanR797$")

        button = self.PL_PAGE_WORKER.locator("button.px-4")
        await button.wait_for(state="visible", timeout=2500)
        await button.click()

        await self.PL_PAGE_WORKER.wait_for_selector(".btn-lg", timeout=30000)

        return True

    # async def get_new_proxy(self):
    #     self.PROXY = Config.INPUT_PROXIES.get(Config.PROXY_CURSOR)
    #     Config.PROXY_CURSOR += 1
    #
    #     if (not self.PROXY) or (not self.PROXY.available):
    #         return await self.get_new_proxy()

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

        proxy_arg = {"server": f"http://{self.PROXY.host}:{self.PROXY.port}"}
        if self.PROXY.username and self.PROXY.password:
            proxy_arg["username"] = self.PROXY.username
            proxy_arg["password"] = self.PROXY.password

        self.PL_BROWSER = await self.PL_OBJ.chromium.launch(
            headless=bool(Config.HEADLESS), proxy=proxy_arg
        )
        Config.logger.info("Запустил новый браузер")

        self.PL_CONTEXT = await self.PL_BROWSER.new_context(
            locale="ru",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.6367.207 Safari/537.36"
        )
        Config.logger.info("Запустил новый контекст браузера")

        self.PL_PAGE_WORKER = await self.PL_CONTEXT.new_page()
        Config.logger.info("Открыл вкладку WORKER")

        self.PL_PAGE_UTILITY = await self.PL_CONTEXT.new_page()
        Config.logger.info("Открыл вкладку UTILITY")

        return True
