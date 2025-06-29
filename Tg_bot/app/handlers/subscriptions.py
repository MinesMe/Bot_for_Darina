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

from aiogram.enums import ParseMode
from app.utils.utils import format_events_by_artist # Наш новый форматер
from app.handlers.afisha import AddToSubsFSM, send_long_message
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.storage.base import BaseStorage, StorageKey
# ... (остальные ваши импорты)
from app.services.recommendation import get_recommended_artists



router = Router()


class SubscriptionFlow(StatesGroup):
    # Онбординг общей мобильности
    general_mobility_onboarding = State()
    selecting_general_regions = State()
    # Основной флоу добавления
    waiting_for_action = State()
    waiting_for_artist_name = State()
    choosing_mobility_type = State()
    selecting_custom_regions = State()

class RecommendationFlow(StatesGroup):
    selecting_artists = State()


async def trigger_recommendation_flow(
    user_id: int,
    bot: Bot,
    storage: BaseStorage,
    added_artist_names: list[str]
):
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
        
        state_key = StorageKey(bot_id=bot.id, chat_id=user_id, user_id=user_id)
        await storage.set_state(key=state_key, state=RecommendationFlow.selecting_artists)
        await storage.set_data(
            key=state_key, 
            data={
                "recommended_artists": recommended_artists_dicts, # Сохраняем list[dict]
                "current_selection_ids": [],
                "message_id_to_edit": sent_message.message_id
            }
        )
        logging.info(f"--> Отправлена рекомендация и установлено состояние для {user_id}")

    except Exception as e:
        logging.error(f"Не удалось запустить флоу рекомендаций для пользователя {user_id}: {e}", exc_info=True)


async def show_events_for_new_favorites(
    callback: CallbackQuery,
    state: FSMContext,
    artist_ids: list[int],
    artist_names: list[str]
):
    """
    Ищет события для артистов и отправляет их пользователю.
    Выполняется как фоновая задача.
    """
    lexicon = Lexicon(callback.from_user.language_code)
    found_events = await db.get_future_events_for_artists(artist_ids)
    
    if not found_events:
        no_events_text = "\n\n" + lexicon.get('no_future_events_for_favorites')
        await callback.message.answer(no_events_text)
        return

    response_text, event_ids_to_subscribe = await format_events_by_artist(
        found_events, artist_names, lexicon
    )
    
    if not response_text:
        no_events_text = "\n\n" + lexicon.get('no_future_events_for_favorites')
        await callback.message.answer(no_events_text)
        return

    # Устанавливаем состояние для добавления в подписки
    await state.set_state(AddToSubsFSM.waiting_for_event_numbers)
    await state.update_data(last_shown_event_ids=event_ids_to_subscribe)
    
    await send_long_message(
        message=callback.message,
        text=response_text,
        lexicon=lexicon,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=kb.get_afisha_actions_keyboard(lexicon)
    )

@router.message(F.text.in_(['➕ Найти/добавить артиста', '➕ Find/Add Artist', '➕ Знайсці/дадаць выканаўцу'])) 
async def menu_add_subscriptions(message: Message, state: FSMContext):
    """
    Точка входа в флоу ДОБАВЛЕНИЯ подписки.
    """
    await state.clear()
    user_id = message.from_user.id
    onboarding_done = await db.check_general_geo_onboarding_status(user_id)
    user_lang = message.from_user.language_code
    lexicon = Lexicon(user_lang)

    if not onboarding_done:
        # Случай 1: Пользователь здесь в самый первый раз.
        await state.set_state(SubscriptionFlow.general_mobility_onboarding)
        await message.answer(
            lexicon.get('onboarding_mobility_prompt'),
            reply_markup=kb.get_general_onboarding_keyboard(lexicon)
        )
    else:
        # Пользователь уже проходил онбординг.
        general_mobility_regions = await db.get_general_mobility(user_id)
        await state.set_state(SubscriptionFlow.waiting_for_action)
        await state.update_data(pending_favorites=[])

        if not general_mobility_regions:
            # Случай 2: Онбординг пройден, но мобильность не настроена (пропущена).
            # Показываем дополнительную кнопку.
            await message.answer(
                lexicon.get('action_prompt_with_mobility_setup'),
                reply_markup=kb.get_add_sub_action_keyboard(lexicon, show_setup_mobility_button=True)
            )
        else:
            # Случай 3: Все настроено.
            # Стандартный флоу без лишних кнопок.
            await message.answer(
                lexicon.get('action_prompt_default'),
                reply_markup=kb.get_add_sub_action_keyboard(lexicon, show_setup_mobility_button=False)
            )

# @router.callback_query(F.data == "show_my_subscriptions_from_profile")
# async def cq_show_my_subscriptions_from_profile(callback: CallbackQuery, state: FSMContext):
#     """Точка входа в раздел 'Мои подписки' из меню профиля."""
#     await state.clear()
#     await callback.message.delete()
#     await show_subscriptions_menu(callback.message)
#     await callback.answer()

@router.callback_query(F.data == "add_new_subscription")
async def start_subscription_add_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу добавления подписки."""
    user_id = callback.from_user.id
    onboarding_done = await db.check_general_geo_onboarding_status(user_id)
    user_lang = callback.message.from_user.language_code
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

@router.callback_query(F.data == "cancel_artist_search")
async def cq_cancel_artist_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.waiting_for_action)
    
    lexicon = Lexicon(callback.from_user.language_code)
    
    # Показываем то же сообщение и клавиатуру, что и в начале флоу
    await callback.message.edit_text(
        lexicon.get('action_prompt_default'),
        reply_markup=kb.get_add_sub_action_keyboard(lexicon, show_setup_mobility_button=False)
    )
    await callback.answer("Отменено.")

@router.callback_query(SubscriptionFlow.general_mobility_onboarding, F.data.in_(['setup_general_mobility', 'skip_general_mobility']))
async def handle_general_onboarding_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора в онбординге общей мобильности."""
    await db.set_general_geo_onboarding_completed(callback.from_user.id)
    user_lang = callback.message.from_user.language_code
    lexicon = Lexicon(user_lang)

    if callback.data == 'setup_general_mobility':
        await state.set_state(SubscriptionFlow.selecting_general_regions)
        await state.update_data(selected_regions=[])
        all_countries = await db.get_countries()
        
        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        # Кнопка "Назад" будет просто отменять весь процесс добавления
        await callback.message.edit_text(
            lexicon.get('general_mobility_selection_prompt'),
            reply_markup=kb.get_region_selection_keyboard(
                all_countries, [], 
                finish_callback="finish_general_selection",
                back_callback="cancel_add_to_fav" ,
                lexicon=lexicon
            )
        )
    else: # skip_general_mobility
        await state.set_state(SubscriptionFlow.waiting_for_action)
        await state.update_data(pending_favorites=[])
        await callback.message.edit_text(
            lexicon.get('general_mobility_skipped_prompt'),
            reply_markup=kb.get_add_sub_action_keyboard(lexicon)
        )

@router.callback_query(F.data == "cancel_add_to_fav")
async def cq_cancel_add_process(callback: CallbackQuery, state: FSMContext):
    print('here')
    """Отменяет процесс добавления и возвращает в главное меню."""
    await state.clear()
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.delete()
    # Здесь можно либо показать главное меню, либо меню "Избранное"
    # Давайте вернем в главное меню, это универсальнее
    await callback.message.answer(
        lexicon.get('main_menu_greeting').format(first_name=hbold(callback.from_user.first_name)),
        reply_markup=kb.get_main_menu_keyboard(lexicon),
        parse_mode="HTML"
    )
    await callback.answer(lexicon.get('cancel_alert'))

@router.callback_query(SubscriptionFlow.waiting_for_action, F.data == "setup_general_mobility")
async def handle_setup_general_mobility_again(callback: CallbackQuery, state: FSMContext):
    """
    Этот хэндлер срабатывает, когда пользователь нажимает 'Настроить общую мобильность'
    уже после прохождения первого онбординга.
    """
    user_lang = callback.message.from_user.language_code
    lexicon = Lexicon(user_lang)
    await state.set_state(SubscriptionFlow.selecting_general_regions)
    await state.update_data(selected_regions=[])
    all_countries = await db.get_countries()
    await callback.message.edit_text(
        lexicon.get('general_mobility_selection_prompt'),
        reply_markup=kb.get_region_selection_keyboard(
            all_countries, [], finish_callback="finish_general_selection", back_callback="cancel_add_to_fav",
            lexicon=lexicon
        )
    )
    await callback.answer()

@router.callback_query(SubscriptionFlow.selecting_general_regions, F.data.startswith("toggle_region:"))
async def cq_toggle_region_for_general(callback: CallbackQuery, state: FSMContext):
    region_name = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_regions", [])
    user_lang = callback.message.from_user.language_code
    lexicon = Lexicon(user_lang)
    if region_name in selected:
        selected.remove(region_name)
    else:
        selected.append(region_name)
    await state.update_data(selected_regions=selected)
    all_countries = await db.get_countries()
    # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_region_selection_keyboard(all_countries, selected, finish_callback="finish_general_selection",  back_callback="cancel_add_to_fav",
            lexicon=lexicon )
    )

@router.callback_query(SubscriptionFlow.waiting_for_action, F.data == "finish_adding_subscriptions")
async def finish_adding_subscriptions(callback: CallbackQuery, state: FSMContext):
    """
    Завершает сессию, сохраняет все в ИЗБРАННОЕ и показывает найденные события.
    """
    data = await state.get_data()
    pending_items = data.get('pending_favorites', [])
    lexicon = Lexicon(callback.from_user.language_code)

    if not pending_items:
        await callback.answer(lexicon.get('nothing_to_add_alert'), show_alert=True)
        return

    added_artist_names = []
    added_artist_ids = []
    
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
    
    await state.clear()
    
    if not added_artist_ids:
        await callback.message.edit_text(lexicon.get('failed_to_add_artists'))
        await callback.answer()
        return

    # Сначала показываем пользователю результат по ивентам
    initial_feedback_text = lexicon.get('favorites_added_final').format(count=len(added_artist_names))
    await callback.message.edit_text(initial_feedback_text)
    
    # --- ЗАПУСК РЕКОМЕНДАЦИЙ И ПОИСКА СОБЫТИЙ В ФОНЕ ---
    # Мы не ждем завершения этих задач, чтобы интерфейс бота не "зависал"
    
    # 1. Запускаем поиск событий для добавленных артистов
    asyncio.create_task(
        show_events_for_new_favorites(callback, state, added_artist_ids, added_artist_names)
    )
    
    # 2. Запускаем флоу рекомендаций
    # Передаем bot и storage из контекста aiogram (data['bot'], data['state'].storage)
    asyncio.create_task(
        trigger_recommendation_flow(
            user_id=callback.from_user.id,
            bot=callback.bot,
            storage=state.storage,
            added_artist_names=added_artist_names
        )
    )
    
    await callback.answer()

@router.callback_query(SubscriptionFlow.waiting_for_action, F.data == "write_artist")
async def handle_write_artist(callback: CallbackQuery, state: FSMContext):
    lexicon = Lexicon(callback.from_user.language_code)
    await state.set_state(SubscriptionFlow.waiting_for_artist_name)
    await callback.message.edit_text(lexicon.get('enter_artist_name_prompt'))
    await callback.answer()

@router.callback_query(SubscriptionFlow.waiting_for_action, F.data == "import_artists")
async def handle_import_artists(callback: CallbackQuery, state: FSMContext):
    lexicon = Lexicon(callback.from_user.language_code)
    # --- ИСПРАВЛЕНИЕ --- Замена текста
    await callback.answer(lexicon.get('import_in_development_alert'), show_alert=True)

@router.message(SubscriptionFlow.waiting_for_artist_name, F.text)
async def process_artist_search(message: Message, state: FSMContext):
    """Поиск артиста по имени."""
    found_artists = await db.find_artists_fuzzy(message.text)
    lexicon = Lexicon(message.from_user.language_code)
    if not found_artists:
        await message.answer(lexicon.get('favorites_not_found_try_again'))
    else:
        await message.answer(lexicon.get('favorites_found_prompt_select_artist'),
                             reply_markup=kb.found_artists_keyboard(found_artists, lexicon))

@router.callback_query(F.data.startswith("subscribe_to_artist:"))
async def cq_subscribe_to_artist(callback: CallbackQuery, state: FSMContext):
    artist_id = int(callback.data.split(":", 1)[1])
    user_lang = callback.message.from_user.language_code
    lexicon = Lexicon(user_lang)
    # Нам нужно получить имя артиста для сообщений пользователю
    async with db.async_session() as session:
        artist = await session.get(db.Artist, artist_id)
    
    if not artist:
        await callback.answer(lexicon.get('artist_not_found_error'), show_alert=True)
        return

    # Сохраняем в state и ID, и имя
    await state.update_data(current_artist_id=artist.artist_id, current_artist=artist.name)
    
    general_mobility = await db.get_general_mobility(callback.from_user.id)
    if general_mobility:
        await state.set_state(SubscriptionFlow.choosing_mobility_type)
        await callback.message.edit_text(
            lexicon.get('artist_mobility_choice_prompt').format(artist_name=hbold(artist.name)),
            reply_markup=kb.get_mobility_type_choice_keyboard(lexicon),
            parse_mode="HTML"
        )
    else:
        await state.set_state(SubscriptionFlow.selecting_custom_regions)
        await state.update_data(selected_regions=[])
        all_countries = await db.get_countries()
        await callback.message.edit_text(
            lexicon.get('artist_set_tracking_countries_prompt').format(artist_name=hbold(artist.name)),
            reply_markup=kb.get_region_selection_keyboard(
                all_countries, [], 
                finish_callback="finish_custom_selection",
                back_callback="cancel_artist_search",
                lexicon=lexicon
            ),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(SubscriptionFlow.choosing_mobility_type, F.data.in_(['use_general_mobility', 'setup_custom_mobility']))
async def handle_mobility_type_choice(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    artist_name = data.get('current_artist')
    pending_subs = data.get('pending_favorites', [])
    user_lang = callback.message.from_user.language_code
    lexicon = Lexicon(user_lang)
    if callback.data == 'use_general_mobility':
        regions = await db.get_general_mobility(callback.from_user.id)
        pending_subs.append({"item_name": artist_name, "category": "music", "regions": regions})
        await state.update_data(pending_favorites=pending_subs)
        await callback.answer(lexicon.get('artist_added_with_general_settings_alert').format(artist_name=artist_name), show_alert=True)
        await show_add_more_or_finish(callback.message, state, lexicon)
    else:
        await state.set_state(SubscriptionFlow.selecting_custom_regions)
        await state.update_data(selected_regions=[])
        all_countries = await db.get_countries()
        await callback.message.edit_text(
            lexicon.get('artist_set_tracking_countries_prompt').format(artist_name=hbold(artist_name)),
            reply_markup=kb.get_region_selection_keyboard(all_countries, [], finish_callback="finish_custom_selection", back_callback=f"subscribe_to_artist:{artist_name}",
            lexicon=lexicon),
            parse_mode="HTML"
        )

@router.callback_query(SubscriptionFlow.selecting_custom_regions, F.data.startswith("toggle_region:"))
async def cq_toggle_region_for_custom(callback: CallbackQuery, state: FSMContext):
    region_name = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_regions", [])
    user_lang = callback.message.from_user.language_code
    lexicon = Lexicon(user_lang)
    if region_name in selected:
        selected.remove(region_name)
    else:
        selected.append(region_name)
    await state.update_data(selected_regions=selected)
    all_countries = await db.get_countries()
    # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_region_selection_keyboard(all_countries, selected, finish_callback="finish_custom_selection", back_callback=f"subscribe_to_artist:{data.get('current_artist')}",
            lexicon=lexicon)
    )

@router.callback_query(SubscriptionFlow.selecting_custom_regions, F.data == "finish_custom_selection")
async def cq_finish_custom_selection(callback: CallbackQuery, state: FSMContext):
    """Завершение настройки кастомных регионов для подписки."""
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    artist_name = data.get('current_artist')
    pending_subs = data.get('pending_favorites', [])
    lexicon = Lexicon(callback.from_user.language_code)

    if not regions:
        await callback.answer(lexicon.get('no_regions_selected_alert'), show_alert=True)
        return
    
    pending_subs.append({"item_name": artist_name, "category": "music", "regions": regions})
    await state.update_data(pending_favorites=pending_subs)
    await callback.answer(lexicon.get('artist_added_with_custom_settings_alert').format(artist_name=artist_name), show_alert=True)

    await show_add_more_or_finish(callback.message, state, lexicon)

async def show_add_more_or_finish(message: Message, state: FSMContext, lexicon: Lexicon):
    """Показывает клавиатуру 'Добавить еще' / 'Готово'."""
    data = await state.get_data()
    pending_subs = data.get('pending_favorites', [])
    text = lexicon.get('sub_added_to_queue')
    if pending_subs:
        text += lexicon.get('queue_for_adding_header')
        for sub in pending_subs:
            text += f"▫️ {hbold(sub['item_name'])}\n"
    
    await state.set_state(SubscriptionFlow.waiting_for_action)
    await message.edit_text(text, reply_markup=kb.get_add_more_or_finish_keyboard(lexicon), parse_mode="HTML")

@router.callback_query(SubscriptionFlow.selecting_general_regions, F.data == "finish_general_selection")
async def cq_finish_general_selection(callback: CallbackQuery, state: FSMContext):
    """Завершение настройки общей мобильности."""
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    lexicon = Lexicon(callback.from_user.language_code)

    # if not regions: # Можно раскомментировать, если нужно
    #     await callback.answer("Нужно выбрать хотя бы один регион!", show_alert=True)
    #     return

    await db.set_general_mobility(callback.from_user.id, regions)
    await callback.answer(lexicon.get('mobility_saved_alert'), show_alert=True)
    
    # Возвращаемся к выбору действия
    await state.set_state(SubscriptionFlow.waiting_for_action)
    await callback.message.edit_text(
        lexicon.get('general_mobility_saved_prompt_action'),
        reply_markup=kb.get_add_sub_action_keyboard(lexicon)
    )


@router.callback_query(F.data.startswith("unsubscribe:"))
async def cq_unsubscribe_item(callback: CallbackQuery, state: FSMContext):
    """Удаление подписки из меню."""
    lexicon = Lexicon(callback.from_user.language_code)
    item_name = callback.data.split(":", 1)[1]
    await db.remove_subscription(callback.from_user.id, item_name)
    await callback.answer(lexicon.get('subs_removed_alert').format(item_name=item_name))
    await show_favorites_list(callback)


@router.callback_query(RecommendationFlow.selecting_artists, F.data.startswith("rec_toggle:"))
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

    lexicon = Lexicon(callback.from_user.language_code)
    
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


@router.callback_query(RecommendationFlow.selecting_artists, F.data == "rec_finish")
async def cq_finish_recommendation_selection(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает нажатие на кнопку "Готово", сохраняет выбранных артистов
    и запускает поиск их событий.
    """
    data = await state.get_data()
    selected_ids = data.get('current_selection_ids', [])
    message_id_to_edit = data.get('message_id_to_edit')
    all_artists_data = data.get('recommended_artists', [])
    
    lexicon = Lexicon(callback.from_user.language_code)
    
    # Сразу очищаем state, так как сессия выбора рекомендаций завершена
    await state.clear()
    await callback.answer()

    # Сначала редактируем сообщение с рекомендациями
    if not selected_ids:
        # Если ничего не выбрано, просто пишем "Хорошо!"
        final_text = lexicon.get('ok_button')
    else:
        # Если выбраны, пишем "Добавлено N артистов"
        final_text = lexicon.get('favorites_added_final').format(count=len(selected_ids))

    try:
        if message_id_to_edit:
            await callback.bot.edit_message_text(
                chat_id=callback.from_user.id,
                message_id=message_id_to_edit,
                text=final_text,
                reply_markup=None # Убираем клавиатуру
            )
    except TelegramBadRequest: pass

    # Если ничего не было выбрано, просто выходим
    if not selected_ids:
        return

    # --- Если артисты были выбраны, продолжаем ---

    # 1. Сохраняем их в "Избранное"
    general_mobility = await db.get_general_mobility(callback.from_user.id) or []
    async with db.async_session() as session:
        for artist_id in selected_ids:
            await db.add_artist_to_favorites(session, callback.from_user.id, artist_id, general_mobility)
        await session.commit()
    
    # 2. Запускаем фоновую задачу для поиска их событий
    selected_artist_names = [
        artist['name'] for artist in all_artists_data 
        if artist['artist_id'] in selected_ids
    ]

    asyncio.create_task(
        show_events_for_new_favorites(callback, state, selected_ids, selected_artist_names)
    )