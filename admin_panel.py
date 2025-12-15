from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import Database
from keyboards import get_admin_keyboard, get_main_menu
from config import ADMINS

class AdminStates(StatesGroup):
    waiting_for_nomination_add = State()
    waiting_for_participant_name = State()
    waiting_for_nomination_delete = State()

router = Router()

def get_nominations_keyboard_admin(action):
    """Клавиатура номинаций для админ-панели"""
    db = Database()
    nominations = db.get_nominations()
    keyboard = []
    
    for nom_id, name in nominations:
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"admin_{action}_{nom_id}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_participants_for_deletion(nomination_id):
    """Получить список участников для удаления"""
    db = Database()
    participants = db.get_participants(nomination_id)
    
    if not participants:
        return None
    
    keyboard = []
    for part_id, name in participants:
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"admin_delete_part_{part_id}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back_to_delete")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMINS:
        await message.answer("⛔ У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "👨‍💻 Админ-панель",
        reply_markup=get_admin_keyboard()
    )

@router.message(F.text == "➕ Добавить участника")
async def add_participant_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    
    await message.answer(
        "Выберите номинацию для добавления участника:",
        reply_markup=get_nominations_keyboard_admin("add")
    )
    await state.set_state(AdminStates.waiting_for_nomination_add)

@router.callback_query(F.data.startswith("admin_add_"))
async def select_nomination_for_add(callback: CallbackQuery, state: FSMContext):
    nomination_id = int(callback.data.split("_")[2])
    await state.update_data(nomination_id=nomination_id)
    
    db = Database()
    nominations = db.get_nominations()
    nomination_name = next((name for id, name in nominations if id == nomination_id), "Неизвестная номинация")
    
    await callback.message.edit_text(
        f"Номинация: <b>{nomination_name}</b>\n\nВведите имя участника:"
    )
    await state.set_state(AdminStates.waiting_for_participant_name)

@router.message(AdminStates.waiting_for_participant_name)
async def add_participant_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    nomination_id = data['nomination_id']
    participant_name = message.text.strip()
    
    if not participant_name:
        await message.answer("❌ Имя участника не может быть пустым. Попробуйте еще раз:")
        return
    
    db = Database()
    try:
        db.add_participant(nomination_id, participant_name)
        
        # Получаем название номинации для красивого сообщения
        nominations = db.get_nominations()
        nomination_name = next((name for id, name in nominations if id == nomination_id), "")
        
        await message.answer(
            f"✅ Участник <b>'{participant_name}'</b> успешно добавлен в номинацию <b>'{nomination_name}'</b>!",
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при добавлении участника: {str(e)}",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

@router.message(F.text == "🗑️ Удалить участника")
async def delete_participant_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMINS:
        return
    
    await message.answer(
        "Выберите номинацию для удаления участника:",
        reply_markup=get_nominations_keyboard_admin("delete")
    )
    await state.set_state(AdminStates.waiting_for_nomination_delete)

@router.callback_query(F.data.startswith("admin_delete_"))
async def select_nomination_for_deletion(callback: CallbackQuery, state: FSMContext):
    # Проверяем, это номинация или участник
    data_parts = callback.data.split("_")
    
    if len(data_parts) == 3:  # admin_delete_X
        nomination_id = int(data_parts[2])
        
        db = Database()
        participants = db.get_participants(nomination_id)
        nominations = db.get_nominations()
        nomination_name = next((name for id, name in nominations if id == nomination_id), "")
        
        if not participants:
            await callback.message.edit_text(
                f"❌ В номинации <b>'{nomination_name}'</b> пока нет участников для удаления.",
                reply_markup=get_nominations_keyboard_admin("delete")
            )
            return
        
        keyboard = get_participants_for_deletion(nomination_id)
        await callback.message.edit_text(
            f"Номинация: <b>{nomination_name}</b>\n\nВыберите участника для удаления:",
            reply_markup=keyboard
        )
    
    elif len(data_parts) == 4 and data_parts[2] == "part":  # admin_delete_part_X
        participant_id = int(data_parts[3])
        
        db = Database()
        participant_info = db.get_participant_info(participant_id)
        
        if participant_info:
            participant_name, nomination_name, nomination_id = participant_info
            db.delete_participant(participant_id)
            
            # Используем answer вместо edit_text для ReplyKeyboardMarkup
            await callback.message.delete()
            await callback.message.answer(
                f"✅ Участник <b>'{participant_name}'</b> успешно удален из номинации <b>'{nomination_name}'</b>!",
                reply_markup=get_admin_keyboard()
            )
        else:
            await callback.message.delete()
            await callback.message.answer(
                "❌ Участник не найден!",
                reply_markup=get_admin_keyboard()
            )
        
        await state.clear()

@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message):
    if message.from_user.id not in ADMINS:
        return
    
    db = Database()
    results = db.get_vote_results()
    
    if not results:
        await message.answer("📊 Голосов пока нет")
        return
    
    current_nomination = ""
    text = "📊 <b>Результаты голосования:</b>\n\n"
    
    for nom_name, part_name, votes in results:
        if nom_name != current_nomination:
            text += f"<b>{nom_name}:</b>\n"
            current_nomination = nom_name
        
        if part_name:
            text += f"  {part_name}: {votes} голосов\n"
        else:
            text += "  Нет участников\n"
    
    total_votes = db.get_total_votes_count()
    text += f"\n<b>Всего голосов:</b> {total_votes}"
    
    await message.answer(text)

@router.message(F.text == "👥 Кто голосовал")
async def show_voters(message: Message):
    if message.from_user.id not in ADMINS:
        return
    
    db = Database()
    votes = db.get_voters_info()
    
    if not votes:
        await message.answer("📝 Голосов пока нет")
        return
    
    # Группируем по пользователям
    voters = {}
    for user_id, nomination, participant, first_name, last_name, username in votes:
        if user_id not in voters:
            voters[user_id] = {
                'name': f"{first_name or ''} {last_name or ''}".strip() or 'Неизвестно',
                'username': f"@{username}" if username else "нет username",
                'votes': []
            }
        voters[user_id]['votes'].append(f"{nomination}: {participant}")
    
    # Формируем сообщение
    text = "👥 <b>Информация о голосующих:</b>\n\n"
    for user_id, data in voters.items():
        text += f"🆔 ID: {user_id}\n"
        text += f"👤 Имя: {data['name']}\n"
        text += f"📱 Username: {data['username']}\n"
        text += "🗳️ Голоса:\n"
        for vote in data['votes']:
            text += f"  • {vote}\n"
        text += "─" * 30 + "\n\n"
    
    # Разбиваем на части если сообщение слишком длинное
    if len(text) > 4096:
        parts = [text[i:i+4096] for i in range(0, len(text), 4096)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(text)

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    # Используем answer вместо edit_text для ReplyKeyboardMarkup
    await callback.message.delete()
    await callback.message.answer(
        "👨‍💻 Админ-панель",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(F.data == "admin_back_to_delete")
async def admin_back_to_delete(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Выберите номинацию для удаления участника:",
        reply_markup=get_nominations_keyboard_admin("delete")
    )
    await state.set_state(AdminStates.waiting_for_nomination_delete)

@router.message(F.text == "🔙 Главное меню")
async def admin_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏆 Главное меню:",
        reply_markup=get_main_menu()
    )