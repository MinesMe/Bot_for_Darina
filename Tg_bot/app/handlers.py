from datetime import datetime
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.markdown import hbold, hlink, hitalic, hcode, html_decoration

from .database import requests as db
from .database.models import async_session
from . import keyboards as kb

router = Router()


class UserSetup(StatesGroup):
    choosing_country = State()
    choosing_regions = State()


class SearchState(StatesGroup):
    waiting_for_query = State()


class SubscriptionFlow(StatesGroup):
    waiting_for_artist_name = State()


async def format_grouped_events_for_response(events: list) -> str:
    if not events:
        return "По вашему запросу ничего не найдено."

    response_parts = []
    for event in events:
        title_text = html_decoration.quote(event.title)

        if event.links and event.links[0]:
            url = html_decoration.quote(event.links[0])
            title_link = f'<b><a href="{url}">{title_text}</a></b>'
        else:
            title_link = hbold(title_text)

        place_info = event.venue_name if event.venue_name else "—"

        dates_str = []
        if event.dates:
            unique_dates = sorted(list(set(d for d in event.dates if d is not None)))
            for dt in unique_dates:
                dates_str.append(dt.strftime("%d.%m.%Y в %H:%M"))

        dates_info = "\n".join(f"▫️ {d}" for d in dates_str) if dates_str else "—"

        price_info = "—"
        if event.min_price and event.max_price and event.min_price != event.max_price:
            price_info = f"от {event.min_price} до {event.max_price} BYN"
        elif event.min_price:
            price_info = f"от {event.min_price} BYN"

        event_card = (
            f"{title_link}\n\n"
            f"📍 {hbold('Место:')} {hitalic(place_info)}\n"
            f"💰 {hbold('Цена:')} {hitalic(price_info)}\n\n"
            f"📅 {hbold('Доступные даты:')}\n{hitalic(dates_info)}"
        )
        response_parts.append(event_card)

    separator = "\n\n" + "—" * 15 + "\n\n"
    return separator.join(response_parts)


async def format_events_for_response(events: list) -> str:
    if not events:
        return "По вашему запросу ничего не найдено."

    response_parts = []
    for event in events:
        if event.links:
            url = html_decoration.quote(event.links[0].url)
            title = html_decoration.quote(event.title)
            title_link = f'<b><a href="{url}">{title}</a></b>'
        else:
            title_link = hbold(event.title)

        place_info = "—"
        if event.venue:
            place_info = f"{event.venue.name}, {event.venue.city}" if event.venue.city else event.venue.name

        date_start_info = event.date_start.strftime("%d.%m.%Y в %H:%M") if event.date_start else "—"

        price_info = "—"
        if event.price_min and event.price_max:
            price_info = f"от {event.price_min} до {event.price_max} BYN"
        elif event.price_min:
            price_info = f"от {event.price_min} BYN"

        when_info = event.description if event.description else "—"

        event_card = (
            f"{title_link}\n\n"
            f"📍 {hbold('Место:')} {hitalic(place_info)}\n"
            f"🕒 {hbold('Время:')} {hitalic(when_info)}\n"
            f"📅 {hbold('Начало:')} {hitalic(date_start_info)}\n"
            f"💰 {hbold('Цена:')} {hitalic(price_info)}"
        )
        response_parts.append(event_card)

    separator = "\n\n" + "—" * 15 + "\n\n"
    return separator.join(response_parts)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    async with async_session() as session:
        user = await db.get_or_create_user(session, message.from_user.id, message.from_user.username)
        user_regions = user.regions

    if not user_regions:
        await state.set_state(UserSetup.choosing_country)
        await message.answer(
            "👋 Привет! Похоже, ты здесь впервые.\n\n"
            "Давай настроим твоего бота. Сначала выбери страну.",
            reply_markup=kb.get_country_selection_keyboard()
        )
    else:
        await message.answer(
            f"С возвращением, {hbold(message.from_user.first_name)}!",
            reply_markup=kb.get_main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )


@router.callback_query(UserSetup.choosing_country, F.data.startswith("select_country:"))
async def cq_select_country(callback: CallbackQuery, state: FSMContext):
    await state.set_state(UserSetup.choosing_regions)
    await state.update_data(selected_regions=[])
    all_cities = await db.get_all_cities()
    await callback.message.edit_text(
        "Отлично! Теперь выбери регионы, события из которых ты хочешь отслеживать. Можно выбрать несколько.",
        reply_markup=kb.get_region_selection_keyboard(all_cities, [])
    )


@router.callback_query(UserSetup.choosing_regions, F.data.startswith("toggle_region:"))
async def cq_toggle_region(callback: CallbackQuery, state: FSMContext):
    region = callback.data.split(":")[1]
    data = await state.get_data()
    selected_regions = data.get("selected_regions", [])

    if region in selected_regions:
        selected_regions.remove(region)
    else:
        selected_regions.append(region)

    await state.update_data(selected_regions=selected_regions)
    all_cities = await db.get_all_cities()
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_region_selection_keyboard(all_cities, selected_regions)
    )
    await callback.answer()


@router.callback_query(UserSetup.choosing_regions, F.data == "finish_region_selection")
async def cq_finish_region_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_regions = data.get("selected_regions", [])
    if not selected_regions:
        await callback.answer("Нужно выбрать хотя бы один регион!", show_alert=True)
        return

    await db.update_user_regions(callback.from_user.id, selected_regions)
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        "Отлично, настройки сохранены! Теперь можешь пользоваться афишей.",
        reply_markup=kb.get_main_menu_keyboard()
    )


@router.message(F.text == "🗓 Афиша")
async def menu_afisha(message: Message):
    await message.answer("Выберите категорию:", reply_markup=kb.get_categories_keyboard())


@router.message(F.text == "⚙️ Настройки")
async def menu_settings(message: Message, state: FSMContext):
    await state.set_state(UserSetup.choosing_country)
    await message.answer(
        "Здесь ты можешь изменить свои настройки. Выбери страну:",
        reply_markup=kb.get_country_selection_keyboard()
    )


@router.message(F.text == "🔎 Поиск")
async def menu_search(message: Message, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await message.answer("Введите название события или артиста для поиска:", reply_markup=ReplyKeyboardRemove())


async def show_subscriptions(message: Message | CallbackQuery):
    user_id = message.from_user.id

    subscriptions = await db.get_user_subscriptions(user_id)
    text = "У тебя пока нет подписок. Добавь первую!" if not subscriptions else "Твои подписки:"

    if isinstance(message, CallbackQuery):
        # Если это колбэк, редактируем сообщение
        await message.message.edit_text(text, reply_markup=kb.manage_subscriptions_keyboard(subscriptions))
    else:
        # Если это обычное сообщение, отправляем новое
        await message.answer(text, reply_markup=kb.manage_subscriptions_keyboard(subscriptions))


@router.message(F.text == "⭐ Мои подписки")
async def menu_my_subscriptions(message: Message):
    await show_subscriptions(message)


@router.callback_query(F.data.startswith("unsubscribe:"))
async def cq_unsubscribe_item(callback: CallbackQuery):
    item_name = callback.data.split(":", 1)[1]
    await db.remove_subscription(callback.from_user.id, item_name)
    await callback.answer(f"❌ Ты отписался от {item_name}.")
    await show_subscriptions(callback)


@router.callback_query(F.data == "add_subscription")
async def cq_add_subscription(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.waiting_for_artist_name)
    await callback.message.edit_text("Введите имя артиста или название группы:")
    await callback.answer()


@router.message(SubscriptionFlow.waiting_for_artist_name)
async def process_artist_search(message: Message, state: FSMContext):
    found_artists = await db.find_artists_fuzzy(message.text)
    if not found_artists:
        await message.answer("По твоему запросу никого не найдено. Попробуй еще раз или нажми 'Отмена'.",
                             reply_markup=kb.found_artists_keyboard([]))
        return
    await message.answer("Вот кого я нашел. Выбери нужного артиста, чтобы подписаться, или нажми 'Отмена'.",
                         reply_markup=kb.found_artists_keyboard(found_artists))


@router.callback_query(F.data.startswith("subscribe_to_artist:"))
async def cq_subscribe_to_artist(callback: CallbackQuery, state: FSMContext):
    artist_name = callback.data.split(":", 1)[1]
    await db.add_subscription(callback.from_user.id, artist_name, 'music')
    await state.clear()
    await callback.answer(f"✅ Подписка на '{artist_name}' оформлена!")
    await show_subscriptions(callback)


@router.callback_query(F.data == "cancel_subscription")
async def cq_cancel_subscription(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_subscriptions(callback)


@router.callback_query(F.data.startswith("category:"))
async def cq_category(callback: CallbackQuery):
    category_name = callback.data.split(":")[1]
    user_regions = await db.get_user_regions(callback.from_user.id)
    if not user_regions:
        await callback.answer("Сначала выберите регионы в настройках!", show_alert=True)
        return
    cities = await db.get_cities_for_category(category_name, user_regions)
    if not cities:
        await callback.answer("В ваших регионах нет событий этой категории.", show_alert=True)
        return
    await callback.message.edit_text(
        f"Выбрана категория: {hbold(category_name)}. Теперь выберите город:",
        reply_markup=kb.get_cities_keyboard(cities, category_name),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("city:"))
async def cq_city(callback: CallbackQuery):
    _, city, category = callback.data.split(":")
    await callback.message.edit_text(f"Загружаю события для города {hbold(city)}...")
    events = await db.get_grouped_events_by_city_and_category(city, category)
    response_text = await format_grouped_events_for_response(events)
    await callback.message.answer(response_text, disable_web_page_preview=True, parse_mode=ParseMode.HTML)
    await callback.answer()


@router.message(SearchState.waiting_for_query)
async def search_query_handler(message: Message, state: FSMContext):
    await state.clear()
    user_regions = await db.get_user_regions(message.from_user.id)
    await message.answer(f"Ищу события по запросу: {hitalic(message.text)}...", parse_mode=ParseMode.HTML,
                         reply_markup=kb.get_main_menu_keyboard())
    found_events = await db.find_events_fuzzy(message.text, user_regions)
    response_text = await format_events_for_response(found_events)
    await message.answer(response_text, disable_web_page_preview=True, parse_mode=ParseMode.HTML)


COUNTRY_ID_GERMANY = 1 # Просто пример ID

event_data_for_test = {
    "event_type": "Концерт",      # Используется для event_type_obj
    "place": "Белорусь", # Используется для venue (и extract_city_from_place)
    "country": COUNTRY_ID_GERMANY, # Используется для venue (country_id)
    "event_title": "Коцнерт Imagine Dragons",    # Используется для artist (name)
    "timestamp": datetime(2026, 8, 30, 19, 1, 0).timestamp(), # Используется для date_start (timestamp), можно None
    "time": "Начало в 19:00",    # Используется для description нового Event
    "price_min": 50,              # Используется для price_min нового Event (опционально)
    "price_max": 250,             # Используется для price_max нового Event (опционально)
    "link": "https://example.com/tickets/imagine_dragons_berlin" # Используется для EventLink (url)
}


@router.message(F.text)
async def any_text_handler(message: Message):
    await db.add_unique_event(event_data_for_test)
    print("success")
    # await message.reply("Я не понимаю эту команду. Воспользуйтесь кнопками меню. Для поиска нажмите '🔎 Поиск'.")