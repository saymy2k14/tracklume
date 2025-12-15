from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import Database

def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗳️ Голосовать")],
            [KeyboardButton(text="📊 Мои голоса")],
            [KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_admin_main_menu():
    """Главное меню для администраторов"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🗳️ Голосовать")],
            [KeyboardButton(text="📊 Мои голоса"), KeyboardButton(text="🏆 Результаты")],
            [KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )

def get_nominations_keyboard():
    """Клавиатура номинаций для обычного голосования"""
    db = Database()
    nominations = db.get_nominations()
    keyboard = []
    
    for nom_id, name in nominations:
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"vote_nom_{nom_id}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_participants_keyboard(nomination_id):
    """Клавиатура участников для обычного голосования"""
    db = Database()
    participants = db.get_participants(nomination_id)
    keyboard = []
    
    for part_id, name in participants:
        keyboard.append([InlineKeyboardButton(text=name, callback_data=f"vote_part_{part_id}")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад к номинациям", callback_data="back_to_nominations")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить участника"), KeyboardButton(text="🗑️ Удалить участника")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Кто голосовал")],
            [KeyboardButton(text="🔙 Главное меню")]
        ],
        resize_keyboard=True
    )

def back_to_main_inline_keyboard():
    """Inline клавиатура для возврата в главное меню (используется в edit_text)"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_main")]]
    )