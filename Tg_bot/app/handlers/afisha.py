# app/handlers/afisha.py

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold

from ..database import requests as db
from .. import keyboards as kb
from ..lexicon import Lexicon
from .common import format_grouped_events_for_response, format_events_for_response
from app.handlers.onboarding import city_search as onboarding_city_search, \
                                    toggle_event_type as onboarding_toggle_event_type, \
                                    search_for_city as onboarding_search_for_city

router = Router()

class AfishaFSM(StatesGroup): # Переименовал для ясности
    choosing_city = State()           # Состояние выбора города (из списка или после поиска)
    waiting_city_input = State()    # Состояние ожидания ввода текста для поиска города
    choosing_event_types = State()    # Состояние выбора типов событий (бывший main_geo_setting)

class SearchGlobalFSM(StatesGroup): # Переименовал для ясности
    waiting_for_query = State()
    

@router.message(F.text.in_(['🗓 Афиша', '🗓 Events', '🗓 Афіша']))
async def menu_afisha(message: Message, state: FSMContext):
    await state.clear() 
    is_main_geo = await db.check_main_geo_status(message.from_user.id)
    lexicon = Lexicon(message.from_user.language_code) 

    if not is_main_geo: 
        await state.update_data(is_settings_complete=False) 
        await message.answer(
            lexicon.get('afisha_prompt_no_main_settings_v2'),
            reply_markup=kb.get_afisha_settings() 
        )
    else:
        await state.update_data(is_settings_complete=True) 
        await message.answer(
            lexicon.get('afisha_prompt_with_main_settings_v2'), 
            reply_markup=kb.get_afisha_settings_type() 
        )

@router.callback_query(
    F.data.in_([
        "afisha_main_geo_settings", # От kb.get_afisha_settings() -> "Настроить"
        "skip_afisha_main_geo",     # От kb.get_afisha_settings() -> "Пропустить настройку"
        "afisha_another_type_settings" # От kb.get_afisha_settings_type() -> "Другую"
    ]) 
    # Примечание: Я изменил F.data.startswith на F.data.in_ для тех callback_data,
    # которые не должны иметь суффикса. Если у вас они имеют суффикс, верните startswith.
    # В вашем keyboards.py для этих кнопок нет суффиксов.
)
async def afisha_start_fsm_setup(callback: CallbackQuery, state:FSMContext): 
    # await state.set_state(Afisha.main_geo_setting) # НЕПРАВИЛЬНОЕ НАЧАЛЬНОЕ СОСТОЯНИЕ ЗДЕСЬ
    cq_data = callback.data
    user_id = callback.from_user.id
    lexicon = Lexicon(callback.from_user.language_code)
    
    current_fsm_data = await state.get_data() 
    is_initial_setup_path = not current_fsm_data.get("is_settings_complete", True)

    if cq_data == "skip_afisha_main_geo":
        await state.update_data(is_settings_skipped_via_afisha=True) 
        await state.update_data(save_final_settings_as_main=False) 
    elif cq_data == "afisha_main_geo_settings" and is_initial_setup_path: # Это основной онбординг через афишу
        await state.update_data(is_settings_skipped_via_afisha=False)
        await state.update_data(save_final_settings_as_main=True) 
    else: # Это временная настройка (afisha_another_type_settings ИЛИ afisha_main_geo_settings когда is_settings_complete=True)
        await state.update_data(is_settings_skipped_via_afisha=True) 
        await state.update_data(save_final_settings_as_main=False) 

    user_prefs = await db.get_user_preferences(user_id)
    user_country = user_prefs.get('home_country') if user_prefs else None
    
    # Проверяем save_final_settings_as_main после того, как оно было установлено
    data_after_flag_set = await state.get_data()
    if data_after_flag_set.get("save_final_settings_as_main") and not user_country:
        await callback.message.edit_text(lexicon.get("afisha_error_country_needed_for_main_setup_v2"))
        await state.clear()
        await callback.answer()
        return
    
    if not user_country:
        await callback.message.edit_text(lexicon.get("afisha_error_country_not_set_v2"))
        await state.clear()
        await callback.answer()
        return

    await state.update_data(current_afisha_country=user_country) 
    
    # Устанавливаем правильное начальное состояние для выбора города
    await state.set_state(AfishaFSM.choosing_city) # ИСПРАВЛЕНО
    
    top_cities = await db.get_top_cities_for_country(user_country)
    try:
        await callback.message.edit_text(
            lexicon.get("afisha_select_city_prompt_v2").format(country_name=user_country),
            reply_markup=kb.get_home_city_selection_keyboard(top_cities, lexicon),
            parse_mode=ParseMode.HTML
        )
    except Exception: 
        await callback.message.answer(
             lexicon.get("afisha_select_city_prompt_v2").format(country_name=user_country),
            reply_markup=kb.get_home_city_selection_keyboard(top_cities, lexicon),
            parse_mode=ParseMode.HTML
        )
    await callback.answer()

# Этот хендлер ожидает состояние AfishaFSM.choosing_city
@router.callback_query(AfishaFSM.choosing_city, F.data == "search_for_home_city") # ИСПРАВЛЕНО состояние
async def afisha_fsm_ask_city_input(callback: CallbackQuery, state: FSMContext): 
    await state.set_state(AfishaFSM.waiting_city_input) # ИСПРАВЛЕНО состояние
    # Убедитесь, что onboarding_search_for_city правильно работает с state и callback
    await onboarding_search_for_city(callback, state, "Afisha_FSM_Search") 

@router.message(AfishaFSM.waiting_city_input, F.text) # ИСПРАВЛЕНО состояние
async def afisha_fsm_process_city_input(message: Message, state: FSMContext): 
    data = await state.get_data() 
    user_country = data.get('current_afisha_country') 
    lexicon = Lexicon(message.from_user.language_code)

    if not user_country:
        await message.reply(lexicon.get("error_state_lost_country_v2"))
        await state.clear()
        return
    
    # Убедитесь, что onboarding_city_search правильно работает с state и message
    # и не меняет состояние на свое собственное из onboarding.Onboarding FSM
    await onboarding_city_search(message, state, "Afisha_FSM_Search", user_country)
    await state.set_state(AfishaFSM.choosing_city) # ИСПРАВЛЕНО состояние, возвращаемся к выбору

@router.callback_query(AfishaFSM.choosing_city, F.data == "back_to_city_selection") # ИСПРАВЛЕНО состояние
async def afisha_fsm_back_to_city_list(callback: CallbackQuery, state:FSMContext): 
    data = await state.get_data() 
    user_country = data.get('current_afisha_country')
    lexicon = Lexicon(callback.from_user.language_code)

    if not user_country:
        await callback.message.edit_text(lexicon.get("error_state_lost_country_v2"))
        await state.clear()
        await callback.answer()
        return

    top_cities = await db.get_top_cities_for_country(user_country)
    await callback.message.edit_text(
        lexicon.get("afisha_select_city_prompt_v2").format(country_name=user_country),
        reply_markup=kb.get_home_city_selection_keyboard(top_cities, lexicon),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# Этот хендлер ТЕПЕРЬ ПРАВИЛЬНО ожидает состояние AfishaFSM.choosing_city
@router.callback_query(AfishaFSM.choosing_city, F.data.startswith("select_home_city:")) # ИСПРАВЛЕНО состояние
async def afisha_fsm_city_selected_ask_types(callback: CallbackQuery, state: FSMContext): 
    city_name = callback.data.split(":")[1]
    await state.update_data(current_afisha_city=city_name) 
    lexicon = Lexicon(callback.from_user.language_code)
    
    await state.set_state(AfishaFSM.choosing_event_types) # ИСПРАВЛЕНО состояние (бывший main_geo_setting)
    await state.update_data(current_afisha_event_types=[]) 
    
    await callback.message.edit_text(
        lexicon.get("afisha_city_selected_ask_types_v2").format(city_name=hbold(city_name)),
        reply_markup=kb.get_event_type_selection_keyboard(lexicon, []), 
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# Этот хендлер ожидает состояние AfishaFSM.choosing_event_types
@router.callback_query(AfishaFSM.choosing_event_types, F.data.startswith("toggle_event_type:")) # ИСПРАВЛЕНО состояние
async def afisha_fsm_toggle_type(callback: CallbackQuery, state: FSMContext): 
    event_type_toggled = callback.data.split(":")[1]
    data = await state.get_data() 
    current_selection = data.get("current_afisha_event_types", [])
    if event_type_toggled in current_selection:
        current_selection.remove(event_type_toggled)
    else:
        current_selection.append(event_type_toggled)
    await state.update_data(current_afisha_event_types=current_selection)
    
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_event_type_selection_keyboard(lexicon, current_selection)
    )
    await callback.answer()

@router.callback_query(F.data == "afisha_defautl_type_settings") 
async def afisha_display_by_saved_prefs(callback: CallbackQuery, state: FSMContext): 
    # ... (код этого хендлера остается без изменений, так как он не зависит от AfishaFSM) ...
    await state.clear() 
    user_id = callback.from_user.id
    lexicon = Lexicon(callback.from_user.language_code)
    user_prefs = await db.get_user_preferences(user_id)

    if not user_prefs or not user_prefs.get("home_city") or not user_prefs.get("preferred_event_types"):
        await callback.message.edit_text(
             lexicon.get("afisha_error_incomplete_main_settings_v2")
        )
        await callback.answer()
        return

    city_name = user_prefs["home_city"]
    preferred_event_types = user_prefs["preferred_event_types"]

    if not preferred_event_types: 
        await callback.message.edit_text(lexicon.get("afisha_error_no_types_in_main_settings_for_city_v2").format(city_name=city_name))
        await callback.answer()
        return

    header_text = lexicon.get('afisha_header_by_main_settings_v2').format(city_name=hbold(city_name))
    try:
        await callback.message.edit_text(header_text, parse_mode=ParseMode.HTML)
    except Exception: 
        await callback.message.answer(header_text, parse_mode=ParseMode.HTML)
    
    await callback.answer() 

    for event_type_name in preferred_event_types:
        await callback.message.answer(
            lexicon.get('afisha_loading_category_city_v2').format(category_name=event_type_name, city_name=hbold(city_name)),
            parse_mode=ParseMode.HTML
        )
        events = await db.get_grouped_events_by_city_and_category(city_name, event_type_name)
        response_text = await format_grouped_events_for_response(events)
        
        if not events:
            await callback.message.answer(lexicon.get('afisha_no_events_for_category_city_v2').format(city_name=hbold(city_name), category_name=event_type_name), parse_mode=ParseMode.HTML)
        else:
            await callback.message.answer(response_text, disable_web_page_preview=True, parse_mode=ParseMode.HTML)


# Этот хендлер ожидает состояние AfishaFSM.choosing_event_types
@router.callback_query(AfishaFSM.choosing_event_types, F.data.startswith("finish_preferences_selection:")) # ИСПРАВЛЕНО состояние
async def afisha_fsm_finish_and_display_events(callback: CallbackQuery, state: FSMContext): 
    # ... (код этого хендлера остается без изменений в части логики сохранения и отображения,
    # так как он уже полагался на флаг save_final_settings_as_main) ...
    is_confirmed_done = callback.data.split(":")[1] != "False" 
    
    data = await state.get_data() 
    lexicon = Lexicon(callback.from_user.language_code)
    
    city_name = data.get("current_afisha_city")
    selected_event_types = data.get("current_afisha_event_types", [])
    should_save_preferences = data.get("save_final_settings_as_main", False) 
    country_name_for_saving = data.get("current_afisha_country")

    if is_confirmed_done and not selected_event_types:
        await callback.answer(lexicon.get('afisha_alert_no_types_selected_v2'), show_alert=True)
        return 
    
    if not city_name:
        await callback.answer(lexicon.get('afisha_alert_no_city_selected_critical_v2'), show_alert=True)
        await state.clear()
        return

    header_text_after_setup = ""
    if should_save_preferences:
        if not country_name_for_saving:
            await callback.message.edit_text(lexicon.get('afisha_error_main_save_no_country_critical_v2'))
            await state.clear()
            await callback.answer()
            return
        
        header_text_after_setup = lexicon.get('afisha_header_main_settings_saved_v2').format(city_name=hbold(city_name))
        await db.update_user_preferences(
            user_id=callback.from_user.id,
            home_country=country_name_for_saving,
            home_city=city_name,
            event_types=selected_event_types,
            main_geo_completed=True 
        )
    else: 
        header_text_after_setup = lexicon.get('afisha_header_temp_choice_v2').format(city_name=hbold(city_name))

    try:
        await callback.message.edit_text(header_text_after_setup, parse_mode=ParseMode.HTML)
    except Exception: 
        await callback.message.answer(header_text_after_setup, parse_mode=ParseMode.HTML)

    await state.clear() 
    await callback.answer() 

    if selected_event_types: 
        for event_type_name in selected_event_types:
            await callback.message.answer(
                lexicon.get('afisha_loading_category_city_v2').format(category_name=event_type_name, city_name=hbold(city_name)),
                parse_mode=ParseMode.HTML
            )
            events = await db.get_grouped_events_by_city_and_category(city_name, event_type_name)
            response_text = await format_grouped_events_for_response(events)
            
            if not events:
                await callback.message.answer(lexicon.get('afisha_no_events_for_category_city_v2').format(city_name=hbold(city_name), category_name=event_type_name), parse_mode=ParseMode.HTML)
            else:
                await callback.message.answer(response_text, disable_web_page_preview=True, parse_mode=ParseMode.HTML)
    elif not is_confirmed_done: 
        await callback.message.answer(lexicon.get('afisha_no_types_info_v2'))


@router.message(F.text.in_(['🔎 Поиск', '🔎 Search', '🔎 Пошук'])) 
async def menu_search(message: Message, state: FSMContext): 
    await state.clear()
    await state.set_state(SearchGlobalFSM.waiting_for_query) # ИСПРАВЛЕНО состояние
    lexicon = Lexicon(message.from_user.language_code)
    await message.answer(lexicon.get('search_prompt_enter_query_v2'))


@router.message(SearchGlobalFSM.waiting_for_query, F.text) # ИСПРАВЛЕНО состояние
async def search_query_handler(message: Message, state: FSMContext): 
    # ... (код этого хендлера остается без изменений в части логики поиска и отображения) ...
    await state.clear()
    user_id = message.from_user.id
    lexicon = Lexicon(message.from_user.language_code)
    
    user_prefs = await db.get_user_preferences(user_id)
    search_regions = None
    if user_prefs and user_prefs.get("home_country") and user_prefs.get("home_city"):
        search_regions = [user_prefs["home_country"], user_prefs["home_city"]]

    await message.answer(
        lexicon.get('search_searching_for_query_v2').format(query_text=hbold(message.text)),
        parse_mode=ParseMode.HTML
    )

    found_events = await db.find_events_fuzzy(message.text, search_regions)
    response_text = await format_events_for_response(found_events) 
    
    if not found_events:
        await message.answer(lexicon.get('search_no_results_found_v2').format(query_text=hbold(message.text)))
    else:
        await message.answer(response_text, disable_web_page_preview=True, parse_mode=ParseMode.HTML)