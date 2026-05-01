from aiogram.fsm.state import StatesGroup, State

class OrderState(StatesGroup):
    waiting_for_operator = State()
    waiting_for_mode = State()
    waiting_for_qr = State()

class WithdrawState(StatesGroup):
    waiting_for_wallet = State()

class AdminState(StatesGroup):
    waiting_for_broadcast = State()