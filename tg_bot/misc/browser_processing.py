import asyncio
import base64
import json
import time
import traceback
from asyncio import CancelledError, Future
from copy import deepcopy
from multiprocessing.queues import Queue
from random import uniform
from typing import Optional
from datetime import datetime, timedelta

from aiohttp import ClientSession, BasicAuth
from playwright.async_api import Page, Browser, async_playwright

from config import Config
from tg_bot.db_models.db_gino import connect_to_db
from tg_bot.db_models.quick_commands import DbAccount, DbBooking
from tg_bot.db_models.schemas import Booking
from tg_bot.misc.models import ProxyData, WorkTypes
from tg_bot.misc.utils import Utils as Ut


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
    PROCESS_QUEUE: Optional[Queue] = None
    ASYNCIO_TASK: Optional[Future] = None
    FLAG_CANCEL_COMPLETE: bool = False

    ACCOUNT_ID: Optional[int] = None
    ACCOUNT_PHONE: Optional[str] = None
    ACCOUNT_PASSWORD: Optional[str] = None
    ACCOUNT_AUTH_TOKEN: Optional[str] = None
    ACCOUNT_PROXY: Optional[ProxyData] = None
    BOOKING_OBJ: Optional[Booking] = None

    WORK_TYPE: Optional[str] = None

    PL_OBJ = None
    PL_BROWSER: Optional[Browser] = None
    PL_CONTEXT = None
    PL_PAGE: Optional[Page] = None

    def __init__(self, work_type: str, account_id: Optional[int], process_queue: Optional[Queue] = None):
        self.ACCOUNT_ID = account_id
        self.WORK_TYPE = work_type
        self.PROCESS_QUEUE = process_queue

    async def run_task(self):
        self.AIOHTTP_SESSION = ClientSession()
        if self.PROCESS_QUEUE:
            datetime_of_start = datetime.now(tz=Config.TIMEZONE).strftime(Config.DATETIME_FORMAT)
            logger = await Ut.add_logging(datetime_of_start=datetime_of_start, process_id=0)
            Config.logger = logger

            await connect_to_db(remove_data=False)

        db_account = await DbAccount(db_id=self.ACCOUNT_ID).select()
        self.ACCOUNT_PHONE = db_account.phone
        self.ACCOUNT_PASSWORD = db_account.password
        self.ACCOUNT_AUTH_TOKEN = db_account.auth_token

        host, port, username, password = db_account.proxy.split(":")
        self.ACCOUNT_PROXY = ProxyData(host=host, port=port, username=username, password=password)

        if self.WORK_TYPE == WorkTypes.GET_TRUCKS_LIST:
            return await self.get_trucks_info()

        elif self.WORK_TYPE == WorkTypes.BOOKING_PROCESSING:
            loop = asyncio.get_event_loop()
            self.ASYNCIO_TASK = loop.create_task(self.processing_booking())
            return await self.queue_messages_checker()

        else:
            return None

    async def processing_booking(self):
        try:
            db_booking = await DbBooking(status=1, account_id=self.ACCOUNT_ID).select()
            self.BOOKING_OBJ = db_booking
            if not db_booking:
                raise CancelledError()

            db_booking = db_booking[0]
            self.BOOKING_OBJ = db_booking

            result = await self.get_booking_data_per_day()
            if (not result) or ("availableToBook" not in result[0]):
                return Config.logger.error(f"Не удалось получить данные о времени!\nОтвет: {result}")

            await self.get_new_browser_obj()
            await self.PL_PAGE.goto("https://amurbooking.com/")
            await self.PL_PAGE.evaluate(
                "({ key, value }) => localStorage.setItem(key, value)",
                {"key": "oktet-auth-token", "value": self.ACCOUNT_AUTH_TOKEN}
            )
            await asyncio.sleep(uniform(1, 2))
            await self.PL_PAGE.goto("https://amurbooking.com/booking")

            await self.PL_PAGE.wait_for_selector(".btn-lg", timeout=30000)
            await self.PL_PAGE.locator(".btn-lg").first.click(timeout=10000)
            await self.PL_PAGE.locator(".datepicker-input").wait_for(state="attached", timeout=30000)

            await self.PL_PAGE.locator(".ng-input").first.click()
            await self.PL_PAGE.get_by_text(self.BOOKING_OBJ.truck).click()

            await self.PL_PAGE.locator("#cargoType").click()
            await self.PL_PAGE.wait_for_selector(
                f"xpath=//*[contains(normalize-space(), '{Config.GOOD_CHARACTERS[self.BOOKING_OBJ.good_character]}')]",
                timeout=15000
            )
            await self.PL_PAGE.get_by_text(Config.GOOD_CHARACTERS[self.BOOKING_OBJ.good_character]).click()

            await self.PL_PAGE.locator(".datepicker-input").click()

            start_tr = self.BOOKING_OBJ.book_date  # start time range
            end_tr = self.BOOKING_OBJ.book_date + timedelta(minutes=self.BOOKING_OBJ.time_duration)  # end time range
            selected_time_text = ""
            while True:
                print("request")
                await asyncio.sleep(uniform(0.300, 0.500))
                result = await self.get_booking_data_per_day()
                if not result:
                    continue

                flag = False
                for time_info in result:
                    time_info_dt = datetime.strptime(time_info['dateBooked'], "%Y-%m-%dT%H:%M:%S")
                    if time_info["availableToBook"] and start_tr <= time_info_dt <= end_tr:
                        selected_time_text = time_info_dt.strftime("%H:%M")
                        flag = True
                        break

                if flag:
                    break

            await self.PL_PAGE.locator(".datepicker-input").fill(self.BOOKING_OBJ.book_date.strftime("%d.%m.%Y"))
            await self.PL_PAGE.locator(".form-control--time").click()
            await self.PL_PAGE.wait_for_selector(".select-time", state="attached", timeout=5000)
            await self.PL_PAGE.get_by_text(selected_time_text).click()

            await self.PL_PAGE.locator(".form-footer .btn-primary").click()

            await self.PL_PAGE.wait_for_selector("iframe[data-testid='checkbox-iframe']", timeout=15000)
            frame_loc = self.PL_PAGE.frame_locator("iframe[data-testid='checkbox-iframe']")

            slider = frame_loc.locator(".Thumb")
            track = frame_loc.locator(".Track")

            await slider.wait_for(state="visible", timeout=10_000)
            await track.wait_for(state="visible", timeout=10_000)

            sbb = await slider.bounding_box()
            tbb = await track.bounding_box()

            print(f"sbb = {sbb}")
            print(f"tbb = {tbb}")

            sx = sbb["x"] + sbb["width"] / 2
            sy = sbb["y"] + sbb["height"] / 2
            tx = tbb["x"] + tbb["width"] - 2
            ty = sy

            await asyncio.sleep(1)

            await self.PL_PAGE.mouse.move(sx, sy)
            await self.PL_PAGE.mouse.down()
            await self.PL_PAGE.mouse.move(tx, ty, steps=20)
            await self.PL_PAGE.mouse.up()

            await self.PL_PAGE.wait_for_selector('iframe[data-testid="advanced-iframe"]', timeout=15000)
            iframe_el = await self.PL_PAGE.query_selector('iframe[data-testid="advanced-iframe"]')
            frame = await iframe_el.content_frame()

            while True:
                try:
                    view = frame.locator(".AdvancedCaptcha-View")
                    await view.wait_for(state="visible", timeout=15_000)
                except Exception:
                    print("⏳ Не дочекались .AdvancedCaptcha-View")
                    return False

                img = view.locator("img")
                src = await img.get_attribute("src")
                if not src:
                    print("❌ Не знайшов src для картинки капчі")
                    return False

                async with ClientSession() as session:
                    proxy = "http://31.59.236.40:59100"
                    proxy_auth = BasicAuth("valetinles", "f5bay87SBb")
                    async with session.get(url=src, proxy=proxy, proxy_auth=proxy_auth) as resp:
                        img_bytes = await resp.read()
                    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

                    data_post = {
                        "key": "bfcac84dd8e6d4df3bd114d93ede4f51",
                        "method": "base64",
                        "body": img_b64,
                        "phrase": 1,
                        "regsense": 0,
                        "numeric": 2,
                        "lang": "ru",
                        "json": 1,
                    }
                    async with session.post("http://rucaptcha.com/in.php", json=data_post) as resp:
                        answer_text = await resp.text()
                        print(answer_text)
                        post_answer = json.loads(answer_text)

                    if post_answer.get("status") != 1:
                        print("❌ RuCaptcha in.php error:", post_answer)
                        return False

                    req_id = post_answer.get("request")

                    params_get = {"key": "bfcac84dd8e6d4df3bd114d93ede4f51", "action": "get", "id": req_id, "json": 1}
                    captcha_result = None
                    for _ in range(500):
                        await asyncio.sleep(0.2)
                        async with session.get("http://rucaptcha.com/res.php", params=params_get) as resp:
                            answer_text = await resp.text()
                            print(answer_text)
                            get_answer = json.loads(answer_text)

                        if get_answer.get("status") == 1:
                            captcha_result = get_answer.get("request")
                            break

                    if not captcha_result:
                        print("❌ Не отримали відповідь RuCaptcha вчасно")
                        return False

                print("captcha_result", captcha_result)

                input_box = frame.locator("#xuniq-0-1")
                await input_box.wait_for(state="visible", timeout=5_000)
                await input_box.fill(captcha_result)

                submit_btn = frame.locator(".CaptchaButton-ProgressWrapper")
                await submit_btn.click()

                hint = frame.locator(".Textinput-Hint")
                try:
                    await hint.wait_for(state="attached", timeout=5_000)
                    style = await hint.get_attribute("style") or ""
                    if "hidden" in style:
                        break

                    else:
                        continue

                except Exception:
                    break

            print("wait 1542")
            button_locator = self.PL_PAGE.locator(".form-footer .btn-primary")
            await button_locator.click(timeout=0)

            print("ПОЙМАЛ")
            await self.PL_PAGE.screenshot(path="temp124.png")

            for uid in Config.ADMINS:
                try:
                    await Config.BOT.send_message(chat_id=uid, text="ПОЙМАЛ")

                except Exception:
                    print(f"не смог отправить сообщение {uid}")

            print("sleep")
            while True:
                time.sleep(1000)

        except CancelledError:
            if self.PL_BROWSER:
                await self.PL_BROWSER.close()

            if self.PL_OBJ:
                await self.PL_OBJ.stop()

            if self.AIOHTTP_SESSION:
                await self.AIOHTTP_SESSION.close()

            self.FLAG_CANCEL_COMPLETE = True
            Config.logger.info("Успешно завершил задачу!")

        except Exception:
            print(traceback.format_exc())

            print("sleep")
            while True:
                time.sleep(1000)

    async def send_log_to_tg(self, log_text: str):
        for uid in Config.ADMINS:
            try:
                text = [
                    f"\n<b>{log_text}</b>"
                ]
                await Config.BOT.send_message(chat_id=uid, text="\n".join(text))

            except Exception as ex:
                Config.logger.warning(f"Не удалось прислать лог в телеграм! user_id={uid}\n{ex}")

    async def get_booking_data_per_day(self, retries: int = 3):
        headers = deepcopy(self.DEFAULT_HEADERS)
        headers["referer"] = "https://amurbooking.com/booking"

        if not self.ACCOUNT_AUTH_TOKEN:
            if not await self.auth():
                return False

        headers["authorization"] = self.ACCOUNT_AUTH_TOKEN
        date = self.BOOKING_OBJ.book_date.strftime("%Y-%m-%d")

        print(f"date = {date}")

        async with self.AIOHTTP_SESSION.get(
                url=f"https://amurbooking.com/oktet/api/v1/booking/time-slots?date={date}",
                headers=headers,
                proxy=f"http://{self.ACCOUNT_PROXY.host}:{self.ACCOUNT_PROXY.port}",
                proxy_auth=BasicAuth(login=self.ACCOUNT_PROXY.username, password=self.ACCOUNT_PROXY.password) \
                        if self.ACCOUNT_PROXY.username else None,
                timeout=20
        ) as response:
            print(await response.text())
            if response.status == 200:
                return json.loads(await response.text())

            elif response.status == 401:
                Config.logger.error(f"Не удалось получить данные о времени! Пробую пройти авторизацию...\n")
                await self.auth()

            else:
                Config.logger.error(
                    f"Не удалось получить данные о временеи!"
                    f"\nкод={response.status}\nответ: {await response.text()}"
                )

            if retries:
                await asyncio.sleep(5)
                return await self.get_booking_data_per_day(retries=retries - 1)

            Config.logger.error(
                f"Попытки для получения данных о времени закончились!"
                f"\nкод={response.status}\nответ: {await response.text()}"
            )
            return False

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
                await self.AIOHTTP_SESSION.close()
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
            await self.AIOHTTP_SESSION.close()
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

                    print(f"auth_token = {auth_token}")
                    Config.logger.info(f"Успешно вошел в аккаунт №{self.ACCOUNT_ID}!")
                    return auth_token  # temp

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

    async def queue_messages_checker(self):
        Config.logger.info(f"Чекер сообщений запущен! Процесс обработки записи №")

        while True:
            await asyncio.sleep(0.5)

            msg = await Ut.get_message_from_queue(self.PROCESS_QUEUE)
            if msg is None:
                continue

            Config.logger.info(f"Получил queue message в процесс обработки записи №")
            if msg.msg_type == Ut.STOP_PROCESS:
                Config.logger.info("Останавливаю процесс...")

                if not self.ASYNCIO_TASK.done():
                    self.ASYNCIO_TASK.cancel()

                while not self.FLAG_CANCEL_COMPLETE:
                    Config.logger.info("Ожидаю закрытия сессий...")
                    await asyncio.sleep(1)

                return None
