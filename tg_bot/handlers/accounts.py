from typing import Union

from aiogram import Router, F, types, enums
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hcode

from config import Config
from tg_bot.db_models.quick_commands import DbAccount
from tg_bot.keyboards.default import DefaultMarkups as Dm
from tg_bot.keyboards.inline import InlineMarkups as Im
from tg_bot.misc.states import AddAccountStates
from tg_bot.misc.utils import Utils as Ut

router = Router()


@router.message(F.chat.type == enums.ChatType.PRIVATE, F.text == Dm.start_menu_btn_accounts_list)
@router.callback_query(F.data == "back_to_acc_list")
@router.callback_query(F.data == "move_to_accounts_list")
async def show_accounts_list(message: Union[types.Message, types.CallbackQuery], state: FSMContext):
    uid = message.from_user.id
    Config.logger.info(f"Handler called. {show_accounts_list.__name__}. user_id={uid}")

    await state.clear()
    if isinstance(message, types.CallbackQuery):
        await message.answer()
        message = message.message

    db_accounts = await DbAccount(verified=True).select()
    if not db_accounts:
        text = [
            "<b>ℹ️ У вас нету сохраненных аккаунтов!</b>",
            "\n<b>Вы можете быстро добавить аккаунт по кнопке под сообщением ⬇️</b>"
        ]

        await Ut.send_step_message(
            user_id=uid, text="\n".join(text),
            markup=await Im.markup_from_buttons([[Im.add_account_btn], [Im.back_to_menu_btn]])
        )
        return

    acc_texts = []

    is_work_counter = 0
    for db_acc in db_accounts:
        is_work_counter += 1 if db_acc.is_work else 0

        acc_texts.append([
            "\n".join([
                f"<b>🆔 Аккаунт №{hcode(str(db_acc.id))}</b>",
                f"\n<b>📱 Телефон: {hcode(db_acc.phone)}</b>",
                f"<b>🔐 Пароль: {hcode(db_acc.password)}</b>",
                f"<b>🖥 Прокси: {hcode(db_acc.proxy)}</b>",
                f"<b>👨‍💻 В работе: {'Да' if db_acc.is_work else 'Нет'}</b>"
            ]),
            await Im.markup_from_buttons([[await Im.get_delete_account_btn(db_acc.id)]])
        ])

    main_text = [
        "<b>❇️ Список добавленных аккаунтов</b>",
        f"\n<b>ℹ️ Количество аккаунтов: {len(db_accounts)}</b>",
        f"<b>👨‍💻 В работе: {is_work_counter}</b>",
        "\n<b>Используйте кнопки под сообщениями ⬇️</b>"
    ]

    await Ut.send_step_message(
        user_id=uid, text="\n".join(main_text),
        markup=await Im.markup_from_buttons([[Im.add_account_btn], [Im.back_to_menu_btn]])
    )
    for acc_text, acc_markup in acc_texts:
        msg = await message.answer(text=acc_text, reply_markup=acc_markup, disable_web_page_preview=True)
        await Ut.add_msg_to_delete(user_id=uid, msg_id=msg.message_id)


@router.callback_query(F.data == "add_account")
@router.callback_query(F.data == "back_to_add_account_phone")
async def add_account(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {add_account.__name__}. user_id={uid}")

    text = [
        "<b>➕ Добавление аккаунта</b>",
        "\n<b>Введите номер телефона для авторизации в аккаунт</b>",
        "\n<b>ℹ️ Номер телефона должен быть полным!</b>"
    ]
    await Ut.send_step_message(
        user_id=uid, text="\n".join(text),
        markup=await Im.markup_from_buttons([[await Im.get_back_btn("back_to_acc_list")]])
    )

    await state.set_state(AddAccountStates.WritePhone)


@router.message(AddAccountStates.WritePhone)
@router.callback_query(F.data == "back_to_add_account_password")
async def account_phone(message: Union[types.Message, types.CallbackQuery], state: FSMContext):
    uid = message.from_user.id
    Config.logger.info(f"Handler called. {account_phone.__name__}. user_id={uid}")

    if isinstance(message, types.CallbackQuery):
        await message.answer()

    else:
        phone = message.text.strip().replace("+", "")
        if len(phone) < 6:
            text = [
                "<b>🔴 Номер телефона не может быть таким коротким!</b>",
                "<b>Попробуйте ещё раз!</b>"
            ]
            msg = await message.answer(text="\n".join(text))
            await Ut.add_msg_to_delete(user_id=uid, msg_id=msg.message_id)
            return

        await state.update_data(phone="+" + phone)

    text = [
        "<b>➕ Добавление аккаунта</b>",
        "\n<b>Теперь вам нужно ввести пароль к аккаунту</b>"
    ]
    await Ut.send_step_message(
        user_id=uid, text="\n".join(text),
        markup=await Im.markup_from_buttons([[await Im.get_back_btn("back_to_add_account_phone")]])
    )

    await state.set_state(AddAccountStates.WritePassword)


@router.message(AddAccountStates.WritePassword)
async def account_password(message: types.Message, state: FSMContext):
    uid = message.from_user.id
    Config.logger.info(f"Handler called. {account_password.__name__}. user_id={uid}")

    data = await state.get_data()
    phone = data["phone"]
    password = message.text.strip()
    await state.update_data(password=password)

    text = [
        "<b>➕ Добавление аккаунта</b>",
        "\n<b>Проверьте действительность данных для авторизации:</b>",
        f"\n<b>📱 Телефон: {hcode(phone)}</b>",
        f"<b>🔐 Пароль: {hcode(password)}</b>",
        "\n<b>ℹ️ После подтверждения вами данных, бот выполнит проверочную авторизацию в аккаунт перед добавлением информации в базу данных</b>",
        "\n<b>Используйте кнопки под сообщением ⬇️</b>"
    ]
    await Ut.send_step_message(
        user_id=uid, text="\n".join(text),
        markup=await Im.markup_from_buttons([
            [await Im.get_confirm_btn("confirm_add_account")],
            [await Im.get_back_btn("back_to_add_account_password")],
        ])
    )

    await state.set_state(AddAccountStates.Confirmation)


@router.callback_query(F.data == "confirm_add_account")
async def confirm_add_account(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {confirm_add_account.__name__}. user_id={uid}")

    data = await state.get_data()

    accounts_with_proxy = await DbAccount().select(proxy_not_none=True)
    attached_proxies = [acc.proxy for acc in accounts_with_proxy]

    selected_proxy = None
    for proxy_obj in Config.INPUT_PROXIES:
        if str(proxy_obj) in attached_proxies:
            continue

        selected_proxy = str(proxy_obj)
        print(f"selected_proxy = {selected_proxy}")
        print(f"attached_proxies = {attached_proxies}")
        print(f"proxy_obj = {proxy_obj}")
        break

    if not selected_proxy:  # body in temp status!:
        text = [
            "<b>Не хватило прокси на этот аккаунт!</b>",
            "<b>Обратитесь к администратору!</b>"
        ]
        await Ut.send_step_message(user_id=uid, text="\n".join(text))
        await state.clear()
        return

    result = await DbAccount(phone=data['phone'], password=data['password'], proxy=selected_proxy).add()
    if result:
        text = [
            "<b>➕ Добавление аккаунта</b>",
            "\n<b>✅ Вы подтвердили данные для авторизации в аккаунт!</b>",
            f"\n<b>📱 Телефон: {hcode(data['phone'])}</b>",
            f"<b>🔐 Пароль: {hcode(data['password'])}</b>",
            "\n<b>ℹ️ Теперь данные находятся в проверке на действительность. Ожидайте сообщения о успешном добавлении аккаунта!</b>"
        ]
        await Ut.send_step_message(
            user_id=uid, text="\n".join(text), markup=await Im.markup_from_buttons([[Im.move_to_accounts_list_btn]])
        )

    else:
        text = [
            "<b>Не удалось добавить аккаунт в список проверки!</b>"
        ]
        await Ut.send_step_message(user_id=uid, text="\n".join(text))

    await state.clear()
