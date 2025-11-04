import asyncio
import base64
import json
import time

from aiohttp import ClientSession, BasicAuth
from playwright.async_api import async_playwright
from playwright_stealth import Stealth


async def account_auth():
    pass


async def check_account_auth():
    pass


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            proxy={
                "server": "http://31.59.236.40:59100",
                "username": "valetinles",
                "password": "f5bay87SBb"
            }
        )

        context = await browser.new_context(
            locale="ru",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/124.0.6367.207 Safari/537.36"
        )
        page = await context.new_page()
        await page.set_viewport_size(viewport_size={
            "width": 800,
            "height": 600
        })
        await Stealth().apply_stealth_async(page)

        await page.goto("https://amurbooking.com/user/login", timeout=20000)
        locator = page.locator('oktet-phone-input#username input[type="text"]')
        await locator.wait_for(state='visible', timeout=2500)
        await locator.fill("+79638042595")

        password_input = page.locator('oktet-password-input#password input[type="password"]')
        await password_input.wait_for(state="visible", timeout=2500)
        await password_input.fill("VovanR797$")

        button = page.locator("button.px-4")
        await button.wait_for(state="visible", timeout=2500)
        await button.click()

        await page.wait_for_selector(".btn-lg", timeout=30000)

        # 2 STEP

        await page.locator(".btn-lg").first.click(timeout=10000)
        await page.locator(".datepicker-input").wait_for(state="attached", timeout=30000)

        await page.locator(".ng-input").first.click()
        await page.locator(".ng-option").first.click()
        await page.locator("#cargoType").click()

        await page.wait_for_selector("xpath=//*[contains(normalize-space(), 'Опасный')]", timeout=15000)

        # STEP 3
        await page.get_by_text("Опасный").click()

        datepicker = page.locator(".datepicker-input")
        while True:
            print("iter")
            await datepicker.fill("13.11.2025")

            try:
                locator = page.locator(".time-item__btn.outline-success")
                await locator.first.wait_for(state="attached", timeout=2000)
                print("FOUND")

                elements = await locator.all()
                for el in elements:
                    print(await el.text_content())

                break

            except Exception as ex:
                print(ex)
                await datepicker.fill("")
                await asyncio.sleep(0.1)

        await page.locator(".form-control--time").click()

        try:
            await page.wait_for_selector(".select-time", state="attached", timeout=5000)

        except Exception as ex:
            print(ex)
            return

        locator_os = page.locator(".outline-success")
        await locator_os.first.click()

        await page.locator(".form-footer .btn-primary").click()

        # STEP 4
        try:
            # 1. Дочекатись, поки iframe зʼявиться в DOM
            await page.wait_for_selector("iframe[data-testid='checkbox-iframe']", timeout=15_000)
        except Exception:
            print("⏳ Не дочекались iframe протягом 15 секунд")
            return

            # 2. Працюємо через frame_locator — тепер він точно існує
        frame_loc = page.frame_locator("iframe[data-testid='checkbox-iframe']")

        slider = frame_loc.locator(".Thumb")
        track = frame_loc.locator(".Track")

        await slider.wait_for(state="visible", timeout=10_000)
        await track.wait_for(state="visible", timeout=10_000)

        sbb = await slider.bounding_box()
        tbb = await track.bounding_box()

        if not sbb or not tbb:
            print("Не вдалося отримати геометрію")
            return

        print(f"sbb = {sbb}")
        print(f"tbb = {tbb}")

        # STEP 5
        sx = sbb["x"] + sbb["width"] / 2
        sy = sbb["y"] + sbb["height"] / 2
        tx = tbb["x"] + tbb["width"] - 2
        ty = sy

        # await page.pause()
        # print("PAUSE")

        await asyncio.sleep(1)

        await page.mouse.move(sx, sy)
        await page.mouse.down()
        await page.mouse.move(tx, ty, steps=20)
        await page.mouse.up()

        # STEP 6

        try:
            # 1) Дочекатись, поки iframe зʼявиться в DOM
            await page.wait_for_selector('iframe[data-testid="advanced-iframe"]', timeout=15_000)
        except Exception:
            print("⏳ Не дочекались advanced-iframe протягом 15 секунд")
            return False

            # 2) Отримати об'єкт Frame (реальний), щоб працювати всередині
        iframe_el = await page.query_selector('iframe[data-testid="advanced-iframe"]')
        frame = await iframe_el.content_frame()
        if frame is None:
            print("❌ Не вдалося отримати content_frame()")
            return False

        while True:
            # 3) Дочекатись області з капчею
            try:
                view = frame.locator(".AdvancedCaptcha-View")
                await view.wait_for(state="visible", timeout=15_000)
            except Exception:
                print("⏳ Не дочекались .AdvancedCaptcha-View")
                return False

            # 4) Дістати URL картинки капчі
            img = view.locator("img")
            src = await img.get_attribute("src")
            if not src:
                print("❌ Не знайшов src для картинки капчі")
                return False

            # 5) Завантажити картинку та відправити на RuCaptcha
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

                # 6) Опитування результату
                params_get = {"key": "bfcac84dd8e6d4df3bd114d93ede4f51", "action": "get", "id": req_id, "json": 1}
                captcha_result = None
                for _ in range(500):  # до ~24 секунд при sleep(0.2)
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

            # 7) Ввести відповідь і натиснути кнопку
            #    id="xuniq-0-1" — якщо id динамічний, краще селектором по типу/placeholder.
            input_box = frame.locator("#xuniq-0-1")
            await input_box.wait_for(state="visible", timeout=5_000)
            await input_box.fill(captcha_result)

            submit_btn = frame.locator(".CaptchaButton-ProgressWrapper")
            await submit_btn.click()

            # 8) Перевірити, чи зникла/сховалась підказка (як у твоєму коді з Selenium)
            #    Якщо .Textinput-Hint відображається з style, де є 'hidden', — вважаємо що пройшло.
            hint = frame.locator(".Textinput-Hint")
            try:
                # дочекаємось появи хінта у DOM (може бути hidden)
                await hint.wait_for(state="attached", timeout=5_000)
                style = await hint.get_attribute("style") or ""
                if "hidden" in style:
                    # успіх — капча пройдена
                    break
                else:
                    # інакше повторити цикл (може, відповідь не підійшла і зʼявився новий img src)
                    continue
            except Exception:
                # Якщо хінт не зʼявився — теж вважаємо успішним (як у твоєму except)
                break

        input("close? ")

        await context.close()
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
