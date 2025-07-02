# app/handlers/subscriptions.py

import asyncio
import logging
from aiogram import Bot, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold
from sqlalchemy import select

from ..database.requests import requests as db
from app import keyboards as kb
from app.utils.utils import format_events_for_response
from .favorities import show_favorites_list 
from ..lexicon import Lexicon
from aiogram.filters import Command
from app.handlers.profile import menu_profile # Импортируем хэндлер профиля для вызоваs

from aiogram.enums import ParseMode
from app.utils.utils import format_events_by_artist # Наш новый форматер
from app.handlers.afisha import AddToSubsFSM, send_long_message
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.base import BaseStorage, StorageKey
# ... (остальные ваши импорты)
from app.services.recommendation import get_recommended_artists
from app.handlers.states import SubscriptionFlow,RecommendationFlow,CombinedFlow
from .search_countries import start_country_search, process_country_input as process_country_search
from aiogram.filters import or_f



router = Router()


async def trigger_recommendation_flow(user_id: int, bot: Bot, state: FSMContext, added_artist_names: list[str]):
    """
    Запускает флоу рекомендаций: запрашивает, отправляет и устанавливает FSM.
    """
    if not added_artist_names:
        return

    # 1. Получаем рекомендации. Эта функция уже возвращает list[dict].
    recommended_artists_dicts = await get_recommended_artists(added_artist_names)
    if not recommended_artists_dicts:
        logging.info(f"Для пользователя {user_id} не найдено рекомендаций на основе {added_artist_names}.")
        return

    # --- ИСПРАВЛЕНИЕ: Убираем лишнее преобразование ---
    # Строка `recommended_artists_dicts = [artist.to_dict() for artist in recommended_artists]` УДАЛЕНА.
    # Мы используем `recommended_artists_dicts` напрямую.

    # 2. Готовим сообщение и клавиатуру
    user_lang = await db.get_user_lang(user_id)
    lexicon = Lexicon(user_lang)
    
    source_artist_str = ", ".join(f"'{name.title()}'" for name in added_artist_names)
    text_header = lexicon.get('recommendations_after_add_favorite').format(artist_name=source_artist_str)
    
    # В клавиатуру передаем наш list[dict]
    keyboard = kb.get_recommended_artists_keyboard(
        recommended_artists_dicts, 
        lexicon,
        set() # <-- Явно указываем, что при первом показе ничего не выбрано
    )

    # 3. Отправляем сообщение и устанавливаем FSM
    try:
        sent_message = await bot.send_message(
            chat_id=user_id,
            text=text_header,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
        
        # Обновляем state, добавляя ID этого сообщения к списку на удаление
        current_messages = (await state.get_data()).get('messages_to_delete_on_combined_finish', [])
        await state.update_data(
            recommended_artists=recommended_artists_dicts,
            current_selection_ids=[],
            recommendation_message_id=sent_message.message_id # Новый ключ
        )
        logging.info(f"--> Данные для рекомендаций добавлены в state для {user_id}")

    except Exception as e:
        logging.error(f"Не удалось запустить флоу рекомендаций для пользователя {user_id}: {e}", exc_info=True)


async def show_events_for_new_favorites(callback: CallbackQuery, state: FSMContext, artist_ids: list[int], artist_names: list[str]):
    """
    Ищет события и ДОБАВЛЯЕТ `last_shown_event_ids` в текущий state.
    """
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)
    found_events = await db.get_future_events_for_artists(artist_ids)
    
    if not found_events:
        no_events_text = "\n\n" + lexicon.get('no_future_events_for_favorites')
        await callback.message.answer(no_events_text)
        return

    response_text, event_ids_to_subscribe = await format_events_by_artist(found_events, artist_names, lexicon)
    
    if not response_text:
        no_events_text = "\n\n" + lexicon.get('no_future_events_for_favorites')
        await callback.message.answer(no_events_text)
        return

    # НЕ устанавливаем state, а только обновляем данные
    await state.update_data(last_shown_event_ids=event_ids_to_subscribe)
    
    sent_messages = await send_long_message(
        message=callback.message, text=response_text, lexicon=lexicon,
        parse_mode=ParseMode.HTML, disable_web_page_preview=True,
        reply_markup=kb.get_afisha_actions_keyboard(lexicon)
    )
    # Добавляем их в state
    current_messages = (await state.get_data()).get('messages_to_delete_on_combined_finish', [])
    await state.update_data(event_messages_ids=sent_messages)

@router.message(F.text.in_(['➕ Добавить в избранное', '➕ Add to Favorites', '➕ Знайсці/дадаць выканаўцу'])) 
async def menu_add_subscriptions(message: Message, state: FSMContext):
    """
    Точка входа в флоу ДОБАВЛЕНИЯ подписки.
    """
    current_data = await state.get_data()
    data_to_keep = {
        'messages_to_delete_on_expire': current_data.get('messages_to_delete_on_expire'),
        'last_shown_event_ids': current_data.get('last_shown_event_ids')
    }
    await state.clear()
    data_to_restore = {k: v for k, v in data_to_keep.items() if v is not None}
    if data_to_restore:
        await state.update_data(data_to_restore)
    user_id = message.from_user.id
    onboarding_done = await db.check_general_geo_onboarding_status(user_id)
    user_lang = await db.get_user_lang(message.from_user.id)
    lexicon = Lexicon(user_lang)

    if not onboarding_done:
        # Если нет - отправляем на онбординг мобильности
        await state.set_state(SubscriptionFlow.general_mobility_onboarding)
        await message.answer(
            lexicon.get('onboarding_mobility_prompt'),
            reply_markup=kb.get_general_onboarding_keyboard(lexicon)
        )
        return
    await state.set_state(SubscriptionFlow.waiting_for_artist_name)
    await state.update_data(pending_favorites=[]) # Инициализируем очередь

    # Проверяем, нужно ли показывать кнопку настройки мобильности
    general_mobility_regions = await db.get_general_mobility(user_id)
    show_setup_button = not bool(general_mobility_regions)

    # Отправляем новое стартовое сообщение
    await message.answer(
        lexicon.get('enter_artist_name_prompt'), # Используем новый текст
        reply_markup=kb.get_artist_input_keyboard(lexicon, show_setup_mobility_button=show_setup_button)
    )

@router.callback_query(F.data == "add_new_subscription")
async def start_subscription_add_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу добавления подписки."""
    user_id = callback.from_user.id
    onboarding_done = await db.check_general_geo_onboarding_status(user_id)
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)
    if not onboarding_done:
        await state.set_state(SubscriptionFlow.general_mobility_onboarding)
        await callback.message.edit_text(
            lexicon.get('onboarding_mobility_prompt'),
            reply_markup=kb.get_general_onboarding_keyboard(lexicon)
        )
    else:
        await state.set_state(SubscriptionFlow.waiting_for_action)
        await state.update_data(pending_favorites=[])
        await callback.message.edit_text(
            lexicon.get('action_prompt_default'),
            reply_markup=kb.get_add_sub_action_keyboard(lexicon)
        )
    await callback.answer()

@router.callback_query(F.data == "cancel_add_to_fav")
async def cq_cancel_add_process(callback: CallbackQuery, state: FSMContext):
    """
    Отменяет текущий процесс, удаляет сообщение с инлайн-клавиатурой
    и возвращает пользователя в главное меню.
    """
    await state.clear()
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)

    try:
        # Пытаемся удалить сообщение, к которому была привязана кнопка
        await callback.message.delete()
        return
    except TelegramBadRequest:
        # Если сообщение уже было удалено или возникла другая ошибка,
        # просто игнорируем ее.
        pass
    
    # Отправляем новое сообщение с приветствием и главным меню
    await callback.message.answer(
        lexicon.get('main_menu_greeting').format(first_name=hbold(callback.from_user.first_name)),
        reply_markup=kb.get_main_menu_keyboard(lexicon),
        parse_mode="HTML"
    )
    
    # Отвечаем на callback, чтобы убрать "часики" на кнопке
    await callback.answer(lexicon.get('cancel_alert'))

@router.callback_query(SubscriptionFlow.general_mobility_onboarding, F.data.in_(['setup_general_mobility', 'skip_general_mobility']))
async def handle_general_onboarding_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора в онбординге общей мобильности."""
    await db.set_general_geo_onboarding_completed(callback.from_user.id)
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)

    if callback.data == 'setup_general_mobility':
        await state.set_state(SubscriptionFlow.selecting_general_regions)
        await state.update_data(selected_regions=[], source_flow="onboarding")
        
        await callback.message.edit_text(
            lexicon.get('general_mobility_selection_prompt'),
            reply_markup=kb.get_region_selection_keyboard(
                selected_regions=[],
                finish_callback="finish_general_selection",
                back_callback="cancel_add_to_fav", # Отмена онбординга = выход
                search_callback="search_for_sub_country", 
                lexicon=lexicon
            )
        )
    else: # skip_general_mobility
        await state.set_state(SubscriptionFlow.waiting_for_artist_name)
        await state.update_data(pending_favorites=[])
        general_mobility_regions = await db.get_general_mobility(callback.from_user.id)
        show_setup_button = not bool(general_mobility_regions)
        await callback.message.edit_text(
            lexicon.get('enter_artist_name_prompt'), 
            reply_markup=kb.get_artist_input_keyboard(lexicon, show_setup_mobility_button=show_setup_button)
        )

@router.callback_query(SubscriptionFlow.selecting_general_regions, F.data == "search_for_general_mobility_country")
async def cq_search_for_general_mobility_country(callback: CallbackQuery, state: FSMContext):
    """Запускает поиск страны для общей мобильности в флоу онбординга."""
    await start_country_search(
        callback,
        state,
        new_state=SubscriptionFlow.waiting_country_input, # Используем то же состояние, что и в других флоу
        back_callback="back_to_general_selection"
    )

@router.callback_query(SubscriptionFlow.waiting_country_input, F.data == "back_to_general_selection")
async def cq_back_to_general_selection(callback: CallbackQuery, state: FSMContext):
    """Возвращает из поиска страны к онбордингу общей мобильности."""
    # Просто пере-вызываем хендлер, который показывает главный экран выбора
    await state.set_state(SubscriptionFlow.selecting_general_regions)
    data = await state.get_data()
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)
    selected_regions = data.get("selected_regions", [])
    
    # Определяем кнопку "Назад" в зависимости от того, откуда пришли
    back_cb = "cancel_add_to_fav" if data.get("source_flow") == "onboarding" else "back_to_artist_input"

    await callback.message.edit_text(
        lexicon.get('general_mobility_selection_prompt'),
        reply_markup=kb.get_region_selection_keyboard(
            selected_regions=selected_regions,
            finish_callback="finish_general_selection",
            back_callback=back_cb,
            search_callback="search_for_sub_country",
            lexicon=lexicon
        )
    )

@router.callback_query(F.data == "cancel_add_to_fav")
async def cq_cancel_add_process(callback: CallbackQuery, state: FSMContext):
    print('here')
    """Отменяет процесс добавления и возвращает в главное меню."""
    await state.clear()
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)
    await callback.message.delete()
    # Здесь можно либо показать главное меню, либо меню "Избранное"
    # Давайте вернем в главное меню, это универсальнее
    await callback.message.answer(
        lexicon.get('main_menu_greeting').format(first_name=hbold(callback.from_user.first_name)),
        reply_markup=kb.get_main_menu_keyboard(lexicon),
        parse_mode="HTML"
    )
    await callback.answer(lexicon.get('cancel_alert'))

@router.callback_query(SubscriptionFlow.waiting_for_artist_name, F.data == "setup_general_mobility")
async def handle_setup_general_mobility_again(callback: CallbackQuery, state: FSMContext):
    """
    Этот хэндлер срабатывает, когда пользователь нажимает 'Настроить общую мобильность'
    на экране ввода имени артиста.
    """
    await state.set_state(SubscriptionFlow.selecting_general_regions)
    await state.update_data(source_flow="setup_again") # Помечаем, откуда пришли
    
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)
    
    current_regions = await db.get_general_mobility(callback.from_user.id) or []
    await state.update_data(selected_regions=current_regions)
    
    await callback.message.edit_text(
        lexicon.get('general_mobility_selection_prompt'),
        reply_markup=kb.get_region_selection_keyboard(
            selected_regions=current_regions, 
            finish_callback="finish_general_selection", 
            back_callback="back_to_artist_input", 
            search_callback="search_for_sub_country",
            lexicon=lexicon
        )
    )
    await callback.answer()

@router.callback_query(SubscriptionFlow.selecting_general_regions, F.data == "back_to_artist_input")
async def cq_back_to_artist_input(callback: CallbackQuery, state: FSMContext):
    """Возвращает из настройки общей мобильности к экрану ввода имени артиста."""
    await state.set_state(SubscriptionFlow.waiting_for_artist_name)
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)
    
    # Проверяем, нужно ли показывать кнопку настройки мобильности снова
    general_mobility_regions = await db.get_general_mobility(callback.from_user.id)
    show_setup_button = not bool(general_mobility_regions)

    await callback.message.edit_text(
        lexicon.get('enter_artist_name_prompt'),
        reply_markup=kb.get_artist_input_keyboard(lexicon, show_setup_mobility_button=show_setup_button)
    )

@router.callback_query(SubscriptionFlow.adding_more_artists, F.data == "finish_adding_subscriptions")
async def finish_adding_subscriptions(callback: CallbackQuery, state: FSMContext):
    """Сохраняет всех из очереди в БД и запускает поиск событий/рекомендаций."""
    data = await state.get_data()
    pending_items = data.get('pending_favorites', [])
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)
    if not pending_items:
        await callback.answer(lexicon.get('nothing_to_add_alert'), show_alert=True)
        return
    
    added_artist_names, added_artist_ids = [], []
    async with db.async_session() as session:
        for item_data in pending_items:
            artist_name = item_data['item_name']
            artist_obj_stmt = select(db.Artist).where(db.Artist.name == artist_name)
            artist = (await session.execute(artist_obj_stmt)).scalar_one_or_none()
            if artist:
                await db.add_artist_to_favorites(session, callback.from_user.id, artist.artist_id, item_data['regions'])
                added_artist_ids.append(artist.artist_id)
                added_artist_names.append(artist.name)
        await session.commit()

    if not added_artist_ids:
        await callback.message.edit_text(lexicon.get('failed_to_add_artists'))
        await callback.answer()
        await state.clear()
        return

    await state.set_state(CombinedFlow.active)
    await state.set_data({})
    
    initial_feedback_text = lexicon.get('favorites_added_final').format(count=len(added_artist_names))
    await callback.message.edit_text(initial_feedback_text)
    
    await asyncio.gather(
        show_events_for_new_favorites(callback, state, added_artist_ids, added_artist_names),
        trigger_recommendation_flow(callback.from_user.id, callback.bot, state, added_artist_names)
    )
    await callback.answer()


@router.callback_query(SubscriptionFlow.waiting_for_action, F.data == "import_artists")
async def handle_import_artists(callback: CallbackQuery, state: FSMContext):
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)
    await callback.answer(lexicon.get('import_in_development_alert'), show_alert=True)

@router.message(SubscriptionFlow.waiting_for_artist_name, F.text)
async def process_artist_search(message: Message, state: FSMContext):
    """Поиск артиста по имени."""
    found_artists, is_exact_match = await db.find_artists_fuzzy(message.text)
    
    user_lang = await db.get_user_lang(message.from_user.id)
    lexicon = Lexicon(user_lang)

    if not found_artists:
        await message.answer(
            lexicon.get('favorites_not_found_try_again'),
            reply_markup=kb.get_cancel_artist_input_keyboard(lexicon)
        )
    else:
        # --- ИЗМЕНЕНИЕ: Выбираем текст в зависимости от флага ---
        if is_exact_match:
            text_to_send = lexicon.get('artist_search_exact_match')
        else:
            text_to_send = lexicon.get('artist_search_suggestion')
            
        await message.answer(
            text_to_send,
            reply_markup=kb.found_artists_keyboard(found_artists, lexicon)
        )

@router.message(SubscriptionFlow.adding_more_artists, F.text)
async def process_artist_search_from_add_more_screen(message: Message, state: FSMContext):
    """
    Если пользователь вводит текст на экране 'Добавить еще / Готово',
    это должно расцениваться как поиск нового артиста.
    """
    # Просто передаем управление основному хендлеру поиска артиста
    await process_artist_search(message, state)

@router.callback_query(F.data.startswith("subscribe_to_artist:"))
async def cq_subscribe_to_artist(callback: CallbackQuery, state: FSMContext):
    artist_id = int(callback.data.split(":", 1)[1])
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)
    
    async with db.async_session() as session:
        artist = await session.get(db.Artist, artist_id)
    
    if not artist:
        await callback.answer(lexicon.get('artist_not_found_error'), show_alert=True)
        return

    await state.update_data(current_artist_id=artist.artist_id, current_artist=artist.name)
    
    general_mobility = await db.get_general_mobility(callback.from_user.id)
    
    if general_mobility:
        # ... (этот блок без изменений)
        data = await state.get_data()
        pending_subs = data.get('pending_favorites', [])
        if not any(sub['item_name'] == artist.name for sub in pending_subs):
            pending_subs.append({
                "item_name": artist.name, 
                "category": "music", 
                "regions": general_mobility
            })
            await state.update_data(pending_favorites=pending_subs)
            await callback.answer(lexicon.get('artist_added_with_general_settings_alert').format(artist_name=artist.name), show_alert=True)
        else:
            await callback.answer(lexicon.get('artist_already_in_queue_alert').format(artist_name=artist.name), show_alert=True)
        await show_add_more_or_finish(callback.message, state, lexicon)
    else:
        # --- ИЗМЕНИТЬ ЭТОТ БЛОК ---
        await state.set_state(SubscriptionFlow.selecting_custom_regions)
        selected_regions = []
        await state.update_data(selected_regions=selected_regions)
        
        await callback.message.edit_text(
            lexicon.get('artist_set_tracking_countries_prompt').format(artist_name=hbold(artist.name)),
            reply_markup=kb.get_region_selection_keyboard(
                selected_regions=selected_regions,
                finish_callback="finish_custom_selection",
                back_callback="cancel_artist_search",
                search_callback="search_for_sub_country", # <-- Новый callback
                lexicon=lexicon
            ),
            parse_mode="HTML"
        )
    await callback.answer()

# @router.callback_query(SubscriptionFlow.choosing_mobility_type, F.data.in_(['use_general_mobility', 'setup_custom_mobility']))
# async def handle_mobility_type_choice(callback: CallbackQuery, state: FSMContext):
#     data = await state.get_data()
#     artist_name = data.get('current_artist')
#     pending_subs = data.get('pending_favorites', [])
#     user_lang = callback.message.from_user.language_code
#     lexicon = Lexicon(user_lang)
#     if callback.data == 'use_general_mobility':
#         regions = await db.get_general_mobility(callback.from_user.id)
#         pending_subs.append({"item_name": artist_name, "category": "music", "regions": regions})
#         await state.update_data(pending_favorites=pending_subs)
#         await callback.answer(lexicon.get('artist_added_with_general_settings_alert').format(artist_name=artist_name), show_alert=True)
#         await show_add_more_or_finish(callback.message, state, lexicon)
#     else:
#         await state.set_state(SubscriptionFlow.selecting_custom_regions)
#         await state.update_data(selected_regions=[])
#         all_countries = await db.get_countries()
#         await callback.message.edit_text(
#             lexicon.get('artist_set_tracking_countries_prompt').format(artist_name=hbold(artist_name)),
#             reply_markup=kb.get_region_selection_keyboard(all_countries, [], finish_callback="finish_custom_selection", back_callback=f"subscribe_to_artist:{artist_name}",
#             lexicon=lexicon),
#             parse_mode="HTML"
#         )

@router.callback_query(SubscriptionFlow.waiting_country_input, F.data == "back_to_custom_regions_selection")
async def cq_back_to_custom_regions_selection(callback: CallbackQuery, state: FSMContext):
    """Возврат из поиска к выбору кастомных регионов."""
    await state.set_state(SubscriptionFlow.selecting_custom_regions)
    data = await state.get_data()
    selected = data.get("selected_regions", [])
    artist_name = data.get('current_artist', '...')
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)
    await callback.message.edit_text(
        lexicon.get('artist_set_tracking_countries_prompt').format(artist_name=hbold(artist_name)),
        reply_markup=kb.get_region_selection_keyboard(
            selected_regions=selected,
            finish_callback="finish_custom_selection",
            back_callback="cancel_artist_search",
            search_callback="search_for_sub_country",
            lexicon=lexicon
        ),
        parse_mode="HTML"
    )

@router.callback_query(
    or_f(SubscriptionFlow.selecting_general_regions, SubscriptionFlow.selecting_custom_regions), 
    F.data == "search_for_sub_country"
)
async def cq_search_for_sub_country(callback: CallbackQuery, state: FSMContext):
    """Запускает поиск страны в флоу подписок."""
    current_state = await state.get_state()
    # Определяем, куда возвращаться
    if current_state == SubscriptionFlow.selecting_general_regions:
        back_cb = "back_to_general_selection"
    else: # selecting_custom_regions
        back_cb = "back_to_custom_regions_selection"

    await start_country_search(
        callback,
        state,
        new_state=SubscriptionFlow.waiting_country_input,
        back_callback=back_cb
    )

@router.message(SubscriptionFlow.waiting_country_input, F.text)
async def process_sub_country_search(message: Message, state: FSMContext):
    """Обрабатывает ввод страны в флоу подписок."""
    data = await state.get_data()
    # Определяем, в какое состояние вернуться
    if data.get("source_flow") or await state.get_state() == SubscriptionFlow.selecting_general_regions:
         return_state = SubscriptionFlow.selecting_general_regions
         back_cb = "back_to_general_selection"
    else:
         return_state = SubscriptionFlow.selecting_custom_regions
         back_cb = "back_to_custom_regions_selection"

    await process_country_search(
        message=message,
        state=state,
        return_state=return_state,
        back_callback=back_cb
    )

@router.callback_query(
    or_f(SubscriptionFlow.selecting_general_regions, SubscriptionFlow.selecting_custom_regions, SubscriptionFlow.waiting_country_input),
    F.data.startswith("toggle_region:")
)
async def cq_toggle_region(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор/снятие региона (универсальный хендлер)."""
    region_name = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_regions", [])
    
    if region_name in selected:
        selected.remove(region_name)
    else:
        selected.append(region_name)
    await state.update_data(selected_regions=selected)

    # Определяем, какой экран перерисовывать
    current_state = await state.get_state()
    # Если мы в поиске или в настройке общей мобильности
    if current_state == SubscriptionFlow.waiting_country_input or data.get("source_flow"):
        await cq_back_to_general_selection(callback, state)
    else: # Значит, мы в кастомной настройке
        await cq_back_to_custom_regions_selection(callback, state)
        
    await callback.answer()




@router.callback_query(SubscriptionFlow.selecting_custom_regions, F.data == "finish_custom_selection")
async def cq_finish_custom_selection(callback: CallbackQuery, state: FSMContext):
    """Завершение настройки кастомных регионов для подписки."""
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    artist_name = data.get('current_artist')
    pending_subs = data.get('pending_favorites', [])
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)

    if not regions:
        await callback.answer(lexicon.get('no_regions_selected_alert'), show_alert=True)
        return
    
    pending_subs.append({"item_name": artist_name, "category": "music", "regions": regions})
    await state.update_data(pending_favorites=pending_subs)
    await callback.answer(lexicon.get('artist_added_with_custom_settings_alert').format(artist_name=artist_name), show_alert=True)

    await show_add_more_or_finish(callback.message, state, lexicon)

async def show_add_more_or_finish(message: Message, state: FSMContext, lexicon: Lexicon):
    """
    Показывает очередь и предлагает написать имя следующего артиста или нажать "Готово".
    """
    await state.set_state(SubscriptionFlow.adding_more_artists) # <-- Устанавливаем новое, уникальное состояние
    data = await state.get_data()
    pending_subs = data.get('pending_favorites', [])
    
    text = ""
    if pending_subs:
        text += lexicon.get('queue_for_adding_header')
        for sub in pending_subs:
            text += f"▫️ {hbold(sub['item_name'])}\n"
    text += "\n" + lexicon.get('add_more_prompt')
    
    # Клавиатура остается прежней, она генерирует правильный callback_data
    await message.edit_text(
        text, 
        reply_markup=kb.get_add_more_or_finish_keyboard(lexicon), 
        parse_mode=ParseMode.HTML
    )

@router.callback_query(SubscriptionFlow.selecting_general_regions, F.data == "finish_general_selection")
async def cq_finish_general_selection(callback: CallbackQuery, state: FSMContext):
    """Завершение настройки общей мобильности."""
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)

    await db.set_general_mobility(callback.from_user.id, regions)
    await callback.answer(lexicon.get('mobility_saved_alert'), show_alert=True)
    
    # Возвращаемся к вводу имени артиста
    await state.set_state(SubscriptionFlow.waiting_for_artist_name)
    await state.update_data(source_flow=None) # Чистим флаг
    await callback.message.edit_text(
        lexicon.get('enter_artist_name_prompt'),
        reply_markup=kb.get_artist_input_keyboard(lexicon, show_setup_mobility_button=not bool(regions))
    )


# @router.callback_query(F.data.startswith("unsubscribe:"))
# async def cq_unsubscribe_item(callback: CallbackQuery, state: FSMContext):
#     """Удаление подписки из меню."""
#     lexicon = Lexicon(callback.from_user.language_code)
#     item_name = callback.data.split(":", 1)[1]
#     await db.remove_subscription(callback.from_user.id, item_name)
#     # await callback.answer(lexicon.get('subs_removed_alert').format(item_name=item_name))
#     await show_favorites_list(callback)


@router.callback_query(CombinedFlow.active, F.data.startswith("rec_toggle:"))
async def cq_toggle_recommended_artist(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие на кнопку с рекомендованным артистом,
    добавляя или удаляя его из списка выбранных.
    """
    try:
        artist_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer("Error: Invalid artist ID.", show_alert=True)
        return

    data = await state.get_data()
    
    # Получаем данные напрямую, без какой-либо очереди
    all_artists_data = data.get('recommended_artists', [])
    if not all_artists_data:
        await callback.answer("Session data is missing. Please try again.", show_alert=True)
        await state.clear()
        return

    # Используем set для быстрой проверки и добавления/удаления
    selected_ids = set(data.get('current_selection_ids', []))

    if artist_id in selected_ids:
        selected_ids.remove(artist_id)
    else:
        selected_ids.add(artist_id)
    
    # Сохраняем обратно в state как список, чтобы избежать ошибок JSON
    await state.update_data(current_selection_ids=list(selected_ids))

    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)
    
    try:
        # Перерисовываем клавиатуру
        await callback.message.edit_reply_markup(
            reply_markup=kb.get_recommended_artists_keyboard(
                all_artists_data, 
                lexicon,
                selected_ids
            )
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e): pass
        else: raise
    
    await callback.answer()


@router.callback_query(CombinedFlow.active, F.data == "rec_finish")
async def cq_finish_recommendation_selection(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие на кнопку "Готово", сохраняет выбранных артистов
    и запускает поиск их событий.
    """
    data = await state.get_data()
    selected_ids = data.get('current_selection_ids', [])
    message_to_edit_id = data.get('recommendation_message_id') # Используем правильный ID
    all_artists_data = data.get('recommended_artists', [])
    user_lang = await db.get_user_lang(callback.from_user.id)
    lexicon = Lexicon(user_lang)

    if not message_to_edit_id:
        await callback.answer("Session error, please try again.", show_alert=True)
        return

    # Если ничего не выбрано, просто удаляем блок с рекомендациями и выходим
    if not selected_ids:
        await callback.message.delete()
        # Проверяем, остался ли первый блок событий. Если нет, очищаем state.
        current_data = await state.get_data()
        if not current_data.get('event_messages_ids'):
            await state.clear()
        await callback.answer("OK")
        return

    # 1. Сохраняем выбранных артистов в БД
    general_mobility = await db.get_general_mobility(callback.from_user.id) or []
    async with db.async_session() as session:
        for artist_id in selected_ids:
            await db.add_artist_to_favorites(session, callback.from_user.id, artist_id, general_mobility)
        await session.commit()
    
    # 2. Ищем события для новых артистов
    selected_artist_names = [a['name'] for a in all_artists_data if a['artist_id'] in selected_ids]
    found_events = await db.get_future_events_for_artists(selected_ids)
    response_text, event_ids_to_subscribe = await format_events_by_artist(found_events, selected_artist_names, lexicon)

    # 3. Готовим итоговое сообщение и клавиатуру
    final_text = response_text if response_text else lexicon.get('no_future_events_for_favorites')
    final_markup = kb.get_afisha_actions_keyboard(lexicon) if response_text else None

    # 4. Редактируем сообщение с рекомендациями, заменяя его на список событий
    try:
        await callback.bot.edit_message_text(
            chat_id=callback.from_user.id,
            message_id=message_to_edit_id,
            text=final_text,
            reply_markup=final_markup,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    except TelegramBadRequest as e:
        logging.error(f"Не удалось отредактировать сообщение с рекомендациями: {e}")
        # Если не удалось, просто удаляем его, чтобы не мешало
        await callback.bot.delete_message(callback.from_user.id, message_to_edit_id)


    # 5. Обновляем state: очищаем данные рекомендаций и добавляем данные о новых событиях
    await state.update_data(
        recommended_artists=None,
        current_selection_ids=None,
        recommendation_message_id=None,
        last_shown_event_ids=event_ids_to_subscribe # Перезаписываем ID событий на новые
    )
    
    # Отправляем alert об успехе
    await callback.answer(
        lexicon.get('favorites_added_final').format(count=len(selected_ids)),
        show_alert=True
    )

@router.message(SubscriptionFlow.waiting_for_action, F.text)
async def process_artist_search_from_action(message: Message, state: FSMContext):
    """
    Ловит текстовый ввод в состоянии 'waiting_for_action'
    и передает управление основному поисковому хэндлеру.
    """
    # Просто вызываем уже существующий хэндлер поиска
    await process_artist_search(message, state)