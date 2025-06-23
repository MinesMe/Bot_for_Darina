# app/handlers/favorites.py

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold

from ..database import requests as db
from .. import keyboards as kb
from ..lexicon import Lexicon

router = Router()

class FavoritesFSM(StatesGroup):
    waiting_for_artist_name = State()

async def show_favorites_menu(message: Message, lexicon: Lexicon, favorites: list):
    """Отображает список избранных артистов и кнопки управления."""
    
    if not favorites:
        text = lexicon.get('favorites_menu_header_empty')
    else:
        fav_list = "\n".join(f"⭐ {hbold(fav.name)}" for fav in favorites)
        text = lexicon.get('favorites_menu_header').format(favorites_list=fav_list)
    
    # ИЗМЕНЕНИЕ: Передаем `favorites` в клавиатуру, чтобы она знала, показывать ли кнопку "Удалить"
    await message.answer(text, reply_markup=kb.get_favorites_menu_keyboard(lexicon, favorites), parse_mode="HTML")

@router.message(F.text.in_(["⭐ Избранное", "⭐ Favorites"]))
async def menu_favorites(message: Message, state: FSMContext):
    await state.clear()
    lexicon = Lexicon(message.from_user.language_code)
    # Делаем запрос здесь, в точке входа
    user_favorites = await db.get_user_favorites(message.from_user.id)
    await show_favorites_menu(message, lexicon, user_favorites)

@router.callback_query(F.data == "add_to_favorites")
async def cq_add_to_favorites_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(FavoritesFSM.waiting_for_artist_name)
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.edit_text(lexicon.get('favorites_enter_name_prompt'))
    await callback.answer()

@router.message(FavoritesFSM.waiting_for_artist_name, F.text)
async def process_favorite_artist_search(message: Message, state: FSMContext):
    lexicon = Lexicon(message.from_user.language_code)
    found_artists = await db.find_artists_fuzzy(message.text)
    
    if not found_artists:
        await message.answer(
            lexicon.get('favorites_not_found'),
            reply_markup=kb.get_favorites_not_found_keyboard(lexicon)
        )
    else:
        await message.answer(
            lexicon.get('favorites_found_prompt'),
            reply_markup=kb.get_found_artists_for_favorites_keyboard(found_artists, lexicon)
        )

@router.callback_query(F.data.startswith("add_fav_artist:"))
async def cq_add_artist_to_favorites(callback: CallbackQuery, state: FSMContext):
    """Добавляет выбранного артиста в избранное и обновляет меню."""
    artist_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    # 1. Добавляем в базу
    await db.add_artist_to_favorites(user_id=user_id, artist_id=artist_id)
    
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.answer(lexicon.get('favorites_added_alert'), show_alert=True)
    await state.clear()
    
    # 2. ПОЛУЧАЕМ АКТУАЛЬНЫЙ СПИСОК ИЗБРАННОГО *ПОСЛЕ* ДОБАВЛЕНИЯ
    updated_favorites = await db.get_user_favorites(user_id)
    
    # 3. Удаляем старое сообщение с кнопками
    await callback.message.delete()
    
    # 4. Вызываем функцию показа меню с уже готовым, актуальным списком
    await show_favorites_menu(callback.message, lexicon, updated_favorites)

@router.callback_query(F.data == "remove_from_favorites")
async def cq_remove_from_favorites_start(callback: CallbackQuery):
    # Этот хэндлер работает нормально, так как он только читает данные
    lexicon = Lexicon(callback.from_user.language_code)
    favorites = await db.get_user_favorites(callback.from_user.id)
    if not favorites:
        await callback.answer(lexicon.get('favorites_remove_empty_alert'), show_alert=True)
        return

    await callback.message.edit_text(
        lexicon.get('favorites_remove_prompt'),
        reply_markup=kb.get_remove_from_favorites_keyboard(favorites, lexicon)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("remove_fav_artist:"))
async def cq_remove_artist_from_favorites(callback: CallbackQuery, state: FSMContext):
    """Удаляет выбранного артиста и обновляет меню."""
    artist_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    # 1. Удаляем из базы
    await db.remove_artist_from_favorites(user_id=user_id, artist_id=artist_id)
    
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.answer(lexicon.get('favorites_removed_alert'), show_alert=True)
    
    # 2. ПОЛУЧАЕМ АКТУАЛЬНЫЙ СПИСОК *ПОСЛЕ* УДАЛЕНИЯ
    updated_favorites = await db.get_user_favorites(user_id)
    
    # 3. Удаляем старое сообщение с кнопками
    await callback.message.delete()
    
    # 4. Вызываем функцию показа меню с актуальным списком
    await show_favorites_menu(callback.message, lexicon, updated_favorites) 
    
@router.callback_query(F.data == "back_to_favorites_menu")
async def cq_back_to_favorites_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    lexicon = Lexicon(callback.from_user.language_code)
    user_favorites = await db.get_user_favorites(callback.from_user.id)
    await show_favorites_menu(callback.message, lexicon, user_favorites)