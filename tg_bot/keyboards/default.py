from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


class DefaultMarkups:
    start_menu_btn_bookings_list = "Список бронирований"
    start_menu_btn_accounts_list = "Список аккаунтов"
    start_menu = ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [
                KeyboardButton(text=start_menu_btn_bookings_list)
            ],
            [
                KeyboardButton(text=start_menu_btn_accounts_list)
            ]
        ]
    )
