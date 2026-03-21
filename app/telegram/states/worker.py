from aiogram.fsm.state import State, StatesGroup

class SellState(StatesGroup):
    product_id = State()
    amount = State()
