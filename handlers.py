import os
import re
from aiogram import Router, F
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from db_requests import (get_user, add_user, get_all_operators, get_queue_stats,
                         get_setting, count_referrals, add_order, get_supplier_stats,
                         create_withdrawal, register_group, get_pending_orders,
                         update_order_status, get_order, update_order_client, process_payment,
                         start_hold, get_admin_stats, get_pending_withdrawals,
                         get_withdrawal_by_id, process_withdrawal, get_all_user_ids, set_user_role)
from keyboards import (get_main_menu, get_operators_keyboard, get_mode_keyboard,
                       get_client_take_keyboard, get_client_processing_keyboard,
                       get_admin_menu_keyboard, get_admin_withdraw_decision)
from states import OrderState, WithdrawState, AdminState

router = Router()

# Формат: "Имя": "<tg-emoji emoji-id='ID_СМАЙЛИКА'>СТАНДАРТНЫЙ_СМАЙЛ</tg-emoji>"
EMOJI_MAP = {
    "МТС": "<tg-emoji emoji-id='5350300928824084944'>🔴</tg-emoji>",
    "Билайн": "<tg-emoji emoji-id='5350509561155456168'>🟡</tg-emoji>",
    "Tele2": "<tg-emoji emoji-id='5350455736625304645'>⚫️</tg-emoji>",
    "Сбер": "<tg-emoji emoji-id='5352814571318970409'>🟢</tg-emoji>",
    "Мегафон": "<tg-emoji emoji-id='5350679628975475985'>🟢</tg-emoji>",
    "ВТБ": "<tg-emoji emoji-id='5352832489922527760'>🔵</tg-emoji>",
    "Газпром": "<tg-emoji emoji-id='1234567890123456789'>🔵</tg-emoji>",
    "Миранда": "<tg-emoji emoji-id='1234567890123456789'>🟣</tg-emoji>",
    "Добросвязь": "<tg-emoji emoji-id='1234567890123456789'>🔵</tg-emoji>"
}


def get_emoji_for_operator(op_name: str) -> str:
    for key, emoji in EMOJI_MAP.items():
        if key in op_name:
            return emoji
    return "⚪️"


async def is_admin(user_id: int) -> bool:
    """Проверяет права. ID из .env - создатель. Остальные берутся из БД."""
    admin_id = os.getenv('ADMIN_ID')
    if admin_id and user_id == int(admin_id):
        return True

    user = await get_user(user_id)
    return user and user['role'] == 'admin'


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    user = await get_user(user_id)

    if not user:
        referrer_id = None
        if command.args and command.args.isdigit():
            ref_id = int(command.args)
            if ref_id != user_id:
                referrer_id = ref_id
        await add_user(user_id, referrer_id)

    operators = await get_all_operators()
    queue_stats = await get_queue_stats()

    prices_text = "💎 <b>Прайсы:</b>\n"
    queues_text = "📥 <b>Очереди:</b>\n"

    for op in operators:
        emoji = get_emoji_for_operator(op['name'])
        prices_text += f"{emoji} <b>{op['name']}</b> — ${op['price_hold']:.2f} / ${op['price_no_hold']:.2f}\n"
        op_stats = queue_stats.get(op['id'], {'hold': 0, 'no_hold': 0})
        queues_text += f"{emoji} <b>{op['name']}:</b> {op_stats['hold']} / {op_stats['no_hold']}\n"

    final_text = (
        f"{prices_text}\n{queues_text}\n<b>Вы находитесь в главном меню.</b>\n👇 <b>Выберите нужное действие ниже:</b>")
    await message.answer(final_text, reply_markup=get_main_menu())


@router.message(F.text == "👤 Профиль")
async def cmd_profile(message: Message):
    user = await get_user(message.from_user.id)
    if not user: return await message.answer("Произошла ошибка. Пожалуйста, отправьте /start")

    roles_ru = {'client': 'Клиент', 'supplier': 'Поставщик', 'admin': 'Администратор'}
    role_text = roles_ru.get(user['role'], 'Неизвестно')
    text = (f"👤 <b>Ваш профиль:</b>\n\n🆔 <b>Ваш ID:</b> <code>{user['telegram_id']}</code>\n"
            f"🎭 <b>Роль:</b> {role_text}\n💰 <b>Баланс:</b> ${user['balance']:.2f}\n")
    await message.answer(text)


@router.message(F.text == "🎁 Реф. система")
async def cmd_referral(message: Message):
    user_id = message.from_user.id
    bot_info = await message.bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
    ref_count = await count_referrals(user_id)
    ref_percent_str = await get_setting('ref_percent')
    ref_percent = float(ref_percent_str) if ref_percent_str else 5.0
    text = ("🎁 <b>Реферальная система</b>\n\nПриглашайте других поставщиков и получайте пассивный доход!\n\n"
            f"📈 <b>Ваш бонус:</b> {ref_percent}% от суммы их успешных сделок.\n👥 <b>Ваши рефералы:</b> {ref_count} чел.\n\n"
            f"🔗 <b>Ваша ссылка для приглашений:</b>\n<code>{ref_link}</code>")
    await message.answer(text)


@router.message(F.text == "📦 Мои номера")
async def cmd_my_numbers(message: Message):
    stats = await get_supplier_stats(message.from_user.id)
    text = (
        f"📦 <b>Статистика ваших номеров:</b>\n\n⏳ <b>В очереди (или в холде):</b> {stats.get('pending', 0) + stats.get('holding', 0)} шт.\n"
        f"✅ <b>Успешно продано:</b> {stats.get('completed', 0)} шт.\n❌ <b>Отклонено/Брак:</b> {stats.get('cancelled', 0)} шт.")
    await message.answer(text)


@router.message(F.text == "🪞 Зеркало")
async def cmd_mirror(message: Message):
    await message.answer("🪞 <b>Зеркала нашего сервиса:</b>\n🤖 @ReserveBot1_bot (В разработке)")


@router.message(F.text == "📲 Сдать номер")
async def start_order_flow(message: Message, state: FSMContext):
    operators = await get_all_operators()
    if not operators: return await message.answer("Ошибка: Прайс-лист пуст.")
    await message.answer("Шаг 1/3. Выберите оператора:", reply_markup=get_operators_keyboard(operators))
    await state.set_state(OrderState.waiting_for_operator)


@router.callback_query(OrderState.waiting_for_operator, F.data.startswith("op_"))
async def process_operator(call: CallbackQuery, state: FSMContext):
    operator_id = int(call.data.split("_")[1])
    await state.update_data(operator_id=operator_id)
    await call.message.edit_text("Шаг 2/3. Выберите режим работы:", reply_markup=get_mode_keyboard())
    await state.set_state(OrderState.waiting_for_mode)


@router.callback_query(OrderState.waiting_for_mode, F.data.startswith("mode_"))
async def process_mode(call: CallbackQuery, state: FSMContext):
    mode = "hold" if call.data == "mode_hold" else "no_hold"
    await state.update_data(mode=mode)
    await call.message.edit_text(
        "Шаг 3/3. Отправьте скриншот QR-кода и обязательно укажите **номер телефона** в описании к фото.")
    await state.set_state(OrderState.waiting_for_qr)


@router.message(OrderState.waiting_for_qr, F.photo)
async def process_qr_photo(message: Message, state: FSMContext):
    raw_phone = message.caption

    if not raw_phone:
        return await message.answer("❌ Вы забыли указать номер телефона в описании к фотографии! Попробуйте еще раз.")

    clean_phone = re.sub(r'[\s\-\(\)]', '', raw_phone)

    if not re.match(r'^(?:\+7|8|7)\d{10}$', clean_phone):
        error_text = (
            "❌ <b>Неверный формат номера!</b>\n\n"
            "Пожалуйста, отправьте фото еще раз и убедитесь, что подпись содержит корректный номер.\n"
            "<i>Пример: +79991234567 или 89991234567</i>"
        )
        return await message.answer(error_text)

    data = await state.get_data()
    await add_order(message.from_user.id, data['operator_id'], clean_phone, message.photo[-1].file_id, data['mode'])
    await state.clear()
    await message.answer("✅ Отлично! Симка успешно загружена и добавлена в очередь.")


@router.message(OrderState.waiting_for_qr)
async def process_qr_wrong_format(message: Message):
    await message.answer("❌ Мне нужна именно **фотография** QR-кода с номером в подписи. Попробуйте еще раз.")


@router.message(F.text == "💸 Вывод средств")
async def cmd_withdraw(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)

    # === ДОБАВЛЕНА ПРОВЕРКА НА НУЛЕВОЙ БАЛАНС ===
    if user['balance'] <= 0:
        return await message.answer("❌ <b>Ошибка:</b> Ваш баланс пуст! Для вывода необходимо иметь средства на счету.")

    await state.update_data(withdraw_amount=user['balance'])
    await message.answer(
        f"💸 <b>Заявка на вывод средств</b>\nСумма: <b>${user['balance']:.2f}</b>\nОтправьте адрес кошелька:")
    await state.set_state(WithdrawState.waiting_for_wallet)


@router.message(WithdrawState.waiting_for_wallet)
async def process_wallet(message: Message, state: FSMContext):
    wallet = message.text
    data = await state.get_data()
    await create_withdrawal(message.from_user.id, data['withdraw_amount'], wallet)
    await state.clear()
    await message.answer("✅ Ваша заявка успешно отправлена администратору. Ожидайте пополнения кошелька.")


@router.message(Command("add_admin"))
async def cmd_add_admin(message: Message, command: CommandObject):
    admin_id = os.getenv('ADMIN_ID')
    # Выдать админку может ТОЛЬКО создатель из .env
    if not admin_id or message.from_user.id != int(admin_id):
        return

    if not command.args or not command.args.isdigit():
        return await message.answer("Укажите ID пользователя, например: /add_admin 123456789")

    target_id = int(command.args)
    user = await get_user(target_id)

    if not user:
        return await message.answer("Пользователь с таким ID не найден в базе бота.")

    await set_user_role(target_id, 'admin')
    await message.answer(f"✅ Пользователь <code>{target_id}</code> успешно назначен администратором!")


@router.message(Command("reg"))
async def cmd_reg_group(message: Message):
    if not await is_admin(message.from_user.id): return
    if message.chat.type in ['group', 'supergroup']:
        await register_group(message.chat.id, message.chat.title or "Без названия", message.from_user.id)
        await message.answer("✅ Группа успешно зарегистрирована! Теперь здесь можно выдавать номера.")
    else:
        await message.answer("Эту команду нужно писать в клиентской группе.")


@router.message(Command("drop"))
async def cmd_drop(message: Message, command: CommandObject):
    if not await is_admin(message.from_user.id): return
    if message.chat.type not in ['group', 'supergroup']: return await message.answer("Только в группах!")
    if not command.args or not command.args.isdigit(): return await message.answer(
        "Укажите количество, например: /drop 5")

    orders = await get_pending_orders(int(command.args))
    if not orders: return await message.answer("📭 Очередь пуста, нет номеров для выдачи.")

    await message.answer(f"🚀 Начинаю выдачу {len(orders)} номеров...")
    for order in orders:
        await update_order_status(order['id'], 'processing', message.chat.id)
        mode_text = "Безхолд" if order['mode'] == 'no_hold' else "Холд 30 мин"
        emoji = get_emoji_for_operator(order['op_name'])

        text = (f"📥 <b>Номер готов к выдаче</b>\n\n<b>Оператор:</b> {emoji} {order['op_name']}\n"
                f"<b>Номер:</b> <code>{order['phone_number']}</code>\n<b>Режим:</b> {mode_text}\n\n<i>Заявка #{order['id']}</i>")
        await message.answer_photo(photo=order['qr_data'], caption=text,
                                   reply_markup=get_client_take_keyboard(order['id']))


@router.callback_query(F.data.startswith("take_"))
async def process_take_number(call: CallbackQuery):
    try:
        await call.answer()
        order_id = int(call.data.split("_")[1])
        order = await get_order(order_id)

        if not order: return await call.message.answer("❌ Ошибка: Этот заказ был удален.")
        if order['status'] != 'processing': return await call.message.answer(f"❌ Ошибка: Заказ уже обработан.")

        await update_order_client(order_id, call.from_user.id)
        emoji = get_emoji_for_operator(order['op_name'])
        mode_text = "Безхолд" if order['mode'] == 'no_hold' else "Холд 30 мин"
        username = call.from_user.username or call.from_user.first_name

        text = (f"⏳ <b>Номер взят в работу</b>\n\n<b>Оператор:</b> {emoji} {order['op_name']}\n"
                f"<b>Номер:</b> <code>{order['phone_number']}</code>\n<b>Режим:</b> {mode_text}\n"
                f"<b>Взял(а):</b> @{username}\n\n<i>Заявка #{order_id}</i>")
        await call.message.edit_caption(caption=text, reply_markup=get_client_processing_keyboard(order_id))
    except Exception as e:
        print(f"Ошибка в take_: {e}")


@router.callback_query(F.data.startswith("success_"))
async def process_success_number(call: CallbackQuery):
    try:
        await call.answer()
        order_id = int(call.data.split("_")[1])
        order = await get_order(order_id)

        if order['client_id'] != call.from_user.id and not await is_admin(call.from_user.id):
            return await call.answer("Это не ваш номер!", show_alert=True)

        if order['mode'] == 'no_hold':
            price = await process_payment(order_id)
            emoji = get_emoji_for_operator(order['op_name'])
            text = (f"✅ <b>Номер — Встал</b> ✅\n\n<b>Оператор:</b> {emoji} {order['op_name']}\n"
                    f"<b>Номер:</b> <code>{order['phone_number']}</code>\n<b>💰 Оплата начислена:</b> ${price:.2f}\n\n<i>Заявка #{order_id} завершена</i>")
            await call.message.edit_caption(caption=text, reply_markup=None)

            try:
                await call.bot.send_message(chat_id=order['supplier_id'],
                                            text=f"✅ <b>Ваш номер {order['phone_number']} успешно продан!</b>\nНачислено: ${price:.2f}")
            except:
                pass
        else:
            hold_end = await start_hold(order_id)
            time_str = hold_end.strftime("%H:%M")
            emoji = get_emoji_for_operator(order['op_name'])
            text = (f"⏳ <b>Номер ушел в ХОЛД</b> ⏳\n\n<b>Оператор:</b> {emoji} {order['op_name']}\n"
                    f"<b>Номер:</b> <code>{order['phone_number']}</code>\n<b>Окончание:</b> ~{time_str} (МСК)\n\n<i>Деньги будут начислены автоматически!</i>")
            await call.message.edit_caption(caption=text, reply_markup=None)
    except Exception as e:
        print(f"Ошибка в success_: {e}")


@router.callback_query(F.data.startswith("fail_"))
async def process_fail_number(call: CallbackQuery):
    try:
        await call.answer()
        order_id = int(call.data.split("_")[1])
        order = await get_order(order_id)

        if order['client_id'] != call.from_user.id and not await is_admin(call.from_user.id):
            return await call.answer("Это не ваш номер!", show_alert=True)

        await update_order_status(order_id, 'cancelled')
        text = (
            f"❌ <b>Номер — Брак</b> ❌\n\n<b>Номер:</b> <code>{order['phone_number']}</code>\n<i>Заявка #{order_id} отклонена</i>")
        await call.message.edit_caption(caption=text, reply_markup=None)
    except Exception as e:
        print(f"Ошибка в fail_: {e}")


# ==================================================
# === ПАНЕЛЬ АДМИНИСТРАТОРА (/admin) ===============
# ==================================================

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await is_admin(message.from_user.id): return
    await message.answer("👑 <b>Панель Администратора</b>\n\nВыберите нужный раздел:",
                         reply_markup=get_admin_menu_keyboard())


@router.callback_query(F.data == "admin_close")
async def admin_close(call: CallbackQuery):
    await call.message.delete()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(call: CallbackQuery):
    await call.answer()
    stats = await get_admin_stats()
    text = (
        "📊 <b>Общая статистика:</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['users']}</b>\n"
        f"📦 Всего загружено симок: <b>{stats['orders']}</b>\n"
        f"💳 Ожидают выплаты: <b>{stats['withdrawals']}</b> заявок\n"
    )
    await call.message.edit_text(text, reply_markup=get_admin_menu_keyboard())


@router.callback_query(F.data == "admin_withdraws")
async def admin_withdraws(call: CallbackQuery):
    await call.answer()

    withdrawals = await get_pending_withdrawals(1)

    if not withdrawals:
        return await call.message.edit_text("✅ Нет новых заявок на вывод средств.",
                                            reply_markup=get_admin_menu_keyboard())

    wd = withdrawals[0]
    text = (
        f"💳 <b>Заявка на вывод #{wd['id']}</b>\n\n"
        f"👤 ID Пользователя: <code>{wd['user_id']}</code>\n"
        f"💰 Сумма: <b>${wd['amount']:.2f}</b>\n"
        f"📬 Кошелек:\n<code>{wd['wallet']}</code>\n\n"
        f"<i>Сделайте перевод на указанный кошелек и нажмите кнопку.</i>"
    )
    await call.message.edit_text(text, reply_markup=get_admin_withdraw_decision(wd['id']))


@router.callback_query(F.data.startswith("wd_pay_"))
async def admin_withdraw_pay(call: CallbackQuery):
    wd_id = int(call.data.split("_")[2])
    wd = await get_withdrawal_by_id(wd_id)

    if not wd or wd['status'] != 'pending':
        return await call.answer("Заявка уже обработана!", show_alert=True)

    await process_withdrawal(wd_id, 'paid')
    await call.answer("Выплата подтверждена!")

    try:
        await call.bot.send_message(wd['user_id'],
                                    f"✅ <b>Выплата ${wd['amount']:.2f} успешно переведена на ваш кошелек!</b>")
    except:
        pass

    await admin_withdraws(call)


@router.callback_query(F.data.startswith("wd_rej_"))
async def admin_withdraw_reject(call: CallbackQuery):
    wd_id = int(call.data.split("_")[2])
    wd = await get_withdrawal_by_id(wd_id)

    if not wd or wd['status'] != 'pending':
        return await call.answer("Заявка уже обработана!", show_alert=True)

    await process_withdrawal(wd_id, 'rejected', wd['user_id'], wd['amount'])
    await call.answer("В выплате отказано, деньги возвращены на баланс.")

    try:
        await call.bot.send_message(wd['user_id'],
                                    f"❌ <b>Отказ в выплате ${wd['amount']:.2f}.</b> Средства возвращены на ваш баланс в боте.")
    except:
        pass

    await admin_withdraws(call)


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text(
        "📢 <b>Рассылка сообщений</b>\n\n"
        "Отправьте мне сообщение (текст, фото или видео с текстом), которое нужно разослать всем пользователям бота.\n\n"
        "<i>Для отмены напишите слово:</i> <code>отмена</code>",
        reply_markup=None
    )
    await state.set_state(AdminState.waiting_for_broadcast)


@router.message(AdminState.waiting_for_broadcast)
async def admin_broadcast_send(message: Message, state: FSMContext):
    if message.text and message.text.lower() == 'отмена':
        await state.clear()
        return await message.answer("❌ Рассылка отменена.", reply_markup=get_main_menu())

    user_ids = await get_all_user_ids()
    success = 0
    failed = 0

    await message.answer(f"🚀 Начинаю рассылку для {len(user_ids)} пользователей... Это может занять какое-то время.")

    for uid in user_ids:
        try:
            await message.copy_to(chat_id=uid)
            success += 1
        except Exception:
            failed += 1

    await state.clear()
    await message.answer(
        f"✅ <b>Рассылка успешно завершена!</b>\n\n"
        f"Доставлено: <b>{success}</b>\n"
        f"Ошибок (заблокировали бота): <b>{failed}</b>",
        reply_markup=get_main_menu()
    )