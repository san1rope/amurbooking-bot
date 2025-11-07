from calendar import Calendar
from typing import List, Optional
from datetime import datetime

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Config


class CustomCallback(CallbackData, prefix="cc"):
    role: str
    data: str


class InlineMarkups:
    back_to_menu_btn = InlineKeyboardButton(text="⌨️ В меню", callback_data="back_to_menu")
    add_account_btn = InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="add_account")
    move_to_accounts_list_btn = InlineKeyboardButton(text="В список аккаунтов", callback_data="move_to_accounts_list")
    add_booking_btn = InlineKeyboardButton(text="➕ Добавить заявку", callback_data="add_booking")
    select_first_half_day_btn = InlineKeyboardButton(
        text="9:00 - 12:00", callback_data=CustomCallback(role="select_time", data="9:00_180").pack())
    select_second_half_day_btn = InlineKeyboardButton(
        text="12:05 - 21:40", callback_data=CustomCallback(role="select_time", data="12:05_575").pack())

    @staticmethod
    async def calendar(date_time: datetime) -> InlineKeyboardMarkup:
        weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
        months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь",
                  "Ноябрь", "Декабрь"]

        markup = InlineKeyboardMarkup(inline_keyboard=[])
        markup.inline_keyboard.append([
            InlineKeyboardButton(text=btn_text, callback_data="0") for btn_text in weekdays])

        today = datetime.now(tz=Config.TIMEZONE)

        month_days = list(Calendar().itermonthdays(year=date_time.year, month=date_time.month))
        for day, counter in zip(month_days, range(len(month_days))):
            if counter % 7 == 0:
                markup.inline_keyboard.append([])

            if (day == 0) or (
                    (today.year == date_time.year and today.month == date_time.month) and day < date_time.day):
                new_btn = InlineKeyboardButton(text=" ", callback_data="0")

            else:
                new_btn = InlineKeyboardButton(text=str(day), callback_data=f"{day}.{date_time.month}.{date_time.year}")

            markup.inline_keyboard[-1].append(new_btn)

        temp_month = date_time.month + 1
        temp_year = date_time.year

        if temp_month > 12:
            temp_month = 1
            temp_year += 1

        right = InlineKeyboardButton(text="➡️", callback_data=f"r:1.{temp_month}.{temp_year}")

        # For button - Previous Month
        if date_time.month == today.month and date_time.year == today.year:
            left_cd = "0"

        else:
            temp_month = date_time.month - 1
            temp_year = date_time.year

            if temp_month < 1:
                temp_month = 12
                temp_year -= 1

            left_cd = f"l:1.{temp_month}.{temp_year}"

        left = InlineKeyboardButton(text="⬅️", callback_data=left_cd)

        month = months[date_time.month - 1]
        current_month = InlineKeyboardButton(text=f"{month} {date_time.year}", callback_data="0")

        markup.inline_keyboard.append([left, current_month, right])
        markup.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back")])
        return markup

    @staticmethod
    async def universal_btn(callback_data: str, btn_text, custom_data: Optional[str] = None) -> InlineKeyboardButton:
        if custom_data:
            callback_data = CustomCallback(role=callback_data, data=str(custom_data)).pack()

        return InlineKeyboardButton(text=btn_text, callback_data=callback_data)

    @staticmethod
    async def get_confirm_btn(callback_data: str, custom_data: Optional[str] = None) -> InlineKeyboardButton:
        if custom_data:
            callback_data = CustomCallback(role=callback_data, data=str(custom_data)).pack()

        return InlineKeyboardButton(text="✅ Подтвердить", callback_data=callback_data)

    @staticmethod
    async def get_back_btn(callback_data: str, custom_data: Optional[str] = None) -> InlineKeyboardButton:
        if custom_data:
            callback_data = CustomCallback(role=callback_data, data=str(custom_data)).pack()

        return InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)

    @staticmethod
    async def get_delete_account_btn(account_id: int) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text="🗑 Удалить аккаунт",
            callback_data=CustomCallback(role="delete_account", data=str(account_id)).pack()
        )

    @staticmethod
    async def get_delete_booking_btn(booking_id: int) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text="🗑 Удалить запись",
            callback_data=CustomCallback(role="delete_booking", data=str(booking_id)).pack()
        )

    @staticmethod
    async def markup_from_buttons(buttons: List[List[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=buttons)
