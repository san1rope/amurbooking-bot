import asyncio
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Union, Dict, Optional, List, Any
from multiprocessing import Process

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup

from config import Config
from tg_bot.db_models.quick_commands import DbMessageId
from tg_bot.db_models.schemas import MessageId
from tg_bot.misc.models import ProxyData

BOOKING_PROCESSES: Dict[int, Process] = {}


class Utils:
    PROCESS_STR = "process"
    QUEUE_STR = "queue"
    FOR_STATS_MONITOR = "for_start_monitor"

    STOP_PROCESS = "stop_process"

    @staticmethod
    async def send_step_message(user_id: int, text: str, markup: Optional[InlineKeyboardMarkup] = None):
        await Utils.delete_messages(user_id=user_id)
        msg = await Config.BOT.send_message(chat_id=user_id, text=text, reply_markup=markup,
                                            disable_web_page_preview=True)
        await Utils.add_msg_to_delete(user_id=user_id, msg_id=msg.message_id)

        return msg

    @staticmethod
    async def add_msg_to_delete(user_id: Union[str, int], msg_id: Union[str, int]):
        try:
            await DbMessageId(tg_user_id=user_id, telegram_id=msg_id).add()

        except Exception as ex:
            Config.logger.error(f"Couldn't add msg_id to msg_to_delete\n{ex}")

    @staticmethod
    async def delete_messages(user_id: Optional[int] = None):
        try:
            if user_id:
                db_messages = await DbMessageId(tg_user_id=user_id).select()

            else:
                db_messages = await DbMessageId().select()

            for db_msg in db_messages:
                db_msg: MessageId

                try:
                    await Config.BOT.delete_message(chat_id=db_msg.tg_user_id, message_id=db_msg.telegram_id)

                except TelegramBadRequest:
                    continue

                await db_msg.delete()

        except KeyError:
            return

    @staticmethod
    async def add_logging(process_id: int, datetime_of_start: Union[datetime, str]) -> logging.Logger:
        if isinstance(datetime_of_start, str):
            file_dir = datetime_of_start

        elif isinstance(datetime_of_start, datetime):
            file_dir = datetime_of_start.strftime(Config.DATETIME_FORMAT)

        else:
            raise TypeError("datetime_of_start must be str or datetime")

        log_filepath = Path(os.path.abspath(f"{Config.LOGGING_DIR}/{file_dir}/{process_id}.txt"))
        log_filepath.parent.mkdir(parents=True, exist_ok=True)
        log_filepath.touch(exist_ok=True)

        logger = logging.getLogger()
        if logger.handlers:
            logger.handlers.clear()

        logger.setLevel(logging.INFO)
        logging.getLogger("aiogram.event").setLevel(logging.WARNING)
        logging.getLogger("gino").setLevel(logging.WARNING)
        formatter = logging.Formatter(u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - ' + str(
            process_id) + '| %(message)s')

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        file_handler = logging.FileHandler(log_filepath, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    @staticmethod
    async def load_proxies() -> Dict[str, List[ProxyData]]:
        out_data = {}
        for proxy_type, proxy_filepath in Config.PROXIES_FILEPATH.items():
            proxy_filepath.parent.mkdir(parents=True, exist_ok=True)
            proxy_filepath.touch(exist_ok=True)

            out_data[proxy_type] = []
            with open(proxy_filepath, "r", encoding="utf-8") as file:
                proxies = file.read().split("\n")

                for proxy, proxy_id in zip(proxies, range(1, len(proxies) + 1)):
                    try:
                        host, port, username, password = proxy.split(":")

                    except ValueError:
                        try:
                            host, port = proxy.split(":")
                            username, password = None, None

                        except ValueError:
                            Config.logger.error(f"Прокси указано в неверном формате: {proxy}")
                            continue

                    out_data[proxy_type].append(ProxyData(host=host, port=port, username=username, password=password))

        return out_data

    @staticmethod
    def wrapper(func, *args, **kwargs) -> Any:
        try:
            return asyncio.run(func(*args, **kwargs))

        except KeyboardInterrupt:
            Config.logger.info("Keyboard interrupt: wrapper")
