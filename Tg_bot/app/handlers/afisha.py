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

router = Router()


class SearchState(StatesGroup):
    waiting_for_query = State()


@router.message(F.text.in_(['🗓 Афиша', '🗓 Events']))
async def menu_afisha(message: Message):
    # Получаем предпочтения пользователя
    user_prefs = await db.get_user_preferences(message.from_user.id)

    # Проверяем, есть ли у пользователя сохраненные и непустые типы событий
    if user_prefs and user_prefs.get("preferred_event_types"):
        preferred_types = user_prefs["preferred_event_types"]
        text = "Вот ваши предпочитаемые категории:"
        # Создаем клавиатуру только с его любимыми категориями
        markup = kb.get_categories_keyboard(categories=preferred_types)
    else:
        # Если предпочтений нет, показываем стандартный набор
        text = "Выберите категорию из полного списка:"
        markup = kb.get_categories_keyboard()

    await message.answer(text, reply_markup=markup)


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