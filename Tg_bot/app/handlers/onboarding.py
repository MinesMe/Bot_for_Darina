# app/handlers/onboarding.py

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold
from aiogram.filters.state import StateFilter

from ..database.requests import requests as db
from app import keyboards as kb
from ..lexicon import Lexicon,get_event_type_keys, get_event_type_storage_value
from aiogram.exceptions import TelegramBadRequest
# from app.handlers.afisha import Afisha

router = Router()


class Onboarding(StatesGroup):
    choosing_home_country = State()
    choosing_main_geo = State()
    choosing_home_city = State()
    waiting_for_city_search = State()
    asking_for_filter_setup = State()
    choosing_event_types = State()


async def finish_onboarding(callback_or_message: Message | CallbackQuery, state: FSMContext, is_setting_complete):
    user_id = callback_or_message.from_user.id
    data = await state.get_data()
    lexicon = Lexicon(callback_or_message.from_user.language_code)

    await db.update_user_preferences(
        user_id=user_id,
        home_country=data.get("home_country"),
        home_city=data.get("home_city"),
        event_types=data.get("selected_event_types", []),
        main_geo_completed=is_setting_complete != "False"
    )

    await state.clear()

    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.message.edit_text(lexicon.get('setup_complete'))
        await callback_or_message.message.answer(
            lexicon.get('main_menu_greeting').format(first_name=hbold(callback_or_message.from_user.first_name)),
            reply_markup=kb.get_main_menu_keyboard(lexicon),
            parse_mode=ParseMode.HTML
        )
    else:
        await callback_or_message.answer(
            lexicon.get('setup_complete'),
            reply_markup=kb.get_main_menu_keyboard(lexicon)
        )


async def start_onboarding_process(message: Message | CallbackQuery, state: FSMContext, lexicon: Lexicon):
    await state.clear()
    await state.set_state(Onboarding.choosing_home_country)

    countries_to_show = await db.get_countries(home_country_selection=True)

    text = lexicon.get('settings_intro')
    if isinstance(message, Message):
        text = lexicon.get('welcome').format(first_name=hbold(message.from_user.first_name))

    action = message.answer if isinstance(message, Message) else message.message.edit_text

    # --- ИСПРАВЛЕНИЕ: Используем правильное имя функции клавиатуры ---
    await action(
        text,
        reply_markup=kb.get_country_selection_keyboard(countries_to_show, lexicon),
        parse_mode=ParseMode.HTML
    )
    if isinstance(message, CallbackQuery):
        await message.answer()

# async def toggle_event_type(callback: CallbackQuery, state: FSMContext):
#     event_type = callback.data.split(":")[1]
#     data = await state.get_data()
#     selected = data.get("selected_event_types", [])

#     if event_type in selected:
#         selected.remove(event_type)
#     else:
#         selected.append(event_type)

#     await state.update_data(selected_event_types=selected)
#     lexicon = Lexicon(callback.from_user.language_code)
#     await callback.message.edit_reply_markup(
#         reply_markup=kb.get_event_type_selection_keyboard(lexicon, selected)
#     )
#     await callback.answer()


async def search_for_city(callback: CallbackQuery, state: FSMContext, send_from):
    await state.update_data(msg_id_to_edit=callback.message.message_id)
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.edit_text(lexicon.get('search_city_prompt'))
    await callback.answer()

async def city_search(message: Message, state: FSMContext, send_from, country_name):
    data = await state.get_data()
    msg_id_to_edit = data.get("msg_id_to_edit")
    lexicon = Lexicon(message.from_user.language_code)

    await message.delete()
    if not msg_id_to_edit: return

    best_matches = await db.find_cities_fuzzy(country_name, message.text)

    # await state.set_state(Onboarding.choosing_home_city)
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
            reply_markup=kb.get_found_home_cities_keyboard(best_matches, lexicon)
        )





@router.callback_query(Onboarding.choosing_home_country, F.data.startswith("main_geo_settings") )
async def cq_select_home_country(callback: CallbackQuery, state: FSMContext):
    country_name = callback.data.split(":")[1]
    await state.update_data(home_country=country_name)
    lexicon = Lexicon(callback.from_user.language_code)

    text = lexicon.get('onboarding_country_selected_prompt').format(country_name=hbold(country_name))
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_main_geo_settings(lexicon),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(Onboarding.choosing_home_country, F.data.startswith("select_home_country"))
async def cq_select_home_country(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    country_name = user_data.get("home_country")
    await state.update_data(home_country=country_name)
    await state.set_state(Onboarding.choosing_home_city)

    lexicon = Lexicon(callback.from_user.language_code)
    top_cities = await db.get_top_cities_for_country(country_name)

    text = lexicon.get('onboarding_city_selection_prompt').format(country_name=hbold(country_name))
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_home_city_selection_keyboard(top_cities, lexicon),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(Onboarding.choosing_home_city, F.data.startswith("select_home_city:"))
async def cq_select_home_city(callback: CallbackQuery, state: FSMContext):
    city_name = callback.data.split(":")[1]
    await state.update_data(home_city=city_name)
    await state.set_state(Onboarding.asking_for_filter_setup)
    lexicon = Lexicon(callback.from_user.language_code)
    await state.set_state(Onboarding.choosing_event_types)
    await state.update_data(selected_event_types=[])
    text = lexicon.get('onboarding_event_type_prompt').format(city_name=hbold(city_name))
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_event_type_selection_keyboard(lexicon),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(Onboarding.choosing_home_city, F.data == "search_for_home_city")
async def cq_search_for_city(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Onboarding.waiting_for_city_search)
    await state.update_data(msg_id_to_edit=callback.message.message_id)
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.edit_text(lexicon.get('search_city_prompt'))
    await callback.answer()


@router.message(Onboarding.waiting_for_city_search, F.text)
async def process_city_search(message: Message, state: FSMContext):
    data = await state.get_data()
    country_name = data.get("home_country")
    msg_id_to_edit = data.get("msg_id_to_edit")
    lexicon = Lexicon(message.from_user.language_code)

    await message.delete()
    if not msg_id_to_edit: return

    best_matches = await db.find_cities_fuzzy(country_name, message.text)
    await state.set_state(Onboarding.choosing_home_city)

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
            reply_markup=kb.get_found_home_cities_keyboard(best_matches, lexicon)
        )


@router.callback_query(Onboarding.choosing_home_city, F.data == "back_to_city_selection")
async def cq_back_to_city_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    country_name = data.get("home_country")
    lexicon = Lexicon(callback.from_user.language_code)
    top_cities = await db.get_top_cities_for_country(country_name)
    text = lexicon.get('onboarding_back_to_city_prompt').format(country_name=hbold(country_name))
    await callback.message.edit_text(
        text,
        reply_markup=kb.get_home_city_selection_keyboard(top_cities, lexicon),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(Onboarding.choosing_event_types, F.data.startswith("toggle_event_type:"))
async def cq_toggle_event_type(callback: CallbackQuery, state: FSMContext):
    event_type_key = callback.data.split(":")[1]
    
    data = await state.get_data()
    selected_values = data.get("selected_event_types", [])

    all_event_keys = get_event_type_keys()
    all_storage_values = [get_event_type_storage_value(key) for key in all_event_keys]
    
    # --- ИСПРАВЛЕННАЯ ЛОГИКА ---
    
    if event_type_key == 'all':
        # Если нажата кнопка "Выбрать/Снять все"
        current_selection_set = set(selected_values)
        all_values_set = set(all_storage_values)
        
        # Если выбраны не все, то выбираем все. Иначе - очищаем.
        if current_selection_set != all_values_set:
            selected_values = all_storage_values
        else:
            selected_values = []
    else:
        # Если нажата обычная кнопка с типом события
        if event_type_key in selected_values:
            selected_values.remove(event_type_key)
        else:
            selected_values.append(event_type_key)
            
    # --- КОНЕЦ ИСПРАВЛЕННОЙ ЛОГИКИ ---

    # Сохраняем обновленный список в state
    await state.update_data(selected_event_types=selected_values)
    
    lexicon = Lexicon(callback.from_user.language_code)
    
    try:
        # Перерисовываем клавиатуру с новым состоянием
        await callback.message.edit_reply_markup(
            reply_markup=kb.get_event_type_selection_keyboard(lexicon, selected_values)
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    
    await callback.answer() 


@router.callback_query(StateFilter(Onboarding.choosing_event_types, Onboarding.choosing_home_country), F.data.startswith("finish_preferences_selection:"))
async def cq_finish_preferences_selection(callback: CallbackQuery, state: FSMContext):
    is_setting_complete = callback.data.split(":")[1]
    data = await state.get_data()
    event_types=data.get("selected_event_types", [])
    if is_setting_complete != "False" and (event_types == []):
        lexicon = Lexicon(callback.from_user.language_code)
        await callback.message.answer(lexicon.get('select_at_least_one_event_type_alert'))
        await callback.answer()
    else:
        await finish_onboarding(callback, state, is_setting_complete)


@router.callback_query(F.data == 'ignore')
async def cq_ignore(callback: CallbackQuery):
    await callback.answer()