# app/handlers/afisha.py

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold
from aiogram.filters.state import StateFilter

from ..database import requests as db
from .. import keyboards as kb
from ..lexicon import Lexicon
from .common import format_grouped_events_for_response, format_events_for_response
from app.handlers.onboarding import city_search, toggle_event_type, search_for_city

router = Router()

class Afisha(StatesGroup):
    main_geo_setting = State()
    waiting_for_city_search = State()
    choosing_home_city = State()

class SearchState(StatesGroup):
    waiting_for_query = State()
    


@router.message(F.text.in_(['🗓 Афиша', '🗓 Events']))
async def menu_afisha(message: Message, state: FSMContext):
    is_main_geo = await db.check_main_geo_status(message.from_user.id)
    if is_main_geo == False:
        await state.update_data(is_settings_complete=False)
        await message.answer("Вы пропустили настройки, вы можете настроить их сейчас или пропустить. Но для афиши надо будет выбрать тип ивента и город",
                             reply_markup=kb.get_afisha_settings())
    else:
        await state.update_data(is_settings_complete=True)
        await message.answer("Хотите посмотреть афиши по вашим настройкам или хотите единоразово выбрать другие",
                             reply_markup=kb.get_afisha_settings_type())
        
        # Получаем предпочтения пользователя
        # user_prefs = await db.get_user_preferences(message.from_user.id)

        # # Проверяем, есть ли у пользователя сохраненные и непустые типы событий
        # if user_prefs and user_prefs.get("preferred_event_types"):
        #     preferred_types = user_prefs["preferred_event_types"]
        #     text = "Вот ваши предпочитаемые категории:"
        #     # Создаем клавиатуру только с его любимыми категориями
        #     markup = kb.get_categories_keyboard(categories=preferred_types)
        # else:
        #     # Если предпочтений нет, показываем стандартный набор
        #     text = "Выберите категорию из полного списка:"
        #     markup = kb.get_categories_keyboard()

        # await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith("afisha_main_geo_settings") | F.data.startswith("skip_afisha_main_geo") | F.data.startswith("afisha_another_type_settings"))
async def main_geo_setting_country(callback: CallbackQuery, state:FSMContext):
    await state.set_state(Afisha.main_geo_setting)
    cq_data = callback.data
    if cq_data == "skip_afisha_main_geo":
        await state.update_data(is_settings_skipped=True)
    else:
        await state.update_data(is_settings_skipped=False)
    user_data = await db.get_user_preferences(callback.from_user.id)
    user_country = user_data['home_country']
    await state.update_data(home_country=user_country)
    lexicon = Lexicon(callback.from_user.language_code)
    top_cities = await db.get_top_cities_for_country(user_country)

    # Действие: редактируем сообщение, из которого пришел CallbackQuery
    await callback.message.edit_text(
        "Выберете город",
        reply_markup=kb.get_home_city_selection_keyboard(top_cities, lexicon),
        parse_mode=ParseMode.HTML
    )

    # Всегда отвечаем на CallbackQuery, чтобы убрать значок загрузки
    await callback.answer()

@router.callback_query(Afisha.main_geo_setting, F.data == "search_for_home_city")
async def cq_search_for_city(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Afisha.waiting_for_city_search)
    await search_for_city(callback, state, "Afisha")

@router.message(Afisha.waiting_for_city_search, F.text)
async def process_city_search(message: Message, state: FSMContext):
    user_data = await db.get_user_preferences(message.from_user.id)
    user_country = user_data['home_country']
    await state.set_state(Afisha.choosing_home_city)

    await city_search(message, state, "Afisha", user_country)

@router.callback_query(Afisha.choosing_home_city, F.data == "back_to_city_selection")
async def main_geo_setting_country(callback: CallbackQuery, state:FSMContext):
    await state.set_state(Afisha.choosing_home_city)
    user_data = await db.get_user_preferences(callback.from_user.id)
    user_country = user_data['home_country']
    lexicon = Lexicon(callback.from_user.language_code)
    top_cities = await db.get_top_cities_for_country(user_country)

    # Действие: редактируем сообщение, из которого пришел CallbackQuery
    await callback.message.edit_text(
        "Выберете город",
        reply_markup=kb.get_home_city_selection_keyboard(top_cities, lexicon),
        parse_mode=ParseMode.HTML
    )

    # Всегда отвечаем на CallbackQuery, чтобы убрать значок загрузки
    await callback.answer()

@router.callback_query(StateFilter(Afisha.main_geo_setting, Afisha.choosing_home_city), F.data.startswith("select_home_city:"))
async def select_home_city(callback: CallbackQuery, state: FSMContext):
    city_name = callback.data.split(":")[1]
    await state.update_data(home_city=city_name)
    lexicon = Lexicon(callback.from_user.language_code)
    await state.set_state(Afisha.main_geo_setting)
    await state.update_data(selected_event_types=[])
    await callback.message.edit_text(
        f"Отлично, твой город: {hbold(city_name)}. "
        "Выбери типы событий, которые тебе интересны. Это поможет мне давать лучшие рекомендации.",
        reply_markup=kb.get_event_type_selection_keyboard(lexicon),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(Afisha.main_geo_setting, F.data.startswith("toggle_event_type:"))
async def cq_set_event_type(callback: CallbackQuery, state: FSMContext):
    await toggle_event_type(callback, state)


@router.callback_query(F.data.startswith("afisha_defautl_type_settings"))
async def cq_set_event_type(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Афиша:")
    await callback.answer()

@router.callback_query(Afisha.main_geo_setting, F.data.startswith("finish_preferences_selection:"))
async def cq_finish_preferences_selection(callback: CallbackQuery, state: FSMContext):
    is_setting_complete = callback.data.split(":")[1]
    data = await state.get_data()
    print(data)
    event_types=data.get("selected_event_types", [])
    if is_setting_complete != "False" and (event_types == []):
        await callback.message.answer("Выберите хотя бы один ивент")
        await callback.answer()
    else:
        if data["is_settings_complete"] == True or data["is_settings_skipped"] == True: 
            await callback.message.edit_text(f"Афиша по вашим единоразовым настройкам:")
        elif data["is_settings_skipped"] == False:
            await callback.message.edit_text(f"Спасибо что настроили основныей настройки! Вот Афиша по вашим настройкам:")
            await db.update_user_preferences(
                user_id=callback.from_user.id,
                home_country=data.get("home_country"),
                home_city=data.get("home_city"),
                event_types=data.get("selected_event_types", []),
                main_geo_completed=is_setting_complete != "False"
            )

        await callback.answer()
@router.message(F.text.in_(['🔎 Поиск', '🔎 Search']))
async def menu_search(message: Message, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await message.answer("Введите название события или артиста для поиска (поиск не зависит от фильтров):")


@router.callback_query(F.data.startswith("category:"))
async def cq_category(callback: CallbackQuery):
    category_name = callback.data.split(":")[1]

    # --- ИЗМЕНЕНИЕ ЛОГИКИ: Используем домашний город, если он есть ---
    user_prefs = await db.get_user_preferences(callback.from_user.id)

    # Если у пользователя задан домашний город, сразу показываем события для него
    if user_prefs and user_prefs.get("home_city"):
        city_name = user_prefs["home_city"]
        await callback.message.edit_text(
            f"Загружаю события для вашего города {hbold(city_name)}...",
            parse_mode=ParseMode.HTML
        )
        events = await db.get_grouped_events_by_city_and_category(city_name, category_name)
        response_text = await format_grouped_events_for_response(events)
        await callback.message.answer(response_text, disable_web_page_preview=True, parse_mode=ParseMode.HTML)
        await callback.answer()
        return

    # Если домашний город не задан, работаем по старой схеме: просим выбрать город
    # Для этого нам нужны регионы мобильности (старое поле 'regions')
    user_regions = await db.get_user_regions(callback.from_user.id)
    if not user_regions:
        # Если не задан ни домашний город, ни регионы мобильности, просим настроить профиль
        await callback.answer("Сначала выберите свой город или регионы в настройках!", show_alert=True)
        return

    cities = await db.get_cities_for_category(category_name, user_regions)
    if not cities:
        await callback.answer("В ваших регионах нет событий этой категории.", show_alert=True)
        return

    await callback.message.edit_text(
        f"Выбрана категория: {hbold(category_name)}. Теперь выберите город:",
        reply_markup=kb.get_cities_keyboard(cities, category_name), parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("city:"))
async def cq_city(callback: CallbackQuery):
    _, city, category = callback.data.split(":")
    await callback.message.edit_text(
        f"Загружаю события для города {hbold(city)}...",
        parse_mode=ParseMode.HTML
    )
    events = await db.get_grouped_events_by_city_and_category(city, category)
    response_text = await format_grouped_events_for_response(events)
    await callback.message.answer(response_text, disable_web_page_preview=True, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.message(SearchState.waiting_for_query, F.text)
async def search_query_handler(message: Message, state: FSMContext):
    await state.clear()
    # Для поиска используем регионы мобильности, а не домашний город, т.к. поиск - это разведка
    user_regions = await db.get_user_regions(message.from_user.id)
    lexicon = Lexicon(message.from_user.language_code)

    await message.answer(
        f"Ищу события по запросу: {hbold(message.text)}...",
        parse_mode=ParseMode.HTML,
        reply_markup=kb.get_main_menu_keyboard(lexicon)
    )

    found_events = await db.find_events_fuzzy(message.text, user_regions)
    response_text = await format_events_for_response(found_events)
    await message.answer(response_text, disable_web_page_preview=True, parse_mode=ParseMode.HTML)