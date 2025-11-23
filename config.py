import os
from logging import Logger
from pathlib import Path
from typing import Optional, List, Dict

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from pytz import timezone

load_dotenv(dotenv_path=".env")


class Config:
    # AIOHTTP_SESSION = AiohttpSession("http://valetinles:f5bay87SBb@31.59.236.40:59100")

    BOT_TOKEN = os.getenv("BOT_TOKEN").strip()
    BOT = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    DISPATCHER = Dispatcher(storage=MemoryStorage())

    HEADLESS: bool = int(os.getenv("HEADLESS").strip())
    ADMINS = list(map(int, os.getenv("ADMINS").strip().split(",")))
    TIMEZONE = timezone(os.getenv("TIMEZONE").strip())
    USE_PROXY: bool = int(os.getenv("USE_PROXY").strip())
    SHARED_PROXIES_FOR_TASK: int = int(os.getenv("SHARED_PROXIES_FOR_TASK").strip())

    INPUT_PROXIES: Optional[Dict[str, List]] = {}
    PRIVATE_PROXIES = "private"
    SHARED_PROXIES = "shared"
    PROXIES_FILEPATH = {
        SHARED_PROXIES: Path(os.path.abspath("proxies_shared.txt")),
        PRIVATE_PROXIES: Path(os.path.abspath("proxies_private.txt"))
    }

    logger: Optional[Logger] = None
    LOGGING_DIR = Path(os.path.abspath("logs"))
    DATETIME_FORMAT = "%d-%m-%Y_%H-%M-%S"

    DATABASE_CLEANUP = bool(int(os.getenv("DATABASE_CLEANUP")))
    DB_USER = os.getenv("DB_USER").strip()
    DB_PASSWORD = os.getenv("DB_PASSWORD").strip()
    DB_HOST = os.getenv("DB_HOST").strip()
    DB_NAME = os.getenv("DB_NAME").strip()

    GOOD_CHARACTERS = {
        1: "Опасный",
        2: "Скоропортящийся",
        3: "Иной нережимный груз"
    }

    BOOKING_STATUSES = {
        0: "Выключена",
        1: "В работе",
        2: "Выполнена",
        3: "Не удалось поймать"
    }

    SHARED_DATA = None
