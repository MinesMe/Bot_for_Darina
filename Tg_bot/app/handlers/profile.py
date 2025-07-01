# app/handlers/profile.py

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold

from ..database.requests import requests as db
from app import keyboards as kb
from ..lexicon import Lexicon
from .states import SubscriptionFlow 
from ..database.models import Event, Subscription # Импортируем модели для type hinting
from aiogram.exceptions import TelegramBadRequest
from ..lexicon import get_event_type_keys, get_event_type_storage_value
from app.handlers.favorities import show_favorites_list
from .search_cities import start_city_search, process_city_input, back_to_city_list
from aiogram.filters import Command, or_f # Добавляем or_f

router = Router()

# FSM для редактирования основного гео
class EditMainGeoFSM(StatesGroup):
    choosing_country = State()
    choosing_city = State()
    waiting_city_input = State()
    choosing_event_types = State()

# FSM для управления подписками
class ProfileFSM(StatesGroup):
    viewing_subscription = State()
    editing_subscription_regions = State()

class EditMobilityFSM(StatesGroup):
    selecting_regions = State()


# --- Хелперы и главное меню профиля ---
async def show_profile_menu(callback_or_message: Message | CallbackQuery, state: FSMContext):
    """Вспомогательная функция для показа главного меню профиля."""
    current_data = await state.get_data()
    data_to_keep = {
        'messages_to_delete_on_expire': current_data.get('messages_to_delete_on_expire'),
        'last_shown_event_ids': current_data.get('last_shown_event_ids')
    }
    await state.clear()
    data_to_restore = {k: v for k, v in data_to_keep.items() if v is not None}
    if data_to_restore:
        await state.update_data(data_to_restore)
    user_lang = await db.get_user_lang(callback_or_message.from_user.id)
    lexicon = Lexicon(user_lang)
    text = lexicon.get('profile_menu_header')
    markup = kb.get_profile_keyboard(lexicon)
    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.message.edit_text(text=text, reply_markup=markup)
    else:
        await callback_or_message.answer(text=text, reply_markup=markup)

@router.message(Command('settings'))
@router.message(F.text.in_(['👤 Профиль', '👤 Profile', '👤 Профіль']))
async def menu_profile(message: Message, state: FSMContext):
    """Точка входа в меню 'Профиль'."""
    await show_profile_menu(message, state)

@router.callback_query(F.data == "back_to_profile")
async def cq_back_to_profile(callback: CallbackQuery, state: FSMContext):
    """Возвращает пользователя в главное меню профиля."""
    await show_profile_menu(callback, state)
    await callback.answer()


# --- Флоу редактирования ОСНОВНОГО ГЕО (с поиском города) ---
@router.callback_query(F.data == "edit_main_geo")
async def cq_edit_main_geo_start(callback: CallbackQuery, state: FSMContext):
    """Начинает флоу редактирования основного гео."""
    await state.set_state(EditMainGeoFSM.choosing_country)
    lexicon = Lexicon(callback.from_user.language_code)
    text = lexicon.get('edit_geo_choose_country_prompt')
    countries_to_show = await db.get_countries(home_country_selection=True)
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_edit_country_keyboard(countries_to_show, lexicon)
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_edit_country")
async def cq_back_to_edit_country(callback: CallbackQuery, state: FSMContext):
    """Возвращает к выбору страны в режиме редактирования."""
    await cq_edit_main_geo_start(callback, state)

@router.callback_query(EditMainGeoFSM.choosing_country, F.data.startswith("edit_country:"))
async def cq_edit_country_selected(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор страны в режиме редактирования."""
    country_name = callback.data.split(":", 1)[1]
    await state.update_data(home_country=country_name)
    await state.set_state(EditMainGeoFSM.choosing_city)
    lexicon = Lexicon(callback.from_user.language_code)
    top_cities = await db.get_top_cities_for_country(country_name)
    text = lexicon.get('edit_geo_city_prompt').format(country_name=hbold(country_name))
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_edit_city_keyboard(top_cities, lexicon),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(EditMainGeoFSM.choosing_city, F.data == "edit_search_for_city")
async def cq_edit_search_for_city(callback: CallbackQuery, state: FSMContext):
    """Начинает поиск города в режиме редактирования."""
    await start_city_search(
        callback, 
        state, 
        new_state=EditMainGeoFSM.waiting_city_input,
        back_callback="back_to_edit_city_list"
    )


@router.message(EditMainGeoFSM.waiting_city_input, F.text)
async def process_edit_city_search(message: Message, state: FSMContext):
    """Обрабатывает введенный текст для поиска города."""
    await process_city_input(
        message=message,
        state=state,
        country_key="home_country",
        return_state=EditMainGeoFSM.choosing_city,
        found_cities_kb=kb.get_edit_found_cities_keyboard
    )


@router.callback_query(or_f(EditMainGeoFSM.choosing_city, EditMainGeoFSM.waiting_city_input), F.data == "back_to_edit_city_list")
async def cq_back_to_edit_city_list(callback: CallbackQuery, state: FSMContext):
    """Возвращает к списку городов после неудачного поиска."""
    await state.set_state(EditMainGeoFSM.choosing_city)
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    await back_to_city_list(
        callback=callback,
        state=state,
        country_key="home_country",
        city_prompt_key='edit_geo_city_prompt',
        city_selection_kb=kb.get_edit_city_keyboard
    )

@router.callback_query(EditMainGeoFSM.choosing_city, F.data.startswith("edit_city:"))
async def cq_edit_city_selected(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор города в режиме редактирования."""
    city_name = callback.data.split(":", 1)[1]
    await state.update_data(home_city=city_name)
    await state.set_state(EditMainGeoFSM.choosing_event_types)
    
    lexicon = Lexicon(callback.from_user.language_code)
    
    # --- ИЗМЕНЕНИЕ: Загружаем текущие предпочтения из БД ---
    prefs = await db.get_user_preferences(callback.from_user.id)
    current_types = prefs.get("preferred_event_types", []) if prefs else []
    
    # Сохраняем их в state, чтобы хэндлер toggle мог с ними работать
    await state.update_data(selected_event_types=current_types)
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    text = lexicon.get('edit_geo_event_types_prompt').format(city_name=hbold(city_name))    
    await callback.message.edit_text(
        text,
        # Передаем текущие типы в клавиатуру, чтобы она отрисовала галочки
        reply_markup=kb.get_edit_event_type_keyboard(lexicon, current_types),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(EditMainGeoFSM.choosing_event_types, F.data.startswith("edit_toggle_event_type:"))
async def cq_edit_toggle_type(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор/снятие типа события в режиме редактирования."""
    event_type_key = callback.data.split(":")[1]
    
    data = await state.get_data()
    selected_values = data.get("selected_event_types", [])

    all_event_keys = get_event_type_keys()
    all_storage_values = [get_event_type_storage_value(key) for key in all_event_keys]
    
    # --- НОВАЯ ЛОГИКА ДЛЯ ОБРАБОТКИ КНОПОК ---
    if event_type_key == 'all':
        current_selection_set = set(selected_values)
        all_values_set = set(all_storage_values)
        
        if current_selection_set != all_values_set:
            selected_values = all_storage_values
        else:
            selected_values = []
    else:
        if event_type_key in selected_values:
            selected_values.remove(event_type_key)
        else:
            selected_values.append(event_type_key)
    # --- КОНЕЦ НОВОЙ ЛОГИКИ ---

    await state.update_data(selected_event_types=selected_values)
    lexicon = Lexicon(callback.from_user.language_code)
    
    try:
        await callback.message.edit_reply_markup(
            reply_markup=kb.get_edit_event_type_keyboard(lexicon, selected_values)
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    
    await callback.answer()

@router.callback_query(EditMainGeoFSM.choosing_event_types, F.data == "finish_edit_preferences")
async def cq_edit_finish(callback: CallbackQuery, state: FSMContext):
    """Завершает редактирование основного гео и возвращает в профиль."""
    data = await state.get_data()
    selected_event_types = data.get("selected_event_types", [])
    lexicon = Lexicon(callback.from_user.language_code)
    if not selected_event_types:
        await callback.answer(lexicon.get('select_at_least_one_event_type_alert'), show_alert=True)
        return
    await db.update_user_preferences(
        user_id=callback.from_user.id,
        home_country=data.get("home_country"),
        home_city=data.get("home_city"),
        event_types=selected_event_types,
        main_geo_completed=True
    )
    await callback.answer(lexicon.get('settings_changed_successfully_alert'), show_alert=True)
    await show_profile_menu(callback, state)


# --- Флоу редактирования ОБЩЕЙ МОБИЛЬНОСТИ ---
@router.callback_query(F.data == "edit_general_mobility")
async def cq_edit_general_mobility(callback: CallbackQuery, state: FSMContext):
    """Начинает флоу редактирования общей мобильности, используя СВОЮ FSM."""
    # Устанавливаем состояние из НАШЕЙ новой FSM
    await state.set_state(EditMobilityFSM.selecting_regions)
    user_lang = callback.message.from_user.language_code
    lexicon = Lexicon(user_lang)
    
    current_regions = await db.get_general_mobility(callback.from_user.id) or []
    await state.update_data(selected_regions=current_regions) # Сохраняем текущий выбор
    all_countries = await db.get_countries()
    
    await callback.message.edit_text(
        lexicon.get('edit_mobility_prompt'),
        reply_markup=kb.get_region_selection_keyboard(
            all_countries, 
            current_regions, 
            finish_callback="finish_mobility_edit",
            back_callback="back_to_profile" ,
            lexicon=lexicon
        )
    )
    await callback.answer()

@router.callback_query(SubscriptionFlow.selecting_general_regions, F.data == "finish_general_edit_from_profile")
async def cq_finish_general_edit_from_profile(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    lexicon = Lexicon(callback.from_user.language_code)
    
    if not regions:
        await callback.answer(lexicon.get('no_regions_selected_alert'), show_alert=True)
        return

    await db.set_general_mobility(callback.from_user.id, regions)
    await callback.answer(lexicon.get('mobility_saved_alert'), show_alert=True)
    
    # Возвращаемся в меню профиля, а не продолжаем флоу подписок
    await show_profile_menu(callback, state)


# --- Флоу управления ПОДПИСКАМИ ---
async def show_subscriptions_list(callback_or_message: Message | CallbackQuery, state: FSMContext):
    """Показывает список подписок на события."""
    current_data = await state.get_data()
    data_to_keep = {
        'messages_to_delete_on_expire': current_data.get('messages_to_delete_on_expire'),
        'last_shown_event_ids': current_data.get('last_shown_event_ids')
    }
    await state.clear()
    data_to_restore = {k: v for k, v in data_to_keep.items() if v is not None}
    if data_to_restore:
        await state.update_data(data_to_restore)
    user_id = callback_or_message.from_user.id
    user_lang = await db.get_user_lang(callback_or_message.from_user.id)
    lexicon = Lexicon(user_lang)
    
    subs = await db.get_user_subscriptions(user_id)
    
    text = lexicon.get('subs_menu_header_active')
    if not subs:
        text = lexicon.get('subs_menu_header_empty')
    
    markup = kb.get_manage_subscriptions_keyboard(subs, lexicon)

    # ИЗМЕНЕНИЕ: Правильно определяем, редактировать или отправлять новое сообщение
    if isinstance(callback_or_message, CallbackQuery):
        # Если это callback, всегда редактируем
        await callback_or_message.message.edit_text(text=text, reply_markup=markup)
        await callback_or_message.answer()
    else:
        # Если это сообщение, отправляем новое
        await callback_or_message.answer(text=text, reply_markup=markup)


@router.message(F.text.in_(['⭐ Мои подписки', '⭐ My Subs']))
async def menu_show_subscriptions(message: Message, state: FSMContext):
    """Точка входа для показа подписок на события с главной клавиатуры."""
    await show_subscriptions_list(message, state)

@router.callback_query(F.data == "manage_favorites")
async def cq_manage_favorites(callback: CallbackQuery, state: FSMContext):
    """Точка входа в раздел 'Избранное' из меню профиля."""
    # Просто вызываем функцию, которая умеет показывать список избранных
    await show_favorites_list(callback, state, True)

    
@router.callback_query(F.data == "back_to_subscriptions_list")
async def cq_back_to_subscriptions_list(callback: CallbackQuery, state: FSMContext):
    print('a')
    await show_subscriptions_list(callback, state)

@router.callback_query(F.data.startswith("view_subscription:"))
async def cq_view_subscription(callback: CallbackQuery, state: FSMContext):
    """Показывает детальную информацию по одной подписке."""
    lexicon = Lexicon(callback.from_user.language_code)
    try:
        event_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer(lexicon.get('invalid_event_id_error'), show_alert=True)
        return

    sub_details = await db.get_subscription_details(callback.from_user.id, event_id)
    
    # Получаем детали события напрямую, без новой функции
    async with db.async_session() as session:
        event_details = await session.get(Event, event_id)

    if not sub_details or not event_details:
        print('b')
        await callback.answer(lexicon.get('sub_or_event_not_found_error'), show_alert=True)
        await show_subscriptions_list(callback, state)
        return

    lexicon = Lexicon(callback.from_user.language_code)
    status_text = lexicon.get('subs_status_active') if sub_details.status == 'active' else lexicon.get('subs_status_paused')
    date_str = event_details.date_start.strftime('%d.%m.%Y %H:%M') if event_details.date_start else lexicon.get('date_not_specified')
    
    text = lexicon.get('subscription_details_view').format(
        title=hbold(event_details.title),
        date=date_str,
        status=status_text
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_single_subscription_manage_keyboard(event_id, sub_details.status, lexicon),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_sub_status:"))
async def cq_toggle_subscription_status(callback: CallbackQuery, state: FSMContext):
    """Переключает статус подписки (active/paused)."""
    lexicon = Lexicon(callback.from_user.language_code)
    try:
        event_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        await callback.answer(lexicon.get('invalid_event_id_error'), show_alert=True)
        return
        
    user_id = callback.from_user.id
    lexicon = Lexicon(callback.from_user.language_code)
    
    current_sub = await db.get_subscription_details(user_id, event_id)
    
    if current_sub:
        new_status = 'paused' if current_sub.status == 'active' else 'active'
        await db.set_subscription_status(user_id, event_id, new_status)
        
        alert_text = lexicon.get('subs_paused_alert') if new_status == 'paused' else lexicon.get('subs_resumed_alert')
        await callback.answer(alert_text, show_alert=True)
        
        # ИЗМЕНЕНИЕ: Передаем сам объект callback, а не callback.message
        await show_subscriptions_list(callback, state)
    else:
        await callback.answer(lexicon.get('subs_not_found_alert'), show_alert=True)

@router.callback_query(F.data.startswith("delete_subscription:"))
async def cq_delete_subscription(callback: CallbackQuery, state: FSMContext):
    lexicon = Lexicon(callback.from_user.language_code)
    try:
        event_id = int(callback.data.split(":", 1)[1])
    except (ValueError, IndexError):
        await callback.answer(lexicon.get('invalid_event_id_error'), show_alert=True)
        return
    
    # 1. Вызываем функцию удаления из БД
    await db.remove_subscription(callback.from_user.id, event_id)
    
    # 2. Сообщаем пользователю об успехе
    lexicon = Lexicon(callback.from_user.language_code)
    
    # 3. Обновляем список подписок, чтобы пользователь увидел изменения
    # ВАЖНО: Мы должны передать state, так как show_subscriptions_list его ожидает
    await show_subscriptions_list(callback, state)  




@router.callback_query(EditMobilityFSM.selecting_regions, F.data.startswith("toggle_region:"))
async def cq_toggle_mobility_region(callback: CallbackQuery, state: FSMContext):
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
    
    # Перерисовываем клавиатуру с тем же уникальным callback
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_region_selection_keyboard(
            all_countries, selected, finish_callback="finish_mobility_edit", back_callback="back_to_profile",
            lexicon=lexicon
        )
    )
    await callback.answer()

@router.callback_query(EditMobilityFSM.selecting_regions, F.data == "finish_mobility_edit")
async def cq_finish_mobility_edit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    lexicon = Lexicon(callback.from_user.language_code)

    await db.set_general_mobility(callback.from_user.id, regions)
    await callback.answer(lexicon.get('mobility_saved_alert'), show_alert=True)
    
    # Возвращаемся в меню профиля
    await show_profile_menu(callback, state)

