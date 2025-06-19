# app/handlers/onboarding.py

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold

from ..database import requests as db
from .. import keyboards as kb
from ..lexicon import Lexicon

router = Router()


class Onboarding(StatesGroup):
    choosing_home_country = State()
    choosing_home_city = State()
    waiting_for_city_search = State()
    asking_for_filter_setup = State()
    choosing_event_types = State()


async def finish_onboarding(callback_or_message: Message | CallbackQuery, state: FSMContext):
    user_id = callback_or_message.from_user.id
    data = await state.get_data()
    lexicon = Lexicon(callback_or_message.from_user.language_code)

    await db.update_user_preferences(
        user_id=user_id,
        home_country=data.get("home_country"),
        home_city=data.get("home_city"),
        event_types=data.get("selected_event_types", [])
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


@router.callback_query(Onboarding.choosing_home_country, F.data == "skip_onboarding")
async def cq_skip_onboarding(callback: CallbackQuery, state: FSMContext):
    await state.update_data(home_country=None, home_city=None, selected_event_types=[])
    await finish_onboarding(callback, state)


@router.callback_query(Onboarding.choosing_home_country, F.data.startswith("select_home_country:"))
async def cq_select_home_country(callback: CallbackQuery, state: FSMContext):
    country_name = callback.data.split(":")[1]
    await state.update_data(home_country=country_name)
    await state.set_state(Onboarding.choosing_home_city)

    lexicon = Lexicon(callback.from_user.language_code)
    top_cities = await db.get_top_cities_for_country(country_name)

    await callback.message.edit_text(
        f"Отлично, твоя страна: {hbold(country_name)}. Теперь выбери свой город или пропусти этот шаг.",
        reply_markup=kb.get_home_city_selection_keyboard(top_cities, lexicon),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(Onboarding.choosing_home_city, F.data == "skip_city_selection")
async def cq_skip_city_selection(callback: CallbackQuery, state: FSMContext):
    await state.update_data(home_city=None)
    await state.set_state(Onboarding.asking_for_filter_setup)
    await callback.message.edit_text(
        "Понял. Хочешь настроить предпочитаемые типы событий (концерты, театр и т.д.)?",
        reply_markup=kb.get_setup_filter_preference_keyboard()
    )
    await callback.answer()


@router.callback_query(Onboarding.choosing_home_city, F.data.startswith("select_home_city:"))
async def cq_select_home_city(callback: CallbackQuery, state: FSMContext):
    city_name = callback.data.split(":")[1]
    await state.update_data(home_city=city_name)
    await state.set_state(Onboarding.asking_for_filter_setup)

    await callback.message.edit_text(
        f"Отлично, твой город: {hbold(city_name)}. "
        "Теперь последний вопрос: хочешь настроить предпочитаемые типы событий?",
        reply_markup=kb.get_setup_filter_preference_keyboard(),
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
    await callback.message.edit_text(
        f"Твоя страна: {hbold(country_name)}. Выбери свой город или пропусти.",
        reply_markup=kb.get_home_city_selection_keyboard(top_cities, lexicon),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(Onboarding.asking_for_filter_setup, F.data == "setup_filters_no")
async def cq_setup_filters_no(callback: CallbackQuery, state: FSMContext):
    await state.update_data(selected_event_types=[])
    await finish_onboarding(callback, state)


@router.callback_query(Onboarding.asking_for_filter_setup, F.data == "setup_filters_yes")
async def cq_setup_filters_yes(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Onboarding.choosing_event_types)
    await state.update_data(selected_event_types=[])
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.edit_text(
        "Выбери типы событий, которые тебе интересны. Это поможет мне давать лучшие рекомендации.",
        reply_markup=kb.get_event_type_selection_keyboard(lexicon)
    )
    await callback.answer()


@router.callback_query(Onboarding.choosing_event_types, F.data.startswith("toggle_event_type:"))
async def cq_toggle_event_type(callback: CallbackQuery, state: FSMContext):
    event_type = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_event_types", [])

    if event_type in selected:
        selected.remove(event_type)
    else:
        selected.append(event_type)

    await state.update_data(selected_event_types=selected)
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_event_type_selection_keyboard(lexicon, selected)
    )
    await callback.answer()


@router.callback_query(Onboarding.choosing_event_types, F.data == "finish_preferences_selection")
async def cq_finish_preferences_selection(callback: CallbackQuery, state: FSMContext):
    await finish_onboarding(callback, state)


@router.callback_query(F.data == 'ignore')
async def cq_ignore(callback: CallbackQuery):
    await callback.answer()