from aiogram.fsm.state import StatesGroup, State


class AddAccountStates(StatesGroup):
    WritePhone = State()
    WritePassword = State()
    Confirmation = State()


class AddBookingStates(StatesGroup):
    SelectAccount = State()
    SelectTruck = State()
    SelectGoodCharacter = State()
    SelectDate = State()
    SelectTimeRange = State()
    Confirmation = State()
