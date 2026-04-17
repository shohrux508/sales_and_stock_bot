from aiogram.fsm.state import State, StatesGroup


class AddCategoryState(StatesGroup):
    name = State()


class EditCategoryState(StatesGroup):
    name = State()


class AddProductState(StatesGroup):
    category_id = State()
    name = State()
    price = State()
    initial_quantity = State()


class WaitAdminReply(StatesGroup):
    waiting_for_new_quantity = State()


class ReceiptState(StatesGroup):
    category_id = State()
    product_id = State()
    quantity = State()


class WriteOffState(StatesGroup):
    category_id = State()
    product_id = State()
    quantity = State()
    reason = State()


class BindBarcodeState(StatesGroup):
    product_id = State()
    barcode = State()


class EditStaffKPIState(StatesGroup):
    target_tg_id = State()
    kpi = State()


class EditStaffProfileState(StatesGroup):
    target_tg_id = State()
    full_name = State()
    phone = State()
