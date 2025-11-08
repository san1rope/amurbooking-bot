from typing import Optional, Union, List
from datetime import datetime

from asyncpg import UniqueViolationError

from config import Config
from .schemas import *


class DbAccount:
    def __init__(
            self, db_id: Optional[int] = None, phone: Optional[str] = None, password: Optional[str] = None,
            proxy: Optional[str] = None, auth_token: Optional[str] = None, is_work: Optional[bool] = None,
            status: Optional[int] = None
    ):
        self.db_id = db_id
        self.phone = phone
        self.password = password
        self.proxy = proxy
        self.auth_token = auth_token
        self.is_work = is_work

    async def add(self) -> Union[Account, None, bool]:
        try:
            target = Account(
                phone=self.phone, password=self.password, proxy=self.proxy, auth_token=self.auth_token,
                is_work=self.is_work
            )
            return await target.create()

        except UniqueViolationError as ex:
            Config.logger.error(ex)
            return False

    async def select(self, proxy_not_none: bool = False) -> Union[Account, List[Account], None, bool]:
        try:
            q = Account.query

            if proxy_not_none:
                return await q.where(Account.proxy.isnot(None)).gino.all()

            if self.db_id is not None:
                return await q.where(Account.id == self.db_id).gino.first()

            if self.phone is not None:
                return await q.where(Account.phone == self.phone).gino.first()

            if self.is_work is not None:
                return await q.where(Account.is_work == self.is_work).gino.all()

            return await q.gino.all()

        except Exception as ex:
            Config.logger.error(ex)
            return False

    async def update(self, **kwargs) -> bool:
        try:
            if not kwargs:
                return False

            target = await self.select()
            return bool(await target.update(**kwargs).apply())

        except Exception as ex:
            Config.logger.error(ex)
            return False

    async def remove(self) -> bool:
        try:
            target = await self.select()
            return bool(await target.delete())

        except Exception as ex:
            Config.logger.error(ex)
            return False


class DbMessageId:
    def __init__(self, db_id: Optional[int] = None, tg_user_id: Optional[int] = None,
                 telegram_id: Optional[int] = None):
        self.db_id = db_id
        self.tg_user_id = tg_user_id
        self.telegram_id = telegram_id

    async def add(self) -> Union[MessageId, bool]:
        try:
            target = MessageId(tg_user_id=self.tg_user_id, telegram_id=self.telegram_id)
            return await target.create()

        except UniqueViolationError as ex:
            Config.logger.error(ex)
            return False

    async def select(self):
        try:
            q = MessageId.query

            if self.db_id:
                return await q.where(MessageId.id == self.db_id).gino.first()

            elif self.tg_user_id:
                return await q.where(MessageId.tg_user_id == self.tg_user_id).gino.all()

            else:
                return await q.gino.all()

        except Exception as ex:
            Config.logger.error(ex)
            return False


class DbBooking:
    def __init__(
            self, db_id: Optional[int] = None, status: Optional[int] = None, truck: Optional[str] = None,
            good_character: Optional[int] = None, book_date: Optional[datetime] = None,
            time_duration: Optional[str] = None, account_id: Optional[int] = None
    ):
        self.db_id = db_id
        self.status = status
        self.account_id = account_id
        self.truck = truck
        self.good_character = good_character
        self.book_date = book_date
        self.time_duration = time_duration

    async def add(self) -> Union[Booking, bool]:
        try:
            target = Booking(status=self.status, truck=self.truck, good_character=self.good_character,
                             book_date=self.book_date, time_duration=self.time_duration, account_id=self.account_id)
            return await target.create()

        except UniqueViolationError as ex:
            Config.logger.error(ex)
            return False

    async def select(self) -> Union[Booking, List[Booking], None, bool]:
        try:
            q = Booking.query
            if self.db_id is not None:
                return await q.where(Booking.id == self.db_id).gino.first()

            if self.status is not None:
                return await q.where(Booking.status == self.status).gino.all()

            if self.account_id is not None:
                return await q.where(Booking.account_id == self.account_id).gino.all()

            return await q.gino.all()

        except Exception as ex:
            Config.logger.error(ex)
            return False

    async def update(self, **kwargs) -> bool:
        try:
            if not kwargs:
                return False

            target = await self.select()
            return bool(await target.update(**kwargs).apply())

        except Exception as ex:
            Config.logger.error(ex)
            return False

    async def remove(self) -> bool:
        try:
            target = await self.select()
            return bool(await target.delete())

        except Exception as ex:
            Config.logger.error(ex)
            return False
