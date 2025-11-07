from datetime import timedelta, datetime
from typing import Union, Optional

from aiogram import Router, F, types, enums
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hcode

from config import Config
from tg_bot.db_models.quick_commands import DbBooking, DbAccount
from tg_bot.keyboards.default import DefaultMarkups as Dm
from tg_bot.keyboards.inline import InlineMarkups as Im, CustomCallback
from tg_bot.misc.browser_processing import BrowserProcessing
from tg_bot.misc.models import WorkTypes
from tg_bot.misc.states import AddBookingStates
from tg_bot.misc.utils import Utils as Ut

router = Router()


@router.message(F.chat.type == enums.ChatType.PRIVATE, F.text == Dm.start_menu_btn_bookings_list)
@router.callback_query(F.data == "back_to_bookings_list")
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
async def add_booking(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {add_booking.__name__}. user_id={uid}")

    text = [
        "<b>➕ Добавление записи на бронь</b>",
        "\n<b>Вам нужно выбрать аккаунт с которого бот будет ловить бронь</b>",
        "\n<b>Используйте кнопки под сообщением ⬇️</b>"
    ]

    db_accounts = await DbAccount().select()
    await Ut.send_step_message(
        user_id=uid, text="\n".join(text),
        markup=await Im.markup_from_buttons([
            *[
                [
                    await Im.universal_btn(
                        callback_data="add_booking_select_account", custom_data=str(acc.id), btn_text=acc.phone
                    )
                ] for acc in db_accounts
            ],
            [await Im.get_back_btn(callback_data="back_to_bookings_list")]
        ])
    )

    await state.set_state(AddBookingStates.SelectAccount)


@router.callback_query(AddBookingStates.SelectAccount, CustomCallback.filter(F.role == "add_booking_select_account"))
async def select_account(callback: types.CallbackQuery, state: FSMContext, callback_data: CustomCallback):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {select_account.__name__}. user_id={uid}")

    acc_id = int(callback_data.data)
    await state.update_data(account_id=acc_id)

    trucks_list = await BrowserProcessing(account_id=acc_id, work_type=WorkTypes.GET_TRUCKS_LIST).run_task()

    db_acc = await DbAccount(db_id=acc_id).select()
    text = [
        "<b>➕ Добавление записи на бронь</b>",
        "\n<b>Вам нужно выбрать грузовик для брони</b>",
        f"\n<b>ℹ️ Все грузовики спаршены с аккаунта №{hcode(str(db_acc.id))}</b>",
        f"<b>📱 Телефон: {hcode(db_acc.phone)}</b>",
        "\n<b>Используйте кнопки под сообщением ⬇️</b>"
    ]

    await Ut.send_step_message(
        user_id=uid, text="\n".join(text),
        markup=await Im.markup_from_buttons([
            *[
                [
                    await Im.universal_btn(
                        callback_data="add_booking_select_truck", custom_data=truck, btn_text=truck
                    )
                ] for truck in trucks_list
            ],
            [await Im.get_back_btn(callback_data="back_to_bookings_list")]
        ])
    )

    await state.set_state(AddBookingStates.SelectTruck)


@router.callback_query(AddBookingStates.SelectTruck, CustomCallback.filter(F.role == "add_booking_select_truck"))
async def select_truck(callback: types.CallbackQuery, state: FSMContext, callback_data: CustomCallback):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {select_truck.__name__}. user_id={uid}")

    await state.update_data(truck=callback_data.data)
    data = await state.get_data()

    text = [
        "<b>➕ Добавление записи на бронь</b>",
        f"\n<b>🆔 Аккаунт №{hcode(str(data['account_id']))}</b>",
        f"<b>🚚 Грузовик: {hcode(data['truck'])}</b>"
        "\n<b>Теперь вам нужно выбрать тип груза</b>",
        "\n<b>Используйте кнопки под сообщением ⬇️</b>"
    ]
    await Ut.send_step_message(
        user_id=uid, text="\n".join(text),
        markup=await Im.markup_from_buttons([
            *[
                [
                    await Im.universal_btn(
                        callback_data="add_booking_select_good", btn_text=good_type, custom_data=good_id
                    )
                ] for good_id, good_type in Config.GOOD_CHARACTERS.items()
            ],
            [await Im.get_back_btn(callback_data="add_booking")]
        ])
    )

    await state.set_state(AddBookingStates.SelectGoodCharacter)


@router.callback_query(AddBookingStates.SelectGoodCharacter, CustomCallback.filter(F.role == "add_booking_select_good"))
@router.callback_query(F.data == "back_to_select_date")
async def select_good_character(callback: types.CallbackQuery, state: FSMContext,
                                callback_data: Optional[CustomCallback] = None):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {select_good_character.__name__}. user_id={uid}")

    if isinstance(callback_data, CustomCallback):
        await state.update_data(good=int(callback_data.data))

    data = await state.get_data()

    text = [
        "<b>➕ Добавление записи на бронь</b>",
        f"\n<b>🆔 Аккаунт №{hcode(str(data['account_id']))}</b>",
        f"<b>🚚 Грузовик: {hcode(data['truck'])}</b>",
        f"<b>📦 Груз: {hcode(Config.GOOD_CHARACTERS[data['good']])}</b>",
        "\n<b>Выберите день для записи</b>",
        "\n<b>Используйте кнопки под сообщением ⬇️</b>"
    ]
    await Ut.send_step_message(
        user_id=uid, text="\n".join(text), markup=await Im.calendar(datetime.now(tz=Config.TIMEZONE))
    )

    await state.set_state(AddBookingStates.SelectDate)


@router.callback_query(AddBookingStates.SelectDate)
async def select_date(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {select_date.__name__}. user_id={uid}")

    data = await state.get_data()
    cd = callback.data

    if cd == "back":
        return await select_truck(
            callback=callback, state=state,
            callback_data=CustomCallback(role="add_booking_select_truck", data=data["truck"])
        )

    if "l:" in cd:
        date_time = datetime.strptime(cd.replace("l:", ""), "%d.%m.%Y")
        current_dt = datetime.now(tz=Config.TIMEZONE)
        if current_dt.year == date_time.year and current_dt.month == date_time.month:
            date_time = current_dt

        return await callback.message.edit_reply_markup(reply_markup=await Im.calendar(date_time=date_time))

    if "r:" in cd:
        date_time = datetime.strptime(cd.replace("r:", ""), "%d.%m.%Y")
        return await callback.message.edit_reply_markup(reply_markup=await Im.calendar(date_time=date_time))

    elif "." in cd:
        returned_value = datetime.strptime(cd, "%d.%m.%Y")
        await state.update_data(date=returned_value)

        text = [
            "<b>➕ Добавление записи на бронь</b>",
            f"\n<b>🆔 Аккаунт №{hcode(str(data['account_id']))}</b>",
            f"<b>🚚 Грузовик: {hcode(data['truck'])}</b>",
            f"<b>📦 Груз: {hcode(Config.GOOD_CHARACTERS[data['good']])}</b>",
            f"<b>📅 Дата: {returned_value.strftime('%d.%m.%Y')}</b>"
            "\n<b>Вам нужно вписать диапазон времени для записи</b>",
            "<b>ℹ️ Формат: HH:MM-HH:MM | Пример: 9:00-09:35, 15:46-19:12, 14:00</b>"
        ]
        await Ut.send_step_message(
            user_id=uid, text="\n".join(text),
            markup=await Im.markup_from_buttons([
                [Im.select_first_half_day_btn],
                [Im.select_second_half_day_btn],
                [await Im.get_back_btn(callback_data="back_to_select_date")]
            ])
        )

        await state.set_state(AddBookingStates.SelectTimeRange)


@router.message(AddBookingStates.SelectTimeRange)
@router.callback_query(AddBookingStates.SelectTimeRange, CustomCallback.filter(F.role == "select_time"))
async def select_time(message: Union[types.Message, types.CallbackQuery], state: FSMContext,
                      callback_data: Optional[CustomCallback] = None):
    uid = message.from_user.id
    Config.logger.info(f"Handler called. {select_time.__name__}. user_id={uid}")

    data = await state.get_data()
    if isinstance(message, types.CallbackQuery):
        await message.answer()

        time, duration = callback_data.data.split("_")
        time_dt = datetime.strptime(time, "%H:%M")
        await state.update_data(
            date=data["date"].replace(hour=time_dt.hour, minute=time_dt.minute),
            time_duration=int(duration)
        )

    else:
        text_wrong_fmt = [
            "<b>🔴 Неверный формат времени!</b>",
            "\n<b>ℹ️ Формат: HH:MM-HH:MM | Пример: 9:00-09:35, 15:46-19:12, 14:00</b>"
            "\n<b>Попробуйте ещё раз!</b>"
        ]

        input_text = message.text.strip().split("-")
        if len(input_text) != 2:
            msg = await message.answer(text="\n".join(text_wrong_fmt))
            await Ut.add_msg_to_delete(user_id=uid, msg_id=msg.message_id)
            return

        try:
            first_time_dt = datetime.strptime(input_text[0], "%H:%M")
            second_time_dt = datetime.strptime(input_text[1], "%H:%M")

        except ValueError:
            msg = await message.answer(text="\n".join(text_wrong_fmt))
            await Ut.add_msg_to_delete(user_id=uid, msg_id=msg.message_id)
            return

        if first_time_dt > second_time_dt:
            msg = await message.answer(text="\n".join(text_wrong_fmt))
            await Ut.add_msg_to_delete(user_id=uid, msg_id=msg.message_id)
            return

        if first_time_dt > datetime.strptime("21:41", "%H:%M"):
            text_wrong_fmt = [
                "<b>🔴 Неверно указанное время!</b>",
                "<b>Левая граница не может быть позже чем 21:40!</b>"
                "\n<b>Попробуйте ещё раз!</b>"
            ]

            msg = await message.answer(text="\n".join(text_wrong_fmt))
            await Ut.add_msg_to_delete(user_id=uid, msg_id=msg.message_id)
            return

        if second_time_dt < datetime.strptime("8:59", "%H:%M"):
            text_wrong_fmt = [
                "<b>🔴 Неверно указанное время!</b>",
                "<b>Правая граница не может быть раньше чем 08:59!</b>"
                "\n<b>Попробуйте ещё раз!</b>"
            ]

            msg = await message.answer(text="\n".join(text_wrong_fmt))
            await Ut.add_msg_to_delete(user_id=uid, msg_id=msg.message_id)
            return

        await state.update_data(
            date=data["date"].replace(hour=first_time_dt.hour, minute=first_time_dt.minute),
            time_duration=int((second_time_dt - first_time_dt).seconds / 60)
        )

    # continue
