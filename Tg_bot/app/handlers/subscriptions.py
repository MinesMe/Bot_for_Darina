# app/handlers/subscriptions.py

from aiogram import Router, F
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

    added_artist_ids = []
    added_artist_names = []
    
    # 1. Сохраняем артистов в базу данных
    async with db.async_session() as session:
        for item_data in pending_items:
            artist_name = item_data['item_name']
            regions_to_save = item_data['regions']
            
            # Находим ID артиста по его имени
            artist_obj_stmt = select(db.Artist).where(db.Artist.name == artist_name)
            artist = (await session.execute(artist_obj_stmt)).scalar_one_or_none()
            
            if artist:
                await db.add_artist_to_favorites(session, callback.from_user.id, artist.artist_id, regions_to_save)
                added_artist_ids.append(artist.artist_id)
                added_artist_names.append(artist.name)
        
        await session.commit()

    if not added_artist_ids:
        await callback.message.edit_text(lexicon.get('failed_to_add_artists'))
        await callback.answer()
        await state.clear()
        return

    # 2. Ищем будущие события для только что добавленных артистов
    found_events = await db.get_future_events_for_artists(added_artist_ids)
    
    # Редактируем исходное сообщение, чтобы пользователь видел, что процесс идет
    # (например, "Добавлено N артистов. Ищем события...")
    initial_feedback_text = lexicon.get('favorites_added_final').format(count=len(added_artist_names))
    await callback.message.edit_text(initial_feedback_text, parse_mode="HTML")

    # 3. Проверяем, нашлись ли события
    if not found_events:
        # Событий нет. Сообщаем об этом и завершаем.
        no_events_text = "\n\n" + lexicon.get('no_future_events_for_favorites')
        await callback.message.answer(no_events_text) # Отправляем доп. сообщение
        await callback.answer()
        await state.clear()
        return

    # 4. События найдены. Форматируем их и отправляем.
    # Вызываем наш новый форматер из utils.py
    response_text, event_ids_to_subscribe = await format_events_by_artist(found_events, lexicon)
    
    if not response_text:
        # На случай, если форматер ничего не вернул (например, все события оказались дублями)
        # Повторяем логику "событий не найдено"
        no_events_text = "\n\n" + lexicon.get('no_future_events_for_favorites')
        await callback.message.answer(no_events_text)
        await callback.answer()
        await state.clear()
        return

    # 5. Сохраняем ID найденных событий в FSM для следующего шага
    # и переводим пользователя в состояние ожидания ввода номеров.
    # Мы переиспользуем FSM из `afisha.py`!
    await state.set_state(AddToSubsFSM.waiting_for_event_numbers)
    await state.update_data(last_shown_event_ids=event_ids_to_subscribe)
    
    # 6. Отправляем большое сообщение с событиями и кнопкой "Добавить в подписки"
    # Используем send_long_message из афиши, чтобы обойти лимиты Telegram
    await send_long_message(
        message=callback.message,
        text=response_text,
        lexicon=lexicon,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
        # Клавиатура из афиши, которая ведет на `add_events_to_subs`
        reply_markup=kb.get_afisha_actions_keyboard(lexicon) 
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