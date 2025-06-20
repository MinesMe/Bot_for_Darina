# app/handlers.py

from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, BotCommand
from aiogram.utils.markdown import hbold

from .database import requests as db
from .database.models import async_session
from . import keyboards as kb
from .lexicon import Lexicon, LEXICON_COMMANDS_RU, LEXICON_COMMANDS_EN
from .playlist_parser import parse_playlist_url

router = Router()


class Onboarding(StatesGroup):
    choosing_home_country = State()
    choosing_travel_countries = State()
    choosing_local_cities = State()
    waiting_for_city_search = State()


class SearchState(StatesGroup):
    waiting_for_query = State()


class SubscriptionFlow(StatesGroup):
    waiting_for_artist_name = State()
    waiting_for_playlist_url = State()
    selecting_from_playlist = State()



async def set_main_menu(bot: Bot, lang: str):
    commands = LEXICON_COMMANDS_RU if lang in ('ru', 'be') else LEXICON_COMMANDS_EN
    main_menu_commands = [BotCommand(command=cmd, description=desc) for cmd, desc in commands.items()]
    await bot.set_my_commands(main_menu_commands)


async def format_grouped_events_for_response(events: list) -> str:
    if not events: return "По вашему запросу ничего не найдено."
    response_parts = []
    for event in events:
        title_text = hbold(event.title)
        url = event.links[0] if event.links and event.links[0] else None
        title_link = f'<a href="{url}">{title_text}</a>' if url else title_text
        place_info = event.venue_name or "—"
        dates_str = sorted(list(set(d.strftime("%d.%m.%Y в %H:%M") for d in event.dates if d)))
        dates_info = "\n".join(f"▫️ {d}" for d in dates_str) if dates_str else "—"
        price_info = "—"
        if event.min_price and event.max_price and event.min_price != event.max_price:
            price_info = f"от {event.min_price} до {event.max_price} BYN"
        elif event.min_price:
            price_info = f"от {event.min_price} BYN"
        event_card = (f"{title_link}\n\n"
                      f"📍 <b>Место:</b> <i>{place_info}</i>\n"
                      f"💰 <b>Цена:</b> <i>{price_info}</i>\n\n"
                      f"📅 <b>Доступные даты:</b>\n<i>{dates_info}</i>")
        response_parts.append(event_card)
    separator = "\n\n" + "—" * 15 + "\n\n"
    return separator.join(response_parts)


async def format_events_for_response(events: list) -> str:
    if not events: return "По вашему запросу ничего не найдено."
    response_parts = []
    for event in events:
        url = event.links[0].url if event.links else None
        title = hbold(event.title)
        title_link = f'<a href="{url}">{title}</a>' if url else title
        place_info = f"{event.venue.name}, {event.venue.city.name}" if event.venue and event.venue.city else (
            event.venue.name if event.venue else "—")
        date_start_info = event.date_start.strftime("%d.%m.%Y в %H:%M") if event.date_start else "—"
        price_info = "—"
        if event.price_min and event.price_max:
            price_info = f"от {event.price_min} до {event.price_max} BYN"
        elif event.price_min:
            price_info = f"от {event.price_min} BYN"
        when_info = event.description or "—"
        event_card = (f"{title_link}\n\n"
                      f"📍 <b>Место:</b> <i>{place_info}</i>\n"
                      f"🕒 <b>Время:</b> <i>{when_info}</i>\n"
                      f"📅 <b>Начало:</b> <i>{date_start_info}</i>\n"
                      f"💰 <b>Цена:</b> <i>{price_info}</i>")
        response_parts.append(event_card)
    separator = "\n\n" + "—" * 15 + "\n\n"
    return separator.join(response_parts)


async def show_city_selection_screen(message: Message, state: FSMContext, lexicon: Lexicon):
    data = await state.get_data()
    country_name = data.get("selected_countries")[0]
    top_cities = await db.get_top_cities_for_country(country_name)
    msg = await message.edit_text(
        lexicon.get('choose_local_cities'),
        reply_markup=kb.get_city_selection_keyboard(top_cities, lexicon, data.get("selected_cities", []))
    )
    await state.update_data(city_selection_message_id=msg.message_id)


async def start_onboarding_process(message: Message | CallbackQuery, state: FSMContext, lexicon: Lexicon):
    await state.clear()
    await state.set_state(Onboarding.choosing_home_country)
    # --- ИЗМЕНЕНИЕ 1: Получаем ограниченный список стран для первого экрана ---
    all_countries = await db.get_countries(home_country_selection=True)

    text = lexicon.get('settings_intro')
    if isinstance(message, Message):
        text = lexicon.get('welcome').format(first_name=hbold(message.from_user.first_name))
    action = message.answer if isinstance(message, Message) else message.message.edit_text
    await action(text, reply_markup=kb.get_country_selection_keyboard(all_countries, lexicon),
                 parse_mode=ParseMode.HTML)
    if isinstance(message, CallbackQuery):
        await message.answer()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    user_lang = message.from_user.language_code
    lexicon = Lexicon(user_lang)
    await set_main_menu(bot, user_lang)
    async with async_session() as session:
        user = await db.get_or_create_user(session, message.from_user.id, message.from_user.username, user_lang)
    if user.regions:
        await message.answer(
            lexicon.get('main_menu_greeting').format(first_name=hbold(message.from_user.first_name)),
            reply_markup=kb.get_main_menu_keyboard(lexicon), parse_mode=ParseMode.HTML
        )
        return
    await start_onboarding_process(message, state, lexicon)


@router.callback_query(Onboarding.choosing_home_country, F.data.startswith("select_country:"))
async def cq_select_home_country(callback: CallbackQuery, state: FSMContext):
    home_country = callback.data.split(":")[1]
    lexicon = Lexicon(callback.from_user.language_code)
    await state.update_data(home_country=home_country, selected_countries=[home_country])
    await state.set_state(Onboarding.choosing_travel_countries)

    # --- ИЗМЕНЕНИЕ 2: Получаем ПОЛНЫЙ список стран для второго экрана ---
    all_countries = await db.get_countries()

    await callback.message.edit_text(
        lexicon.get('choose_travel_countries').format(home_country=hbold(home_country)),
        reply_markup=kb.get_country_selection_keyboard(
            all_countries, lexicon, is_multiselect=True,
            home_country=home_country, selected_countries=[home_country]
        ),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(Onboarding.choosing_travel_countries, F.data.startswith("toggle_country:"))
async def cq_toggle_travel_country(callback: CallbackQuery, state: FSMContext):
    country_to_toggle = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_countries", [])
    if country_to_toggle in selected:
        if len(selected) > 1:
            selected.remove(country_to_toggle)
    else:
        selected.append(country_to_toggle)
    await state.update_data(selected_countries=selected)

    # --- ИЗМЕНЕНИЕ 3: Получаем ПОЛНЫЙ список стран для обновления клавиатуры ---
    all_countries = await db.get_countries()

    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_country_selection_keyboard(
            all_countries, lexicon, is_multiselect=True,
            home_country=data.get('home_country'), selected_countries=selected
        )
    )
    await callback.answer()


@router.callback_query(Onboarding.choosing_travel_countries, F.data == "finish_country_selection")
async def cq_finish_country_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_countries = data.get("selected_countries", [])
    lexicon = Lexicon(callback.from_user.language_code)
    if not selected_countries:
        await callback.answer(lexicon.get('no_countries_selected_alert'), show_alert=True)
        return
    if len(selected_countries) > 1:
        await db.update_user_regions(callback.from_user.id, selected_countries)
        await state.clear()
        await callback.message.delete()
        await callback.message.answer(
            lexicon.get('setup_complete'),
            reply_markup=kb.get_main_menu_keyboard(lexicon)
        )
    else:
        await state.set_state(Onboarding.choosing_local_cities)
        await state.update_data(selected_cities=[])
        await show_city_selection_screen(callback.message, state, lexicon)


@router.callback_query(F.data == 'ignore')
async def cq_ignore(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(Onboarding.choosing_local_cities, F.data.startswith("toggle_city:"))
async def cq_toggle_local_city(callback: CallbackQuery, state: FSMContext):
    city_to_toggle = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_cities", [])
    if city_to_toggle in selected:
        selected.remove(city_to_toggle)
    else:
        selected.append(city_to_toggle)
    await state.update_data(selected_cities=selected)
    lexicon = Lexicon(callback.from_user.language_code)
    await show_city_selection_screen(callback.message, state, lexicon)
    await callback.answer()


@router.callback_query(Onboarding.choosing_local_cities, F.data == "search_for_city")
async def cq_search_for_city(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Onboarding.waiting_for_city_search)
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.edit_text(lexicon.get('search_city_prompt'))
    await callback.answer()


@router.message(Onboarding.waiting_for_city_search, F.text)
async def process_city_search(message: Message, state: FSMContext):
    data = await state.get_data()
    country_name = data.get("selected_countries")[0]
    lexicon = Lexicon(message.from_user.language_code)
    best_matches = await db.find_cities_fuzzy(country_name, message.text)
    await state.set_state(Onboarding.choosing_local_cities)
    await message.delete()
    city_selection_message_id = data.get('city_selection_message_id')
    if not best_matches:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=city_selection_message_id,
            text=lexicon.get('city_not_found'),
            reply_markup=kb.get_back_to_city_selection_keyboard(lexicon)
        )
    else:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=city_selection_message_id,
            text=lexicon.get('city_found_prompt'),
            reply_markup=kb.get_found_cities_keyboard(best_matches, lexicon)
        )


@router.callback_query(Onboarding.choosing_local_cities, F.data == "back_to_city_selection")
async def cq_back_to_city_selection(callback: CallbackQuery, state: FSMContext):
    lexicon = Lexicon(callback.from_user.language_code)
    await show_city_selection_screen(callback.message, state, lexicon)
    await callback.answer()


@router.callback_query(Onboarding.choosing_local_cities, F.data == "finish_city_selection")
async def cq_finish_city_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_cities = data.get("selected_cities", [])
    lexicon = Lexicon(callback.from_user.language_code)
    if not selected_cities:
        await callback.answer(lexicon.get('no_regions_selected_alert'), show_alert=True)
        return
    await db.update_user_regions(callback.from_user.id, selected_cities)
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(
        lexicon.get('setup_complete'),
        reply_markup=kb.get_main_menu_keyboard(lexicon)
    )


@router.message(Command('settings'))
@router.message(F.text.in_(['👤 Профиль', '👤 Profile', '👤 Профіль']))
async def menu_profile(message: Message, state: FSMContext):
    await state.clear()
    lexicon = Lexicon(message.from_user.language_code)
    await message.answer(
        lexicon.get('profile_menu_header'),
        reply_markup=kb.get_profile_keyboard(lexicon)
    )


@router.callback_query(F.data == "change_location")
async def cq_change_location(callback: CallbackQuery, state: FSMContext):
    lexicon = Lexicon(callback.from_user.language_code)
    await start_onboarding_process(callback, state, lexicon)


@router.callback_query(F.data == "open_subscriptions")
async def cq_open_subscriptions(callback: CallbackQuery):
    await callback.answer()
    await show_subscriptions(callback.message)


@router.message(F.text.in_(['🗓 Афиша', '🗓 Events']))
async def menu_afisha(message: Message):
    await message.answer("Выберите категорию:", reply_markup=kb.get_categories_keyboard())


@router.message(F.text.in_(['🔎 Поиск', '🔎 Search']))
async def menu_search(message: Message, state: FSMContext):
    await state.set_state(SearchState.waiting_for_query)
    await message.answer("Введите название события или артиста для поиска:")


async def show_subscriptions(message: Message | CallbackQuery, force_new_message: bool = False):
    user_id = message.from_user.id
    subscriptions = await db.get_user_subscriptions(user_id)
    if not subscriptions:
        text = "У тебя пока нет подписок.\n\nТы можешь добавить артистов вручную или импортировать их из своего плейлиста."
    else:
        text = "Твои подписки:\nНажми на подписку, чтобы удалить ее."
    markup = kb.manage_subscriptions_keyboard(subscriptions)
    if isinstance(message, CallbackQuery) and not force_new_message:
        try:
            await message.message.edit_text(text, reply_markup=markup)
        except Exception:
            await message.answer()
    else:
        chat_id = message.chat.id if isinstance(message, Message) else message.message.chat.id
        await message.bot.send_message(chat_id, text, reply_markup=markup)


@router.message(F.text.in_(['⭐ Мои подписки', '⭐ My Subscriptions', '⭐ Мае падпіскі']))
async def menu_my_subscriptions(message: Message):
    await show_subscriptions(message)


@router.callback_query(F.data.startswith("unsubscribe:"))
async def cq_unsubscribe_item(callback: CallbackQuery):
    item_name = callback.data.split(":", 1)[1]
    await db.remove_subscription(callback.from_user.id, item_name)
    await callback.answer(f"❌ Ты отписался от {item_name}.")
    await show_subscriptions(callback)


@router.callback_query(F.data == "add_subscription")
async def cq_add_subscription_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.waiting_for_artist_name)
    await callback.message.edit_text("Введите имя артиста или название группы, чтобы добавить подписку вручную:")
    await callback.answer()


@router.callback_query(F.data == "import_playlist")
async def cq_import_playlist(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.waiting_for_playlist_url)
    await callback.message.edit_text(
        "Отлично! Отправь мне ссылку на публичный плейлист из одного из сервисов:\n\n"
        "• YouTube Music\n"
        "• Spotify\n"
        "• Яндекс.Музыка\n"
        "• VK Музыка (Boom)\n\n"
        "Я постараюсь извлечь оттуда всех исполнителей."
    )
    await callback.answer()


@router.message(SubscriptionFlow.waiting_for_playlist_url, F.text)
async def process_playlist_url(message: Message, state: FSMContext):
    if not message.text.startswith('http'):
        await message.reply("Это не похоже на ссылку. Пожалуйста, попробуй еще раз или вернись в меню подписок.")
        await show_subscriptions(message)
        return

    msg = await message.reply("Принял ссылку. Начинаю обработку, это может занять некоторое время...")

    master_artists = await db.get_all_master_artists()
    found_artists_lower = await parse_playlist_url(message.text, master_artists=master_artists)

    if found_artists_lower is None:
        await msg.edit_text(
            "Не удалось распознать сервис или плейлист по этой ссылке. Убедись, что плейлист публичный и ссылка верна.")
        await state.clear()
        return

    if not found_artists_lower:
        await msg.edit_text(
            "Не смог найти артистов из твоего списка в этом плейлисте. Возможно, он пуст или нет совпадений.")
        await state.clear()
        return

    correctly_cased_artists = await db.get_artists_by_lowercase_names(found_artists_lower)

    if "music.youtube.com" in message.text.lower():
        await state.set_state(SubscriptionFlow.selecting_from_playlist)
        sorted_artists = sorted(list(set(correctly_cased_artists)))
        await state.update_data(found_artists=sorted_artists, selected_artists=set())
        await msg.edit_text(
            "Я нашел этих артистов в плейлисте. Выбери, на кого хочешь подписаться:",
            reply_markup=kb.get_paginated_artists_keyboard(sorted_artists, set())
        )
    else:
        await state.clear()
        added_count = 0
        for artist_name in set(correctly_cased_artists):
            await db.add_subscription(message.from_user.id, artist_name, 'music')
        added_count += 1
        await msg.delete()
        await message.answer(f"✅ Готово! Успешно добавлено {added_count} новых подписок из плейлиста.")
        await show_subscriptions(message, force_new_message=True)


@router.callback_query(SubscriptionFlow.selecting_from_playlist, F.data.startswith("paginate_artists:"))
async def cq_paginate_artists(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    found = data.get("found_artists", [])
    selected = data.get("selected_artists", set())

    await callback.message.edit_reply_markup(
        reply_markup=kb.get_paginated_artists_keyboard(found, selected, page)
    )
    await callback.answer()


@router.callback_query(SubscriptionFlow.selecting_from_playlist, F.data.startswith("toggle_artist_subscribe:"))
async def cq_toggle_artist_subscribe(callback: CallbackQuery, state: FSMContext):
    artist_name = callback.data.split(":", 1)[1]
    data = await state.get_data()
    found = data.get("found_artists", [])
    selected = data.get("selected_artists", set())

    if artist_name in selected:
        selected.remove(artist_name)
    else:
        selected.add(artist_name)

    await state.update_data(selected_artists=selected)

    current_page = 0
    if found:
        try:
            current_page = found.index(artist_name) // 5
        except ValueError:
            pass

    await callback.message.edit_reply_markup(
        reply_markup=kb.get_paginated_artists_keyboard(found, selected, current_page)
    )
    await callback.answer()


@router.callback_query(SubscriptionFlow.selecting_from_playlist, F.data == "finish_artist_selection")
async def cq_finish_artist_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_artists = data.get("selected_artists", set())

    if not selected_artists:
        await callback.answer("Ты никого не выбрал.", show_alert=True)
        return

    for artist in selected_artists:
        await db.add_subscription(callback.from_user.id, artist, 'music')

    await state.clear()
    await callback.message.delete()
    await callback.message.answer(f"✅ Готово! Успешно добавлено {len(selected_artists)} новых подписок.")
    await show_subscriptions(callback, force_new_message=True)


@router.message(SubscriptionFlow.waiting_for_artist_name, F.text)
async def process_artist_search(message: Message, state: FSMContext):
    found_artists = await db.find_artists_fuzzy(message.text)
    if not found_artists:
        await message.answer("По твоему запросу никого не найдено. Попробуй еще раз или нажми 'Отмена'.",
                             reply_markup=kb.found_artists_keyboard([]))
    else:
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


@router.message(F.text.startswith('/'))
async def any_unregistered_command_handler(message: Message):
    await message.reply("Я не знаю такой команды. Воспользуйтесь кнопками меню.")

