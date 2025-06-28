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
from .subscriptions import SubscriptionFlow 
from ..database.models import Event, Subscription # Импортируем модели для type hinting

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
    await state.clear()
    lexicon = Lexicon(callback_or_message.from_user.language_code)
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
    await state.set_state(EditMainGeoFSM.waiting_city_input)
    await state.update_data(msg_id_to_edit=callback.message.message_id)
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.edit_text(lexicon.get('search_city_prompt'))
    await callback.answer()

@router.message(EditMainGeoFSM.waiting_city_input, F.text)
async def process_edit_city_search(message: Message, state: FSMContext):
    """Обрабатывает введенный текст для поиска города."""
    data = await state.get_data()
    country_name = data.get("home_country")
    msg_id_to_edit = data.get("msg_id_to_edit")
    lexicon = Lexicon(message.from_user.language_code)
    await message.delete()
    if not msg_id_to_edit: return
    
    best_matches = await db.find_cities_fuzzy(country_name, message.text)
    await state.set_state(EditMainGeoFSM.choosing_city)
    
    if not best_matches:
        await message.bot.edit_message_text(
            chat_id=message.chat.id, message_id=msg_id_to_edit,
            text=lexicon.get('city_not_found'),
            reply_markup=kb.get_back_to_city_selection_keyboard(lexicon)
        )
    else:
        await message.bot.edit_message_text(
            chat_id=message.chat.id, message_id=msg_id_to_edit,
            text=lexicon.get('city_found_prompt'),
            reply_markup=kb.get_edit_found_cities_keyboard(best_matches, lexicon)
        )

@router.callback_query(EditMainGeoFSM.choosing_city, F.data == "back_to_edit_city_list")
async def cq_back_to_edit_city_list(callback: CallbackQuery, state: FSMContext):
    """Возвращает к списку городов после неудачного поиска."""
    # Мы не можем вызывать cq_edit_country_selected, так как у нас нет callback.data с именем страны.
    # Вместо этого мы должны сами получить страну из состояния FSM и сгенерировать меню.
    
    data = await state.get_data()
    country_name = data.get("home_country")
    lexicon = Lexicon(callback.from_user.language_code)
    
    if not country_name:
        # Если в состоянии нет страны (маловероятно, но возможно), возвращаемся в профиль
        await callback.answer(lexicon.get('generic_error_try_again'), show_alert=True)
        await show_profile_menu(callback, state)
        return

    # Теперь мы делаем то же самое, что и cq_edit_country_selected, но с данными из state
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

@router.callback_query(EditMainGeoFSM.choosing_city, F.data.startswith("edit_city:"))
async def cq_edit_city_selected(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор города в режиме редактирования."""
    city_name = callback.data.split(":", 1)[1]
    await state.update_data(home_city=city_name)
    await state.set_state(EditMainGeoFSM.choosing_event_types)
    lexicon = Lexicon(callback.from_user.language_code)
    prefs = await db.get_user_preferences(callback.from_user.id)
    current_types = prefs.get("preferred_event_types", []) if prefs else []
    await state.update_data(selected_event_types=current_types)
    text = lexicon.get('edit_geo_event_types_prompt').format(city_name=hbold(city_name))    
    await callback.message.edit_text(
        text    ,
        reply_markup=kb.get_edit_event_type_keyboard(lexicon, current_types),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(EditMainGeoFSM.choosing_event_types, F.data.startswith("edit_toggle_event_type:"))
async def cq_edit_toggle_type(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор/снятие типа события в режиме редактирования."""
    event_type = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_event_types", [])
    if event_type in selected: selected.remove(event_type)
    else: selected.append(event_type)
    await state.update_data(selected_event_types=selected)
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.edit_reply_markup(reply_markup=kb.get_edit_event_type_keyboard(lexicon, selected))
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
    await state.clear() 
    user_id = callback_or_message.from_user.id
    lexicon = Lexicon(callback_or_message.from_user.language_code)
    
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

@router.callback_query(F.data == "manage_my_subscriptions")
async def cq_manage_my_subscriptions(callback: CallbackQuery, state: FSMContext):
    await show_subscriptions_list(callback, state)
    
@router.callback_query(F.data == "back_to_subscriptions_list")
async def cq_back_to_subscriptions_list(callback: CallbackQuery, state: FSMContext):
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
    await callback.answer(lexicon.get('subs_removed_alert'), show_alert=True)
    
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

