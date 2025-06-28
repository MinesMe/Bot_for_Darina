# app/handlers/common.py

from collections import defaultdict
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, BotCommand
from aiogram.utils.markdown import hbold,hitalic

from ..database.requests import requests as db
from ..database.models import async_session
from app import keyboards as kb
from ..lexicon import Lexicon, LEXICON_COMMANDS_RU, LEXICON_COMMANDS_EN, EVENT_TYPE_EMOJI
from app.handlers.onboarding import start_onboarding_process

async def set_main_menu(bot: Bot, lang: str):
    commands = LEXICON_COMMANDS_RU if lang in ('ru', 'be') else LEXICON_COMMANDS_EN
    main_menu_commands = [BotCommand(command=cmd, description=desc) for cmd, desc in commands.items()]
    await bot.set_my_commands(main_menu_commands)

async def format_events_with_headers(events_by_category: dict) -> tuple[str, list[int]]:
    """
    Форматирует словарь {категория: [события]} в единый текст с заголовками
    и возвращает сквозной список ID.
    """
    if not events_by_category:
        return "По вашему запросу ничего не найдено.", []

    response_parts = []
    event_ids_in_order = []
    counter = 1  # Сквозной счетчик для нумерации

    for category_name, events in events_by_category.items():
        # Добавляем заголовок категории
        emoji = EVENT_TYPE_EMOJI.get(category_name, "🔹")
        response_parts.append(f"\n\n--- {emoji} {hbold(category_name)} ---\n")

        # Форматируем события внутри этой категории
        for event in events:
            event_ids_in_order.append(event.event_id)
            
            # Нумеруем с помощью сквозного счетчика
            title_text = hbold(f"{counter}. {event.title}")
            counter += 1

            # Остальная логика форматирования одной карточки события
            url = event.links[0] if hasattr(event, 'links') and event.links and event.links[0] else None
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

    # Собираем все части в один большой текст
    return "\n".join(response_parts), event_ids_in_order


async def format_events_for_response(events: list) -> str:
    if not events: return "По вашему запросу ничего не найдено."
    response_parts = []
    event_ids_in_order = []
    for event in events:
        event_ids_in_order.append(event.event_id)
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

async def format_events_by_artist(
    events: list, # Принимает список объектов Event
    lexicon: Lexicon
) -> tuple[str | None, list[int] | None]:
    """
    Форматирует список событий, группируя их по артистам.

    Args:
        events: Список объектов Event, полученных из БД.
        lexicon: Экземпляр Lexicon для локализации.

    Returns:
        Кортеж (отформатированный текст, упорядоченный список event_id).
        Если событий нет, возвращает (None, None).
    """
    if not events:
        return None, None

    # 1. Группируем события по имени артиста
    events_by_artist = defaultdict(list)
    for event in events:
        # У одного события может быть несколько артистов, проходимся по всем
        for event_artist in event.artists:
            events_by_artist[event_artist.artist.name].append(event)
    
    # Сортируем артистов по алфавиту для предсказуемого вывода
    sorted_artist_names = sorted(events_by_artist.keys())

    response_parts = []
    event_ids_in_order = []
    counter = 1  # Сквозной счетчик для нумерации

    # 2. Формируем текстовые блоки для каждого артиста
    for artist_name in sorted_artist_names:
        # Заголовок для группы событий артиста
        response_parts.append(f"\n\n——— 🎤 {hbold(artist_name.upper())} ———\n")

        # Получаем уникальные события для этого артиста, чтобы не было дублей
        unique_events_for_artist = sorted(
            list(set(events_by_artist[artist_name])), 
            key=lambda e: (e.date_start is None, e.date_start) # Сортируем по дате
        )

        for event in unique_events_for_artist:
            # Проверяем, не добавили ли мы уже это событие под эгидой другого артиста
            if event.event_id in event_ids_in_order:
                continue

            event_ids_in_order.append(event.event_id)
            
            # --- Форматируем карточку одного события (почти как в reminder) ---
            
            # Дата
            date_str = event.date_start.strftime('%d.%m.%Y %H:%M') if event.date_start else lexicon.get('date_not_specified')
            
            # Место
            place_info = "—"
            if event.venue:
                city_name = event.venue.city.name if event.venue.city else ""
                country_name = event.venue.city.country.name if event.venue.city and event.venue.city.country else ""
                place_info = f"{event.venue.name}, {city_name} ({country_name})"

            # Билеты
            tickets_str = event.tickets_info if event.tickets_info and event.tickets_info != "В наличии" else lexicon.get('no_info') # Добавьте 'no_info': 'Нет информации' в лексикон
            
            # Ссылка
            url = event.links[0].url if event.links else None
            title_text = f"{counter}. {event.title}"
            title_with_link = f'<a href="{url}">{hbold(title_text)}</a>' if url else hbold(title_text)
            
            # Собираем карточку
            event_card = (
                f"{title_with_link}\n"
                f"📅 {date_str}\n"
                f"📍 {hitalic(place_info)}\n"
                f"🎟️ Билеты: {hitalic(tickets_str)}"
            )
            response_parts.append(event_card)
            counter += 1

    if not response_parts:
        return None, None
        
    return "\n".join(response_parts), event_ids_in_order