from aiogram import Router, F, types, enums
from aiogram.utils.markdown import hcode

from config import Config
from tg_bot.db_models.quick_commands import DbAccount
from tg_bot.keyboards.default import DefaultMarkups as Dm
from tg_bot.keyboards.inline import InlineMarkups as Im
from tg_bot.misc.utils import Utils as Ut

router = Router()


@router.message(F.chat.type == enums.ChatType.PRIVATE, F.text == Dm.start_menu_btn_accounts_list)
async def show_accounts_list(message: types.Message):
    uid = message.from_user.id
    Config.logger.info(f"Handler called. {show_accounts_list.__name__}. user_id={uid}")

    db_accounts = await DbAccount().select()
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
        "\n<b>Используйте клавиатуры под сообщениями ⬇️</b>"
    ]

    await Ut.send_step_message(
        user_id=uid, text="\n".join(main_text),
        markup=await Im.markup_from_buttons([[Im.add_account_btn], [Im.back_to_menu_btn]])
    )
    for acc_text, acc_markup in acc_texts:
        msg = await message.answer(text=acc_text, reply_markup=acc_markup, disable_web_page_preview=True)
        await Ut.add_msg_to_delete(user_id=uid, msg_id=msg.message_id)


@router.callback_query(F.data == "add_account")
async def add_account(callback: types.CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    Config.logger.info(f"Handler called. {add_account.__name__}. user_id={uid}")
