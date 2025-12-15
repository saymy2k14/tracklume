import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config_token import BOT_TOKEN
from database import Database
from keyboards import (
    get_main_menu, get_admin_main_menu, get_nominations_keyboard, 
    get_participants_keyboard, back_to_main_inline_keyboard
)
from admin_panel import router as admin_router
from config import CHANNEL_USERNAME, ADMINS

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(admin_router)

class VotingStates(StatesGroup):
    waiting_for_participant = State()

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMINS

@dp.message(Command("start"))
async def start_command(message: Message):
    if is_admin(message.from_user.id):
        # Для администраторов показываем меню с результатами
        await message.answer(
            "🏆 Добро пожаловать в систему голосования Track Awards!\n\n"
            "👨‍💻 <b>Вы вошли как администратор</b>\n"
            "Выберите действие в главном меню:",
            reply_markup=get_admin_main_menu()
        )
    else:
        # Для обычных пользователей скрываем результаты
        await message.answer(
            "🏆 Добро пожаловать в систему голосования Track Awards!\n\n"
            "Выберите действие в главном меню:",
            reply_markup=get_main_menu()
        )

@dp.message(F.text == "🔙 Главное меню")
async def main_menu(message: Message):
    if is_admin(message.from_user.id):
        await message.answer(
            "🏆 Главное меню:",
            reply_markup=get_admin_main_menu()
        )
    else:
        await message.answer(
            "🏆 Главное меню:",
            reply_markup=get_main_menu()
        )

@dp.message(F.text == "🗳️ Голосовать")
async def start_voting(message: Message):
    # Проверка подписки на канал
    try:
        chat_member = await bot.get_chat_member(CHANNEL_USERNAME, message.from_user.id)
        if chat_member.status in ['left', 'kicked']:
            await message.answer(
                f"⛔ Для голосования необходимо быть подписанным на канал {CHANNEL_USERNAME}",
                reply_markup=get_main_menu() if not is_admin(message.from_user.id) else get_admin_main_menu()
            )
            return
    except Exception as e:
        await message.answer(
            "❌ Ошибка проверки подписки. Попробуйте позже.",
            reply_markup=get_main_menu() if not is_admin(message.from_user.id) else get_admin_main_menu()
        )
        return
    
    await message.answer(
        "Выберите номинацию:",
        reply_markup=get_nominations_keyboard()
    )

@dp.callback_query(F.data == "back_to_nominations")
async def back_to_nominations(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Выберите номинацию:",
        reply_markup=get_nominations_keyboard()
    )

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    # Для edit_text используем answer с reply_markup вместо edit_text
    await callback.message.delete()
    
    if is_admin(callback.from_user.id):
        await callback.message.answer(
            "🏆 Главное меню:",
            reply_markup=get_admin_main_menu()
        )
    else:
        await callback.message.answer(
            "🏆 Главное меню:",
            reply_markup=get_main_menu()
        )

@dp.callback_query(F.data.startswith("vote_nom_"))
async def select_nomination(callback: CallbackQuery, state: FSMContext):
    nomination_id = int(callback.data.split("_")[2])
    
    db = Database()
    participants = db.get_participants(nomination_id)
    
    if not participants:
        await callback.answer("❌ В этой номинации пока нет участников", show_alert=True)
        return
    
    await state.update_data(nomination_id=nomination_id)
    nominations = db.get_nominations()
    nomination_name = next((name for id, name in nominations if id == nomination_id), "")
    
    await callback.message.edit_text(
        f"Номинация: <b>{nomination_name}</b>\n\nВыберите участника:",
        reply_markup=get_participants_keyboard(nomination_id)
    )
    await state.set_state(VotingStates.waiting_for_participant)

@dp.callback_query(F.data.startswith("vote_part_"), VotingStates.waiting_for_participant)
async def vote_for_participant(callback: CallbackQuery, state: FSMContext):
    participant_id = int(callback.data.split("_")[2])
    data = await state.get_data()
    nomination_id = data['nomination_id']
    
    db = Database()
    
    # Получаем информацию о номинации и участнике для красивого сообщения
    nominations = db.get_nominations()
    nomination_name = next((name for id, name in nominations if id == nomination_id), "")
    
    participants = db.get_participants(nomination_id)
    participant_name = next((name for id, name in participants if id == participant_id), "")
    
    success = db.add_vote(
        user_id=callback.from_user.id,
        nomination_id=nomination_id,
        participant_id=participant_id,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        username=callback.from_user.username
    )
    
    if success:
        await callback.message.edit_text(
            f"✅ Ваш голос успешно учтен!\n\n"
            f"<b>Номинация:</b> {nomination_name}\n"
            f"<b>Участник:</b> {participant_name}",
            reply_markup=back_to_main_inline_keyboard()
        )
    else:
        await callback.message.edit_text(
            f"❌ Произошла ошибка при сохранении голоса. Попробуйте еще раз.",
            reply_markup=back_to_main_inline_keyboard()
        )
    
    await state.clear()

@dp.message(F.text == "📊 Мои голоса")
async def show_my_votes(message: Message):
    db = Database()
    votes = db.get_user_votes(message.from_user.id)
    
    if not votes:
        await message.answer(
            "📝 Вы еще не голосовали ни в одной номинации",
            reply_markup=get_main_menu() if not is_admin(message.from_user.id) else get_admin_main_menu()
        )
        return
    
    text = "📊 <b>Ваши голоса:</b>\n\n"
    for nom_name, part_name in votes:
        text += f"• <b>{nom_name}:</b> {part_name}\n"
    
    await message.answer(
        text, 
        reply_markup=get_main_menu() if not is_admin(message.from_user.id) else get_admin_main_menu()
    )

@dp.message(F.text == "🏆 Результаты")
async def show_results(message: Message):
    # Проверяем, является ли пользователь администратором
    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ Просмотр результатов доступен только администраторам\n\n"
            "Итоги голосования будут объявлены 26.12 на твиче(https://www.twitch.tv/smoget69?sr=a)",
            reply_markup=get_main_menu()
        )
        return
    
    db = Database()
    results = db.get_vote_results()
    
    if not results or all(votes == 0 for _, _, votes in results):
        await message.answer(
            "📊 Голосов пока нет",
            reply_markup=get_admin_main_menu()
        )
        return
    
    current_nomination = ""
    text = "🏆 <b>Текущие результаты:</b>\n\n"
    
    for nom_name, part_name, votes in results:
        if nom_name != current_nomination:
            if current_nomination != "":
                text += "\n"
            text += f"<b>{nom_name}:</b>\n"
            current_nomination = nom_name
        
        if part_name:
            text += f"  {part_name}: {votes} голосов\n"
    
    total_votes = db.get_total_votes_count()
    text += f"\n<b>Всего голосов:</b> {total_votes}"
    
    await message.answer(text, reply_markup=get_admin_main_menu())

async def main():
    print("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())