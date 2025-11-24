import asyncio
import base64
import json
import traceback
from asyncio import CancelledError, Future
from copy import deepcopy
from random import uniform
from typing import Optional, List, Union, Dict
from datetime import datetime, timedelta

from aiohttp import ClientSession, BasicAuth
from playwright.async_api import Page, Browser, async_playwright
from pydantic import ValidationError

from config import Config
from tg_bot.db_models.db_gino import connect_to_db
from tg_bot.db_models.quick_commands import DbAccount, DbBooking
from tg_bot.db_models.schemas import Booking
from tg_bot.misc.models import ProxyData, WorkTypes, BookingSlot
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
    SHARED_DATA = None
    SHARED_PROXIES: Optional[List[ProxyData]] = None
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

    def __init__(self, shared_data, work_type: str, account_id: Optional[int], shared_proxies: List[ProxyData] = None):
        self.ACCOUNT_ID = account_id
        self.WORK_TYPE = work_type
        self.SHARED_DATA = shared_data
        self.SHARED_PROXIES = shared_proxies

    async def run_task(self):
        proxies = await Ut.load_proxies()
        Config.INPUT_PROXIES = proxies

        self.AIOHTTP_SESSION = ClientSession()
        if self.SHARED_DATA:
            self.SHARED_DATA[Ut.FOR_STATS_MONITOR] = {self.ACCOUNT_ID: None}

            datetime_of_start = datetime.now(tz=Config.TIMEZONE).strftime(Config.DATETIME_FORMAT)
            logger = await Ut.add_logging(datetime_of_start=datetime_of_start, process_id=self.ACCOUNT_ID)
            Config.logger = logger

            try:
                await connect_to_db(remove_data=False)

            except Exception:
                print(traceback.format_exc())
                return

        db_account = await DbAccount(db_id=self.ACCOUNT_ID).select()
        if not db_account:
            return Config.logger.error("Не нашел аккаунта в бд! Завершаю работу...")

        flag = True
        if db_account.proxy:
            for i in Config.INPUT_PROXIES[Config.PRIVATE_PROXIES]:
                if str(db_account.proxy) == str(i):
                    flag = False
                    break

        if flag:
            Config.logger.info("Ищу новый PRIVATE прокси...")
            selected_proxy = await Ut.get_new_proxy_to_account(account_id=self.ACCOUNT_ID)
            if not selected_proxy:
                return Config.logger.critical("Не нашел свободных PRIVATE прокси! Завершаю работу...")

            result = await DbAccount(db_id=db_account.id).update(proxy=str(selected_proxy))
            if not result:
                return Config.logger.error("Не удалось обновить proxy в accounts! Завершаю работу")

            Config.logger.info(f"Успешо сменил PRIVATE прокси на {selected_proxy}!")

        self.ACCOUNT_PHONE = db_account.phone
        self.ACCOUNT_PASSWORD = db_account.password
        self.ACCOUNT_AUTH_TOKEN = db_account.auth_token

        host, port, username, password = db_account.proxy.split(":")
        self.ACCOUNT_PROXY = ProxyData(host=host, port=port, username=username, password=password)

        if self.WORK_TYPE == WorkTypes.GET_TRUCKS_LIST:
            result = await self.get_trucks_info()
            try:
                await self.AIOHTTP_SESSION.close()

            except Exception as ex:
                Config.logger.warning(f"Не удалось успешно закрыть AIOHTTP SESSION!\nex: {ex}")

            return result

        elif self.WORK_TYPE == WorkTypes.BOOKING_PROCESSING:
            if not self.SHARED_PROXIES:
                return Config.logger.critical("Не поступило SHARED PROXIES для мониторинга слотов! Завершаю работу...")

            loop = asyncio.get_event_loop()
            self.ASYNCIO_TASK = loop.create_task(self.processing_booking())
            return await self.messages_checker()

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

            result = await self.get_trucks_info()
            if not result:
                Config.logger.error(f"Не удалось сделать тестовый запрос о грозувиках!\nОтвет: {result}")
                raise CancelledError()

            result = await self.get_new_browser_obj()
            if not result:
                Config.logger.error("Не удалось запустить браузер! Завершаю работу...")
                raise CancelledError()

            result = await self.add_auth_token_to_local_storage()
            if not result:
                Config.logger.error("Не удалось добавить токен в local_storage! Завершаю работу...")
                raise CancelledError()

            result = await self.actions_to_slots_monitoring()
            if not result:
                Config.logger.error("Не удалось выполнить действия по форме до SLOTS_MONITORING! Завершаю работу...")
                raise CancelledError()

            selected_time_text = await self.slots_monitoring()

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

            sx = sbb["x"] + sbb["width"] / 2
            sy = sbb["y"] + sbb["height"] / 2
            tx = tbb["x"] + tbb["width"] - 2
            ty = sy

            await asyncio.sleep(uniform(1, 1.1))

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
                        with open("index.html", "w", encoding="utf-8") as file:
                            file.write(await self.PL_PAGE.content())

                        break

                    else:
                        continue

                except Exception:
                    break

            print("готовлюсь тыкать по отправить!")
            button_locator = self.PL_PAGE.locator(".form-footer .btn-primary")
            print("скроллю!")
            await button_locator.scroll_into_view_if_needed(timeout=10_000)
            await button_locator.wait_for(state="visible", timeout=30000)
            print("дождался!")
            await asyncio.sleep(uniform(0.2, 0.25))
            # await button_locator.click(timeout=5_000)
            print("кликнул!")

            print("ПОЙМАЛ ")

            for uid in Config.ADMINS:
                try:
                    await Config.BOT.send_message(chat_id=uid, text=f"ПОЙМАЛ booking = {db_booking.id}")

                except Exception:
                    print(f"не смог отправить сообщение {uid}")

            await DbBooking(db_id=db_booking.id).update(status=2)
            raise CancelledError()

        except CancelledError:
            await self.close_session_objects()

            self.FLAG_CANCEL_COMPLETE = True
            Config.logger.info("Завершил задачу!")

        except Exception:
            Config.logger.critical(traceback.format_exc())

            await self.PL_PAGE.screenshot(path="temp421.png")

            print("sleep")
            while True:
                await asyncio.sleep(1000)

    async def actions_to_slots_monitoring(self, retries: int = 3) -> bool:
        try:
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

            return True

        except Exception as ex:
            Config.logger.error(f"Не удалось выполнить действия до SLOTS_MONITORING! Попыток: {retries}\nex: {ex}")

            if retries:
                await asyncio.sleep(3)
                return await self.actions_to_slots_monitoring(retries=retries - 1)

        return False

    async def slots_monitoring(self) -> str:
        start_tr = self.BOOKING_OBJ.book_date
        end_tr = self.BOOKING_OBJ.book_date + timedelta(minutes=self.BOOKING_OBJ.time_duration)

        while True:
            for proxy in self.SHARED_PROXIES:
                await asyncio.sleep(0.1)

                result = await self.get_slots_data(proxy=proxy)
                if not result:
                    continue

                for slot_info in result:
                    try:
                        if slot_info.availableToBook and start_tr <= slot_info.dateBooked <= end_tr:
                            selected_time_text = slot_info.dateBooked.strftime("%H:%M")
                            return selected_time_text

                    except Exception as ex:
                        Config.logger.warning(f"Не удалось сравнить даты! ex: {ex}")

    async def get_slots_data(self, proxy: ProxyData, retries: int = 3) -> Union[List[BookingSlot], bool]:
        headers = deepcopy(self.DEFAULT_HEADERS)
        headers["referer"] = "https://amurbooking.com/booking"

        date = self.BOOKING_OBJ.book_date.strftime("%Y-%m-%d")

        try:
            async with self.AIOHTTP_SESSION.get(
                    url=f"https://amurbooking.com/oktet/api/v1/booking/time-slots?date={date}",
                    headers=headers,
                    proxy=f"http://{proxy.host}:{proxy.port}",
                    proxy_auth=BasicAuth(login=proxy.username, password=proxy.password) if proxy.username else None,
                    timeout=20
            ) as response:
                answer = await self.processing_response(response=response, prefix="slots")
                if not answer:
                    raise Exception("Answer is False!")

                try:
                    validated_slots: List[BookingSlot] = [BookingSlot.model_validate(item) for item in answer]

                    Config.logger.info("Получил данные о времени!")
                    return validated_slots

                except ValidationError as ex:
                    Config.logger.error(f"Ответ с данных о времени не прошел валидацию! ex: {ex}")
                    raise Exception("Answer hasn't been validated!")

        except Exception as ex:
            Config.logger.error(f"Не удалось получить данные о слотах! Попыток: {retries}\nex: {ex}")

            if retries:
                await asyncio.sleep(5)
                return await self.get_slots_data(proxy=proxy, retries=retries - 1)

        return False

    async def get_trucks_info(self, retries: int = 3) -> Union[List[str], bool]:
        headers = deepcopy(self.DEFAULT_HEADERS)
        headers["referer"] = "https://amurbooking.com/lk"

        if not self.ACCOUNT_AUTH_TOKEN:
            if not await self.auth():
                return False

        headers["authorization"] = self.ACCOUNT_AUTH_TOKEN

        try:
            async with self.AIOHTTP_SESSION.get(
                    url="https://amurbooking.com/oktet/api/v1/vehicle/current-user?page=0&size=10&sort=model,ASC",
                    headers=headers,
                    proxy=f"http://{self.ACCOUNT_PROXY.host}:{self.ACCOUNT_PROXY.port}",
                    proxy_auth=BasicAuth(login=self.ACCOUNT_PROXY.username, password=self.ACCOUNT_PROXY.password) \
                            if self.ACCOUNT_PROXY.username else None,
                    timeout=20
            ) as response:
                answer = await self.processing_response(response=response, prefix="trucks")
                if not answer:
                    raise Exception("Answer is False!")

                return [f"{car_data['model']} / {car_data['registrationPlate']}" for car_data in answer["content"]]

        except Exception as ex:
            Config.logger.error(f"Не удалось получить данные о грузовиках! Попыток: {retries}\nex: {traceback.format_exc()}")

            if retries:
                await asyncio.sleep(5)
                return await self.get_trucks_info(retries=retries - 1)

        return False

    async def processing_response(self, response, prefix: str) -> Union[Dict, bool]:
        if response.status == 200:
            try:
                return json.loads(await response.text())

            except Exception as ex:
                Config.logger.error(f"{prefix} | Не смог подгрузить JSON ответ!")

        elif response.status == 401:
            Config.logger.error(f"{prefix} | Статус код ответа - 401! Пробую пройти авторизацию...")
            await self.auth()

        else:
            Config.logger.error(f"{prefix} | Статус код ответа - {response.status}!")

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

    async def add_auth_token_to_local_storage(self, retries: int = 3) -> bool:
        try:
            await self.PL_PAGE.goto("https://amurbooking.com/")
            await self.PL_PAGE.evaluate(
                "({ key, value }) => localStorage.setItem(key, value)",
                {"key": "oktet-auth-token", "value": self.ACCOUNT_AUTH_TOKEN}
            )
            await asyncio.sleep(uniform(1, 2))

            return True

        except Exception as ex:
            Config.logger.error(f"Не удалось добавить токен в local storage! Попыток: {retries}\nex: {ex}")

            if retries:
                return await self.add_auth_token_to_local_storage(retries=retries - 1)

            return False

    async def get_new_browser_obj(self, retries: int = 3) -> bool:
        Config.logger.info("Пробую получить новый браузер...")

        await self.close_session_objects()

        try:
            self.AIOHTTP_SESSION = ClientSession()

            self.PL_OBJ = await async_playwright().start()
            Config.logger.info("Запустил новый экземпляр playwright_obj")

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

        except Exception as ex:
            Config.logger.error(f"Не удалось получить новый браузер! Попыток: {retries}\nex: {ex}")
            if retries:
                return await self.get_new_browser_obj(retries=retries - 1)

            return False

    async def messages_checker(self):
        Config.logger.info(f"Чекер сообщений запущен! Процесс обработки записи №")

        while True:
            await asyncio.sleep(0.1)

            messages = self.SHARED_DATA.get(self.ACCOUNT_ID)
            if not messages:
                continue

            s_msg = messages[0]

            Config.logger.info(f"Получил queue message в процесс обработки записи №")
            if s_msg.msg_type == Ut.STOP_PROCESS:
                Config.logger.info("Останавливаю процесс...")

                if not self.ASYNCIO_TASK.done():
                    self.ASYNCIO_TASK.cancel()

                while not self.FLAG_CANCEL_COMPLETE:
                    Config.logger.info("Ожидаю закрытия сессий...")
                    await asyncio.sleep(1)

                self.SHARED_DATA.pop(self.ACCOUNT_ID)
                return None

    async def close_session_objects(self):
        if self.PL_BROWSER is not None:
            try:
                await self.PL_BROWSER.close()
                Config.logger.info("Закрыл старый браузер")

            except Exception as ex:
                Config.logger.warning(f"Не удалось закрыть PL_BROWSER. ex: {ex}")

        if self.PL_OBJ is not None:
            try:
                await self.PL_OBJ.stop()
                Config.logger.info("Остановил старый playwright_obj")

            except Exception as ex:
                Config.logger.warning(f"Не удалось остановить PL_OBJ. ex: {ex}")

        if self.AIOHTTP_SESSION:
            try:
                await self.AIOHTTP_SESSION.close()

            except Exception as ex:
                Config.logger.warning(f"Ошибка при закрытии AIOHTTP сессии! ex: {ex}")

    @staticmethod
    async def send_log_to_tg(log_text: str):
        for uid in Config.ADMINS:
            try:
                text = [
                    f"\n<b>{log_text}</b>"
                ]
                await Config.BOT.send_message(chat_id=uid, text="\n".join(text))

            except Exception as ex:
                Config.logger.warning(f"Не удалось прислать лог в телеграм! user_id={uid}\n{ex}")
