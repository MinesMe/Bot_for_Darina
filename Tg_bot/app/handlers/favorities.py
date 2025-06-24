# app/handlers/favorites.py

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold

from ..database import requests as db
from .. import keyboards as kb
from ..lexicon import Lexicon
from ..database.models import Artist

router = Router()

class FavoritesFSM(StatesGroup):
    viewing_list = State()
    viewing_artist = State()
    editing_mobility = State()

# --- ХЕЛПЕРЫ ДЛЯ ПОКАЗА ЭКРАНОВ ---

async def show_favorites_list(callback_or_message: Message | CallbackQuery, state: FSMContext):
    """Отображает главный экран "Избранного" со списком артистов."""
    await state.set_state(FavoritesFSM.viewing_list)
    
    target_obj = callback_or_message.message if isinstance(callback_or_message, CallbackQuery) else callback_or_message
    lexicon = Lexicon(callback_or_message.from_user.language_code)
    print(target_obj.from_user.id)
    favorites = await db.get_user_favorites(callback_or_message.from_user.id)
    
    
    text = lexicon.get('favorites_list_prompt') if favorites else lexicon.get('favorites_menu_header_empty')
    markup = kb.get_favorites_list_keyboard(favorites, lexicon)
    
    action = target_obj.edit_text if isinstance(callback_or_message, CallbackQuery) else target_obj.answer
    try:
        await action(text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        await target_obj.answer(text, reply_markup=markup, parse_mode="HTML")

    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.answer()

async def show_single_favorite_menu(callback: CallbackQuery, state: FSMContext):
    """Показывает меню управления для ОДНОГО артиста, ID которого берется из FSM."""
    data = await state.get_data()
    artist_id = data.get("current_artist_id")
    if not artist_id:
        await callback.answer("Ошибка: не удалось найти артиста. Возвращаю в список.", show_alert=True)
        await show_favorites_list(callback, state)
        return

    async with db.async_session() as session:
        artist = await session.get(Artist, artist_id)
    
    if not artist:
        await callback.answer("Артист больше не найден в базе.", show_alert=True)
        await show_favorites_list(callback, state)
        return

    await state.set_state(FavoritesFSM.viewing_artist)
    lexicon = Lexicon(callback.from_user.language_code)
    await state.update_data(artist_name=artist.name)
    text = lexicon.get('favorite_artist_menu_prompt').format(artist_name=hbold(artist.name))
    markup = kb.get_single_favorite_manage_keyboard(artist_id, lexicon)
    
    await callback.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    await callback.answer()


# --- ХЭНДЛЕРЫ ---

@router.message(F.text.in_(["⭐ Избранное", "⭐ Favorites"]))
async def menu_favorites(message: Message, state: FSMContext):
    """Точка входа в раздел. Очищает состояние."""
    await state.clear()
    await show_favorites_list(message, state)

@router.callback_query(FavoritesFSM.viewing_list, F.data.startswith("view_favorite:"))
async def cq_view_favorite_artist(callback: CallbackQuery, state: FSMContext):
    """Переход из общего списка в меню конкретного артиста."""
    artist_id = int(callback.data.split(":")[1])
    # Сохраняем контекст в state
    await state.update_data(current_artist_id=artist_id)
    # Вызываем хелпер, который сам возьмет ID из state
    await show_single_favorite_menu(callback, state)

@router.callback_query(F.data == "back_to_favorites_list")
async def cq_back_to_favorites_list(callback: CallbackQuery, state: FSMContext):
    """Возврат из меню артиста в общий список."""
    await show_favorites_list(callback, state)

@router.callback_query(FavoritesFSM.viewing_artist, F.data.startswith("delete_favorite:"))
async def cq_delete_favorite_artist(callback: CallbackQuery, state: FSMContext):
    """Удаляет артиста и возвращает в обновленный общий список."""
    data = await state.get_data()
    artist_id = data.get("current_artist_id")
    await db.remove_artist_from_favorites(user_id=callback.from_user.id, artist_id=artist_id)
    
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.answer(lexicon.get('favorites_removed_alert'), show_alert=True)
    await show_favorites_list(callback, state)

# --- ХЭНДЛЕРЫ РЕДАКТИРОВАНИЯ МОБИЛЬНОСТИ ---

# @router.callback_query(FavoritesFSM.viewing_artist, F.data == "edit_general_mobility_from_fav")
# async def cq_edit_general_mobility_from_fav(callback: CallbackQuery, state: FSMContext):
#     """Переход из меню артиста в редактирование мобильности."""
#     await state.set_state(FavoritesFSM.editing_mobility)
#     current_regions = await db.get_general_mobility(callback.from_user.id) or []
#     await state.update_data(selected_regions=current_regions)
#     all_countries = await db.get_countries()
#     lexicon = Lexicon(callback.from_user.language_code)
    
#     await callback.message.edit_text(
#         lexicon.get('edit_mobility_prompt'),
#         reply_markup=kb.get_region_selection_keyboard(
#             all_countries, current_regions,
#             finish_callback="finish_mobility_edit_from_fav",
#             back_callback="back_to_single_favorite_view"
#         )
#     )
#     await callback.answer()

@router.callback_query(FavoritesFSM.editing_mobility, F.data.startswith("toggle_region:"))
async def cq_toggle_mobility_region_from_fav(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора/снятия региона."""
    region_name = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_regions", [])
    
    if region_name in selected:
        selected.remove(region_name)
    else:
        selected.append(region_name)
        
    await state.update_data(selected_regions=selected)
    all_countries = await db.get_countries()
    
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_region_selection_keyboard(
            all_countries, selected,
            finish_callback="finish_fav_regions_edit",
            back_callback="back_to_single_favorite_view"
        )
    )
    await callback.answer()

@router.callback_query(FavoritesFSM.viewing_artist, F.data.startswith("edit_fav_regions:"))
async def cq_edit_favorite_regions_start(callback: CallbackQuery, state: FSMContext):
    """Начинает флоу редактирования регионов для одного избранного."""
    artist_id = int(callback.data.split(":")[1])
    await state.set_state(FavoritesFSM.editing_mobility)
    
    # Получаем текущие регионы для ЭТОГО избранного
    favorite_details = await db.get_favorite_details(callback.from_user.id, artist_id)
    current_regions = favorite_details.regions if favorite_details else []
    
    await state.update_data(selected_regions=current_regions)
    all_countries = await db.get_countries()
    lexicon = Lexicon(callback.from_user.language_code)
    
    data = await state.get_data()
    artist_name = data.get("artist_name", "...")
    
    await callback.message.edit_text(
        lexicon.get('favorite_edit_regions_prompt').format(artist_name=hbold(artist_name)),
        reply_markup=kb.get_region_selection_keyboard(
            all_countries, 
            current_regions,
            finish_callback="finish_fav_regions_edit",
            back_callback="back_to_single_favorite_view"
        ),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(FavoritesFSM.editing_mobility, F.data == "finish_fav_regions_edit")
async def cq_finish_fav_regions_edit(callback: CallbackQuery, state: FSMContext):
    """Сохраняет новые регионы для избранного и возвращает в меню артиста."""
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    artist_id = data.get("current_artist_id")
    
    if not regions:
        await callback.answer("Нужно выбрать хотя бы один регион!", show_alert=True)
        return

    # Вызываем новую функцию для обновления
    await db.update_favorite_regions(callback.from_user.id, artist_id, regions)
    
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.answer(lexicon.get('favorite_regions_updated_alert'), show_alert=True)
    
    # Возвращаемся в меню артиста
    await show_single_favorite_menu(callback, state)

@router.callback_query(FavoritesFSM.editing_mobility, F.data == "finish_mobility_edit_from_fav")
async def cq_finish_mobility_edit_from_fav(callback: CallbackQuery, state: FSMContext):
    """Сохраняет настройки мобильности и возвращает в меню артиста."""
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    await db.set_general_mobility(callback.from_user.id, regions)
    
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.answer(lexicon.get('mobility_saved_alert'), show_alert=True)
    
    # Возвращаемся в меню артиста
    await show_single_favorite_menu(callback, state)

@router.callback_query(FavoritesFSM.editing_mobility, F.data == "back_to_single_favorite_view")
async def cq_back_to_single_favorite(callback: CallbackQuery, state: FSMContext):
    """Возврат из редактирования мобильности в меню артиста."""
    # Просто вызываем хелпер, который сам возьмет ID из state и все отрисует
    await show_single_favorite_menu(callback, state)