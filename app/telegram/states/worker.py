from aiogram.fsm.state import State, StatesGroup


class SellState(StatesGroup):
    category_id = State()
    product_id = State()
    amount = State()
    checkout_decision = State()
