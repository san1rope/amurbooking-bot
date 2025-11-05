from aiogram.fsm.state import StatesGroup, State


class AddAccountStates(StatesGroup):
    WritePhone = State()
    WritePassword = State()
    Confirmation = State()
