from typing import Union

from aiogram import Router, F, types, enums
from aiogram.fsm.context import FSMContext

from config import Config
from tg_bot.keyboards.default import DefaultMarkups as Dm

router = Router()


@router.message(F.chat.type == enums.ChatType.PRIVATE, F.text == Dm.start_menu_btn_bookings_list)
async def show_bookings_list(message: Union[types.Message, types.CallbackQuery], state: FSMContext):
    uid = message.from_user.id
    Config.logger.info(f"Handler called. {show_bookings_list.__name__}. user_id={uid}")

    await state.clear()
    if isinstance(message, types.CallbackQuery):
        await message.answer()
        message = message.message
