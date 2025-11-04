from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


class DefaultMarkups:
    start_menu_btn_active_books = "Активная бронь"
    start_menu_btn_accounts_list = "Список аккаунтов"
    start_menu = ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [
                KeyboardButton(text=start_menu_btn_active_books)
            ],
            [
                KeyboardButton(text=start_menu_btn_accounts_list)
            ]
        ]
    )
