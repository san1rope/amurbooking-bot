from datetime import timedelta
from typing import Union

from aiogram import Router, F, types, enums
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hcode

from config import Config
from tg_bot.db_models.quick_commands import DbBooking, DbAccount
from tg_bot.keyboards.default import DefaultMarkups as Dm
from tg_bot.keyboards.inline import InlineMarkups as Im, CustomCallback
from tg_bot.misc.browser_processing import BrowserProcessing
from tg_bot.misc.states import AddBookingStates
from tg_bot.misc.utils import Utils as Ut

router = Router()


@router.message(F.chat.type == enums.ChatType.PRIVATE, F.text == Dm.start_menu_btn_bookings_list)
async def show_bookings_list(message: Union[types.Message, types.CallbackQuery], state: FSMContext):
    uid = message.from_user.id
    Config.logger.info(f"Handler called. {show_bookings_list.__name__}. user_id={uid}")

    await state.clear()
    if isinstance(message, types.CallbackQuery):
        await message.answer()
        message = message.message

    db_bookings = await DbBooking(status=0).select()
    if not db_bookings:
        text = [
            "<b>ℹ️ У вас нету брони в работе!</b>",
            "\n<b>Вы можете быстро добавить заявку на бронь по кнопке под сообщением ⬇️</b>"
        ]

        await Ut.send_step_message(
            user_id=uid, text="\n".join(text),
            markup=await Im.markup_from_buttons([[Im.add_booking_btn], [Im.back_to_menu_btn]])
        )
        return

    book_texts = []
    for db_book in db_bookings:
        book_texts.append([
            "\n".join([
                f"<b>🆔 Бронь №{hcode(str(db_book.id))}</b>",
                f"\n<b>🚚 Грузовик: {hcode(str(db_book.truck))}</b>",
                f"<b>📦 Груз: {hcode(str(db_book.good_character))}</b>",
                f"<b>Дата и время: {hcode(db_book.book_date.strftime('%d.%m.%Y %H:%M')) + '-'}</b>"
                f"{(db_book.book_date + timedelta(minutes=db_book.time_duration)).strftime('%H:%M')}"
            ]),
            await Im.markup_from_buttons([[await Im.get_delete_booking_btn(db_book.id)]])
        ])

    main_text = [
        "<b>❇️ Список записей на бронь</b>",
        f"\n<b>ℹ️ Количество активных записей: {len(db_bookings)}</b>",
        "\n<b>Используйте кнопки под сообщениями ⬇️</b>"
    ]

    await Ut.send_step_message(
        user_id=uid, text="\n".join(main_text),
        markup=await Im.markup_from_buttons([[Im.add_booking_btn], [Im.back_to_menu_btn]])
    )
    for acc_text, acc_markup in book_texts:
        msg = await message.answer(text=acc_text, reply_markup=acc_markup, disable_web_page_preview=True)
        await Ut.add_msg_to_delete(user_id=uid, msg_id=msg.message_id)


@router.callback_query(CustomCallback.filter(F.role == "delete_booking"))
async def delete_booking(callback: types.CallbackQuery, callback_data: CustomCallback):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {delete_booking.__name__}. user_id={uid}")

    db_book = await DbBooking(db_id=int(callback_data.data)).select()
    if not db_book:
        await callback.message.edit_text(text="<b>⚠️ Ошибка! Записи не существует!</b>")
        return

    text = [
        f"<b>Вы действительно желаете удалить запись №{hcode(db_book.id)}?</b>",
        f"\n<b>🚚 Грузовик: {hcode(str(db_book.truck))}</b>",
        f"<b>📦 Груз: {hcode(str(db_book.good_character))}</b>",
        f"<b>Дата и время: {hcode(db_book.book_date.strftime('%d.%m.%Y %H:%M')) + '-'}</b>"
        f"{(db_book.book_date + timedelta(minutes=db_book.time_duration)).strftime('%H:%M')}",
        "\n<b>Используйте кнопки под сообщением ⬇️</b>"
    ]
    await callback.message.edit_text(
        text="\n".join(text), disable_web_page_preview=True,
        reply_markup=await Im.markup_from_buttons([
            [await Im.get_confirm_btn(custom_data=str(db_book.id), callback_data="delete_booking_confirm")],
            [await Im.get_back_btn(custom_data=str(db_book.id), callback_data="delete_booking_back")]
        ])
    )


@router.callback_query(CustomCallback.filter(F.role == "delete_booking_back"))
async def delete_booking_cancel(callback: types.CallbackQuery, callback_data: CustomCallback):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {delete_booking_cancel.__name__}. user_id={uid}")

    db_book = await DbBooking(db_id=int(callback_data.data)).select()
    if not db_book:
        await callback.message.edit_text(text="<b>⚠️ Ошибка! Записи не существует!</b>")
        return

    text = [
        f"<b>🆔 Бронь №{hcode(str(db_book.id))}</b>",
        f"\n<b>🚚 Грузовик: {hcode(str(db_book.truck))}</b>",
        f"<b>📦 Груз: {hcode(str(db_book.good_character))}</b>",
        f"<b>Дата и время: {hcode(db_book.book_date.strftime('%d.%m.%Y %H:%M')) + '-'}</b>"
        f"{(db_book.book_date + timedelta(minutes=db_book.time_duration)).strftime('%H:%M')}"
    ]
    markup = await Im.markup_from_buttons([[await Im.get_delete_booking_btn(db_book.id)]])
    await callback.message.edit_text(text="\n".join(text), reply_markup=markup, disable_web_page_preview=True)


@router.callback_query(CustomCallback.filter(F.role == "delete_booking_confirm"))
async def delete_booking_confirm(callback: types.CallbackQuery, callback_data: CustomCallback):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {delete_booking_confirm.__name__}. user_id={uid}")

    result = await DbBooking(db_id=int(callback_data.data)).remove()
    if result:
        await callback.message.edit_text(text="<b>✅ Вы удалили запись!</b>")

    else:
        await callback.message.edit_text(text="<b>🔴 Не удалось удалить запись!</b>")


@router.callback_query(F.data == "add_booking")
@router.callback_query(F.data == "back_to_add_account_phone")
async def add_booking(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {add_booking.__name__}. user_id={uid}")

    text = [
        "<b>➕ Добавление записи на бронь</b>",
        "\n<b>Вам нужно выбрать аккаунт с которого бот будет ловить бронь</b>",
        "\n<b>Используйте кнопки под сообщением ⬇️</b>"
    ]

    db_accounts = await DbAccount(is_work=False).select()
    await Ut.send_step_message(
        user_id=uid, text="\n".join(text),
        markup=None
    )

    await state.set_state(AddBookingStates.SelectAccount)


@router.callback_query()
async def select_account(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {select_account.__name__}. user_id={uid}")

    text = [
        "<b>➕ Добавление записи на бронь</b>",
        "\n<b>Вам нужно выбрать грузовик для брони</b>",
        "\n<b>ℹ️ Все грузовики спаршены с аккаунта</b>"
    ]

    await state.set_state(AddBookingStates.SelectTruck)
