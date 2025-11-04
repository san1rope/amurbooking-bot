from typing import List

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


class CustomCallback(CallbackData, prefix="cc"):
    role: str
    data: str


class InlineMarkups:
    back_to_menu_btn = InlineKeyboardButton(text="⌨️ В меню", callback_data="back_to_menu")
    add_account_btn = InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="add_account")

    @staticmethod
    async def get_back_btn(callback_data: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)

    @staticmethod
    async def get_delete_account_btn(account_id: int) -> InlineKeyboardButton:
        return InlineKeyboardButton(
            text="🗑 Удалить аккаунт",
            callback_data=CustomCallback(role="delete_account", data=str(account_id)).pack()
        )

    @staticmethod
    async def markup_from_buttons(buttons: List[List[InlineKeyboardButton]]) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(inline_keyboard=buttons)
