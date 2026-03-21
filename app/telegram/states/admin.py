from aiogram.fsm.state import State, StatesGroup

class AddCategoryState(StatesGroup):
    name = State()

class AddProductState(StatesGroup):
    category_id = State()
    name = State()
    price = State()
    initial_quantity = State()

class WaitAdminReply(StatesGroup):
    waiting_for_new_quantity = State()
