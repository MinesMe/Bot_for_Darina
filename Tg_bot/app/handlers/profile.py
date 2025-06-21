# app/handlers/profile.py

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold

from ..database import requests as db
from .. import keyboards as kb
from ..lexicon import Lexicon
from .subscriptions import SubscriptionFlow 

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
    countries_to_show = await db.get_countries(home_country_selection=True)
    await callback.message.edit_text(
        "Выберите вашу страну проживания:",
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
    await callback.message.edit_text(
        f"Страна: {hbold(country_name)}. Теперь выберите город.",
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
    """Возвращает к списку городов после поиска."""
    # Просто вызываем хэндлер выбора страны, он перерисует меню городов
    await cq_edit_country_selected(callback, state)

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
    await callback.message.edit_text(
        f"Город: {hbold(city_name)}. Теперь выберите интересующие типы событий.",
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
    if not selected_event_types:
        await callback.answer("Пожалуйста, выберите хотя бы один тип событий.", show_alert=True)
        return
    await db.update_user_preferences(
        user_id=callback.from_user.id,
        home_country=data.get("home_country"),
        home_city=data.get("home_city"),
        event_types=selected_event_types,
        main_geo_completed=True
    )
    await callback.answer("Настройки успешно изменены!", show_alert=True)
    await show_profile_menu(callback, state)


# --- Флоу редактирования ОБЩЕЙ МОБИЛЬНОСТИ ---
@router.callback_query(F.data == "edit_general_mobility")
async def cq_edit_general_mobility(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.selecting_general_regions)
    current_regions = await db.get_general_mobility(callback.from_user.id) or []
    await state.update_data(selected_regions=current_regions)
    all_countries = await db.get_countries()
    await callback.message.edit_text(
        "Измените свой список стран для 'общей мобильности'.",
        reply_markup=kb.get_region_selection_keyboard(
            all_countries, current_regions, finish_callback="finish_general_edit_from_profile"
        )
    )
    await callback.answer()

@router.callback_query(SubscriptionFlow.selecting_general_regions, F.data == "finish_general_edit_from_profile")
async def cq_finish_general_edit_from_profile(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    if not regions:
        await callback.answer("Нужно выбрать хотя бы один регион!", show_alert=True)
        return
    await db.set_general_mobility(callback.from_user.id, regions)
    await callback.answer("✅ Общие настройки мобильности сохранены!", show_alert=True)
    await show_profile_menu(callback, state)


# --- Флоу управления ПОДПИСКАМИ ---
async def show_subscriptions_list(callback: CallbackQuery, state: FSMContext):
    await state.clear() 
    user_id = callback.from_user.id
    subs = await db.get_user_subscriptions(user_id)
    text = "Твои подписки:\nНажми на любую, чтобы управлять ей." if subs else "У тебя пока нет подписок."
    await callback.message.edit_text(
        text=text,
        reply_markup=kb.get_manage_subscriptions_keyboard(subs)
    )
    await callback.answer()

@router.callback_query(F.data == "manage_my_subscriptions")
async def cq_manage_my_subscriptions(callback: CallbackQuery, state: FSMContext):
    await show_subscriptions_list(callback, state)
    
@router.callback_query(F.data == "back_to_subscriptions_list")
async def cq_back_to_subscriptions_list(callback: CallbackQuery, state: FSMContext):
    await show_subscriptions_list(callback, state)

@router.callback_query(F.data.startswith("view_subscription:"))
async def cq_view_subscription(callback: CallbackQuery, state: FSMContext):
    item_name = callback.data.split(":", 1)[1]
    sub_details = await db.get_subscription_details(callback.from_user.id, item_name)
    if not sub_details:
        await callback.answer("Подписка не найдена. Возможно, она была удалена.", show_alert=True)
        await show_subscriptions_list(callback, state)
        return
    regions_str = ", ".join(sub_details.regions) if sub_details.regions else "Не заданы"
    text = (f"Подписка: {hbold(item_name)}\n\n"
            f"🌍 Регионы отслеживания: {regions_str}")
    await state.set_state(ProfileFSM.viewing_subscription)
    await state.update_data(viewing_item_name=item_name)
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_single_subscription_manage_keyboard(item_name),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(ProfileFSM.viewing_subscription, F.data.startswith("delete_subscription:"))
async def cq_delete_subscription(callback: CallbackQuery, state: FSMContext):
    item_name = callback.data.split(":", 1)[1]
    await db.remove_subscription(callback.from_user.id, item_name)
    await callback.answer(f"Подписка на {item_name} удалена.", show_alert=True)
    await show_subscriptions_list(callback, state)

@router.callback_query(ProfileFSM.viewing_subscription, F.data.startswith("edit_sub_regions:"))
async def cq_edit_subscription_regions(callback: CallbackQuery, state: FSMContext):
    item_name = callback.data.split(":", 1)[1]
    await state.update_data(editing_item_name=item_name)
    current_sub = await db.get_subscription_details(callback.from_user.id, item_name)
    current_regions = current_sub.regions if current_sub else []
    await state.set_state(ProfileFSM.editing_subscription_regions)
    await state.update_data(selected_regions=current_regions)
    all_countries = await db.get_countries()
    await callback.message.edit_text(
        f"Редактирование регионов для подписки: {hbold(item_name)}",
        reply_markup=kb.get_region_selection_keyboard(all_countries, current_regions, finish_callback="finish_subscription_edit"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(ProfileFSM.editing_subscription_regions, F.data.startswith("toggle_region:"))
async def cq_toggle_region_for_edit(callback: CallbackQuery, state: FSMContext):
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
        reply_markup=kb.get_region_selection_keyboard(all_countries, selected, finish_callback="finish_subscription_edit")
    )
    await callback.answer()

@router.callback_query(ProfileFSM.editing_subscription_regions, F.data == "finish_subscription_edit")
async def cq_finish_subscription_edit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_regions = data.get("selected_regions", [])
    item_name = data.get("editing_item_name")
    if not new_regions:
        await callback.answer("Нужно выбрать хотя бы один регион!", show_alert=True)
        return
    await db.update_subscription_regions(callback.from_user.id, item_name, new_regions)
    await callback.answer("Регионы для подписки обновлены!", show_alert=True)
    await show_subscriptions_list(callback, state)