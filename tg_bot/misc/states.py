from aiogram.fsm.state import StatesGroup, State


class AddAccountStates(StatesGroup):
    WritePhone = State()
    WritePassword = State()
    Confirmation = State()


class AddBookingStates(StatesGroup):
    SelectTruck = State()
    SelectGoodCharacter = State()
    SelectDate = State()
    WriteTimeDuration = State()
    Confirmation = State()
