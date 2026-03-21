from aiogram.fsm.state import State, StatesGroup

class AddProductState(StatesGroup):
    name = State()
    price = State()
    initial_quantity = State()

class WaitAdminReply(StatesGroup):
    waiting_for_new_quantity = State()
