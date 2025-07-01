# app/handlers/favorites.py


import logging
from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold
from aiogram.enums import ParseMode
from aiogram.filters import or_f
from aiogram.exceptions import TelegramBadRequest

# --- ИЗМЕНЕНИЕ: Убираем лишние импорты и добавляем нужные ---
from ..database.requests import requests as db
from app import keyboards as kb
from ..lexicon import Lexicon
from ..database.models import Artist
from app.utils.utils import format_events_by_artist_with_region_split
from app.handlers.states import FavoritesFSM, AddToSubsFSM

router = Router()


# --- ХЕЛПЕРЫ ДЛЯ ПОКАЗА ЭКРАНОВ ---

async def show_favorites_list(callback_or_message: Message | CallbackQuery, state: FSMContext, show_back_button: bool = False):
    """Отображает главный экран "Избранного" со списком артистов."""
    await state.set_state(FavoritesFSM.viewing_list)
    
    target_obj = callback_or_message.message if isinstance(callback_or_message, CallbackQuery) else callback_or_message
    user_lang = await db.get_user_lang(callback_or_message.from_user.id)
    lexicon = Lexicon(user_lang)
    # --- ИЗМЕНЕНИЕ --- Удален отладочный print()
    favorites = await db.get_user_favorites(callback_or_message.from_user.id)
    
    
    text = lexicon.get('favorites_list_prompt') if favorites else lexicon.get('favorites_menu_header_empty')
    markup = kb.get_favorites_list_keyboard(favorites, lexicon,show_back_button)
    
    action = target_obj.edit_text if isinstance(callback_or_message, CallbackQuery) else target_obj.answer
    try:
        await action(text, reply_markup=markup, parse_mode="HTML")
    except Exception:
        await target_obj.answer(text, reply_markup=markup, parse_mode="HTML")

    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.answer()

async def show_single_favorite_menu(chat_id: int, message_id: int, user_id: int, bot: Bot, state: FSMContext):
    """Показывает меню управления для ОДНОГО артиста, ID которого берется из FSM."""
    data = await state.get_data()
    artist_id = data.get("current_artist_id")
    user_lang = await db.get_user_lang(user_id) or 'en'
    lexicon = Lexicon(user_lang)

    if not artist_id:
        # Здесь мы не можем показать список, так как у нас нет callback'а
        # Просто логируем ошибку
        logging.error(f"Артист не найден в state для user_id={user_id}")
        return

    async with db.async_session() as session:
        artist = await session.get(Artist, artist_id)
    
    if not artist:
        # Аналогично, просто логируем
        logging.error(f"Артист {artist_id} не найден в БД для user_id={user_id}")
        return

    await state.set_state(FavoritesFSM.viewing_artist)
    await state.update_data(artist_name=artist.name)
    text = lexicon.get('favorite_artist_menu_prompt').format(artist_name=hbold(artist.name))
    markup = kb.get_single_favorite_manage_keyboard(artist_id, lexicon)
    
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup,
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        # Если не удалось отредактировать, это уже не критично в данном флоу
        logging.warning(f"Не удалось отредактировать сообщение {message_id} для показа меню артиста.")


# --- ХЭНДЛЕРЫ ---

# @router.message(F.text.in_(["⭐ Избранное", "⭐ Favorites"]))
# async def menu_favorites(message: Message, state: FSMContext):
#     """Точка входа в раздел. Очищает состояние."""
#     await state.clear()
#     await show_favorites_list(message, state)

@router.callback_query(FavoritesFSM.viewing_list, F.data.startswith("view_favorite:"))
async def cq_view_favorite_artist(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Переход из общего списка в меню конкретного артиста."""
    artist_id = int(callback.data.split(":")[1])
    await state.update_data(current_artist_id=artist_id)
    # Вызываем обновленный хелпер
    await show_single_favorite_menu(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        user_id=callback.from_user.id,
        bot=bot,
        state=state
    )


@router.callback_query(FavoritesFSM.viewing_artist, F.data.startswith("view_events_for_favorite:"))
async def cq_view_events_for_favorite(callback: CallbackQuery, state: FSMContext):
    """
    Показывает предстоящие события для выбранного артиста,
    разделяя их на отслеживаемые и прочие регионы.
    """
    lexicon = Lexicon(callback.from_user.language_code)
    artist_id = int(callback.data.split(":")[1])
    
    # Сохраняем ID артиста и ID сообщения для редактирования
    await state.update_data(
        current_artist_id=artist_id,
        return_to_favorite_artist_id=artist_id,
        message_to_edit_id=callback.message.message_id
    )
    user_id = callback.from_user.id
    
    all_future_events = await db.get_future_events_for_artists([artist_id])
    favorite_details = await db.get_favorite_details(user_id, artist_id)
    tracked_regions = favorite_details.regions if favorite_details else []
    
    data = await state.get_data()
    artist_name = data.get("artist_name", lexicon.get('unknown_artist'))

    response_text, event_ids_to_subscribe = await format_events_by_artist_with_region_split(
        events=all_future_events,
        tracked_regions=tracked_regions,
        lexicon=lexicon
    )
    
    await state.set_state(FavoritesFSM.viewing_artist_events)
    await state.update_data(last_shown_event_ids=event_ids_to_subscribe or None)
    
    header_text = lexicon.get('favorite_events_header').format(artist_name=hbold(artist_name))
    final_text_parts = [header_text]
    
    actions_keyboard = kb.get_afisha_actions_keyboard(lexicon, show_back_button=True)

    if response_text:
        final_text_parts.append(response_text)
    else:
        final_text_parts.append(lexicon.get('no_future_events_for_favorites'))

    final_text = "\n\n".join(final_text_parts)

    try:
        # Пытаемся отредактировать текущее сообщение
        await callback.message.edit_text(
            final_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=actions_keyboard
        )
    except TelegramBadRequest as e:
        if "message is too long" in str(e):
            # Если текст слишком длинный, редактируем только заголовок и отправляем тело отдельно
            await callback.message.edit_text(header_text)
            await callback.message.answer(
                response_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
                reply_markup=actions_keyboard
            )
        else:
            # Другие ошибки (например, message not modified) просто игнорируем
            pass
    
    await callback.answer()

@router.callback_query(FavoritesFSM.viewing_artist_events, F.data == "add_events_to_subs")
async def cq_add_to_subs_from_favorites(callback: CallbackQuery, state: FSMContext):
    """
    Начинает процесс добавления в подписки ИЗ ИЗБРАННОГО.
    Сохраняет callback_id для alert'а и отправляет новое сообщение.
    """
    data = await state.get_data()
    lexicon = Lexicon(callback.from_user.language_code)
    if not data.get("last_shown_event_ids"):
        await callback.answer(lexicon.get('afisha_must_find_events_first_alert'), show_alert=True)
        return

    await state.set_state(AddToSubsFSM.waiting_for_event_numbers)
    
    prompt_message = await callback.message.answer(lexicon.get('subs_enter_numbers_prompt'))
    
    # Сохраняем ID callback'а и нового сообщения
    await state.update_data(
        prompt_message_id=prompt_message.message_id,
        callback_query_id_for_alert=callback.id
    )
    await callback.answer()

@router.callback_query(or_f(FavoritesFSM.viewing_artist_events, AddToSubsFSM.waiting_for_event_numbers), F.data == "back_to_single_favorite_view")
async def cq_back_to_single_favorite_from_events(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """
    Возвращает пользователя из просмотра/добавления событий обратно в меню управления артистом.
    """
    # ... (логика удаления временных сообщений) ...
    data = await state.get_data()
    prompt_message_id = data.get('prompt_message_id')
    if prompt_message_id:
        try:
            await bot.delete_message(callback.from_user.id, prompt_message_id)
        except TelegramBadRequest:
            pass

    await state.update_data(last_shown_event_ids=None, prompt_message_id=None, callback_query_id_for_alert=None)
    
    # Вызываем обновленный хелпер
    await show_single_favorite_menu(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        user_id=callback.from_user.id,
        bot=bot,
        state=state
    )

@router.callback_query(F.data == "back_to_favorites_list")
async def cq_back_to_favorites_list(callback: CallbackQuery, state: FSMContext):
    """Возврат из меню артиста в общий список."""
    await show_favorites_list(callback, state)

@router.callback_query(
    or_f(FavoritesFSM.viewing_artist, FavoritesFSM.viewing_artist_events), 
    F.data.startswith("delete_favorite:")
)
async def cq_delete_favorite_artist(callback: CallbackQuery, state: FSMContext):
    """Удаляет артиста и возвращает в обновленный общий список."""
    # --- НОВОЕ: Очищаем данные сессии просмотра событий, если они были ---
    await state.update_data(last_shown_event_ids=None, messages_to_delete_on_expire=None)
    # --- КОНЕЦ НОВОГО ---
    
    data = await state.get_data()
    artist_id = data.get("current_artist_id")
    await db.remove_artist_from_favorites(user_id=callback.from_user.id, artist_id=artist_id)
    
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.answer(lexicon.get('favorites_removed_alert'), show_alert=True)
    await show_favorites_list(callback, state)


@router.callback_query(FavoritesFSM.editing_mobility, F.data.startswith("toggle_region:"))
async def cq_toggle_mobility_region_from_fav(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора/снятия региона."""
    region_name = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_regions", [])
    user_lang = callback.from_user.language_code
    lexicon = Lexicon(user_lang)
    
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
            back_callback="back_to_single_favorite_view",
            lexicon=lexicon
        )
    )
    await callback.answer()

@router.callback_query(
    or_f(FavoritesFSM.viewing_artist, FavoritesFSM.viewing_artist_events), 
    F.data.startswith("edit_fav_regions:")
)
async def cq_edit_favorite_regions_start(callback: CallbackQuery, state: FSMContext):
    """Начинает флоу редактирования регионов для одного избранного."""
    # --- НОВОЕ: Очищаем данные сессии просмотра событий, если они были ---
    await state.update_data(last_shown_event_ids=None, messages_to_delete_on_expire=None)
    # --- КОНЕЦ НОВОГО ---
    
    user_lang = callback.from_user.language_code
    lexicon = Lexicon(user_lang)
    artist_id = int(callback.data.split(":")[1])
    await state.set_state(FavoritesFSM.editing_mobility)
    
    favorite_details = await db.get_favorite_details(callback.from_user.id, artist_id)
    current_regions = favorite_details.regions if favorite_details else []
    
    await state.update_data(selected_regions=current_regions)
    all_countries = await db.get_countries()
    
    data = await state.get_data()
    artist_name = data.get("artist_name", "...")
    
    await callback.message.edit_text(
        lexicon.get('favorite_edit_regions_prompt').format(artist_name=hbold(artist_name)),
        reply_markup=kb.get_region_selection_keyboard(
            all_countries, 
            current_regions,
            finish_callback="finish_fav_regions_edit",
            back_callback="back_to_single_favorite_view",
            lexicon=lexicon
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
    lexicon = Lexicon(callback.from_user.language_code) # --- ИЗМЕНЕНИЕ --- Lexicon определен в начале
    
    if not regions:
        # --- ИЗМЕНЕНИЕ --- Текст заменен на вызов существующего ключа lexicon.get()
        await callback.answer(lexicon.get('no_regions_selected_alert'), show_alert=True)
        return

    await db.update_favorite_regions(callback.from_user.id, artist_id, regions)
    
    await callback.answer(lexicon.get('favorite_regions_updated_alert'), show_alert=True)
    
    await show_single_favorite_menu(callback, state)

@router.callback_query(FavoritesFSM.editing_mobility, F.data == "finish_mobility_edit_from_fav")
async def cq_finish_mobility_edit_from_fav(callback: CallbackQuery, state: FSMContext):
    """Сохраняет настройки мобильности и возвращает в меню артиста."""
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    await db.set_general_mobility(callback.from_user.id, regions)
    
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.answer(lexicon.get('mobility_saved_alert'), show_alert=True)
    
    await show_single_favorite_menu(callback, state)

@router.callback_query(FavoritesFSM.editing_mobility, F.data == "back_to_single_favorite_view")
async def cq_back_to_single_favorite(callback: CallbackQuery, state: FSMContext):
    """Возврат из редактирования мобильности в меню артиста."""
    await show_single_favorite_menu(callback, state)

# Для нотифаера
@router.callback_query(F.data.startswith("add_to_subs_from_notify:"))
async def cq_add_to_subs_from_notify(callback: CallbackQuery):
    """Ловит нажатие на кнопку 'Добавить в подписки' из уведомления."""
    lexicon = Lexicon(callback.from_user.language_code) # --- ИЗМЕНЕНИЕ --- Lexicon определен в начале
    try:
        event_id = int(callback.data.split(":")[1])
        await db.add_events_to_subscriptions_bulk(callback.from_user.id, [event_id])
        # --- ИЗМЕНЕНИЕ --- Текст заменен на вызов lexicon.get()
        await callback.answer(lexicon.get('event_added_to_subs_alert'), show_alert=True)
    except (ValueError, IndexError):
        # --- ИЗМЕНЕНИЕ --- Текст заменен на вызов lexicon.get()
        await callback.answer(lexicon.get('error_adding_event_to_subs_alert'), show_alert=True)