from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📲 Сдать номер"), KeyboardButton(text="📦 Мои номера")],
            [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="🎁 Реф. система")],
            [KeyboardButton(text="💸 Вывод средств"), KeyboardButton(text="🪞 Зеркало")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите нужное действие ниже:"
    )
    return keyboard

def get_operators_keyboard(operators: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for op in operators:
        builder.button(text=op['name'], callback_data=f"op_{op['id']}")
    builder.adjust(2)
    return builder.as_markup()

def get_mode_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⏳ Холд", callback_data="mode_hold")
    builder.button(text="⚡ Безхолд", callback_data="mode_no_hold")
    builder.adjust(2)
    return builder.as_markup()

def get_client_take_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Взять номер", callback_data=f"take_{order_id}")
    return builder.as_markup()

def get_client_processing_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Встал", callback_data=f"success_{order_id}")
    builder.button(text="❌ Брак", callback_data=f"fail_{order_id}")
    builder.adjust(2)
    return builder.as_markup()

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админа."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="💳 Заявки на вывод", callback_data="admin_withdraws")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="❌ Закрыть", callback_data="admin_close")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_withdraw_decision(withdraw_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Выплачено", callback_data=f"wd_pay_{withdraw_id}")
    builder.button(text="❌ Отказ (возврат)", callback_data=f"wd_rej_{withdraw_id}")
    builder.adjust(2)
    return builder.as_markup()