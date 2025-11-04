from typing import Union

from aiogram import Router, types, F, enums
from aiogram.filters import CommandStart

from config import Config
from tg_bot.keyboards.default import DefaultMarkups as Dm
from tg_bot.misc.utils import Utils as Ut

router = Router()


@router.message(F.chat.type == enums.ChatType.PRIVATE, CommandStart())
@router.callback_query(F.data == "back_to_menu")
async def cmd_start(message: Union[types.Message, types.CallbackQuery]):
    uid = message.from_user.id
    Config.logger.info(f"Handler called. {cmd_start.__name__}. user_id={uid}")

    if isinstance(message, types.CallbackQuery):
        await message.answer()

    text = [
        "<b>🤖 Бот для бронирования электронной очереди</b>",
        "\n<b>Для взаимодействия с ботом, используйте клавиатуру ⬇️</b>"
    ]
    await Ut.send_step_message(user_id=uid, text="\n".join(text), markup=Dm.start_menu)
