import asyncio
import re
from datetime import datetime
from sqlalchemy import select, delete, inspect, func

from app.database.models import async_session, engine, Country, Venue, EventType, Artist, Event, EventLink, EventArtist
from parsers.configs import ALL_CONFIGS

# Импортируем все наши парсеры
from parsers.kvitki_parser import parse_site as parse_kvitki
from parsers.bezkassira_parser import parse as parse_bezkassira
from parsers.liveball_parser import parse as parse_liveball
from parsers.yandex_parser import parse as parse_yandex

import app.database.requests as rq


async def check_tables_exist():
    async with engine.connect() as conn:
        def has_table_sync(sync_conn):
            inspector = inspect(sync_conn)
            return inspector.has_table("events")

        return await conn.run_sync(has_table_sync)


async def populate_artists_if_needed(session):
    print("Проверка таблицы артистов...")
    count_result = await session.execute(select(func.count(Artist.artist_id)))
    if count_result.scalar_one() > 0:
        print("Таблица артистов уже заполнена. Пропускаю.")
        return
    print("Таблица артистов пуста. Начинаю заполнение из файла artists.txt...")
    try:
        with open('artists.txt', 'r', encoding='utf-8') as f:
            artists_to_add = [line.strip() for line in f if line.strip()]
        if not artists_to_add:
            print("Файл artists.txt пуст. Заполнение не требуется.")
            return
        print(f"Найдено {len(artists_to_add)} артистов в файле. Добавляю в базу...")
        for i, artist_name in enumerate(artists_to_add):
            session.add(Artist(name=artist_name))
            if (i + 1) % 1000 == 0:
                print(f"  Подготовлено к добавлению {i + 1} артистов...")
        await session.commit()
        print(f"Заполнение таблицы артистов завершено. Всего добавлено: {len(artists_to_add)}.")
    except FileNotFoundError:
        print("ОШИБКА: Файл artists.txt не найден. Не могу заполнить таблицу.")
    except Exception as e:
        print(f"Произошла ошибка при заполнении таблицы артистов: {e}")



def extract_city_from_place(place_string: str) -> str:
    if not place_string:
        return "Минск"  # По умолчанию для других сайтов

    # Для Яндекс.Афиши город всегда Москва, так как мы парсим moscow
    if 'afisha.yandex.ru/moscow' in place_string:  # Проверка, что это событие с Яндекса
        return "Москва"

    # Логика для других сайтов (kvitki, bezkassira, liveball)
    parts = place_string.split(',')
    if len(parts) > 1:
        city = parts[-1].strip()
        if not any(char.isdigit() for char in city):
            return city
    parts_space = place_string.split()
    if len(parts_space) > 1 and parts_space[-1].isalpha():
        city_candidate = parts_space[-1]
        known_cities_lower = ["минск", "брест", "витебск", "гомель", "гродно", "могилев"]
        if city_candidate.lower() in known_cities_lower:
            return city_candidate.capitalize()
    known_cities = ["Минск", "Брест", "Витебск", "Гомель", "Гродно", "Могилев", "Лида", "Молодечно", "Сморгонь",
                    "Несвиж"]
    for city in known_cities:
        if city.lower() in place_string.lower():
            return city
    return "Минск"

async def process_all_sites():
    tables_exist = await check_tables_exist()
    if not tables_exist:
        print("\nОШИБКА: Таблицы в базе данных не найдены.")
        print("Пожалуйста, сначала запустите main.py, чтобы создать структуру базы, а затем остановите его (Ctrl+C).")
        return
    async with async_session() as session:
        # Вызываем функцию заполнения артистов в начале
        await populate_artists_if_needed(session)

    all_events_with_types = []
    for site_config in ALL_CONFIGS:
        # ... (логика вызова парсеров)
        event_type_name = site_config.get('event_type', 'Другое')
        events_from_site = []
        parsing_method = site_config.get('parsing_method')

        if parsing_method == 'json': events_from_site = parse_kvitki(site_config)
        elif parsing_method == 'bs4_bezkassira': events_from_site = parse_bezkassira(site_config)
        elif parsing_method == 'bs4_liveball': events_from_site = parse_liveball(site_config)
        elif parsing_method == 'selenium_yandex': events_from_site = parse_yandex(site_config)
        else: continue

        for event in events_from_site:
            event['event_type'] = event_type_name
        all_events_with_types.extend(events_from_site)

    if not all_events_with_types:
        print("События не найдены ни на одном из сайтов. Завершаю работу.")
        return

    print(f"Всего найдено {len(all_events_with_types)} событий. Начинаю обработку...")

    events_created_count = 0
    events_updated_count = 0

    for event_data in all_events_with_types:
        if 'title' not in event_data:
            print(f"ПРЕДУПРЕЖДЕНИЕ: Пропускаю событие без заголовка.")
            continue

        place = event_data.get('place', 'Место не указано')
        link = event_data.get('link')
        time_info = event_data.get('time', 'Время не указано')
        city = extract_city_from_place(place)
        
        start_datetime = None
        if event_data.get('timestamp'):
            try:
                start_datetime = datetime.fromtimestamp(event_data['timestamp'])
            except (ValueError, TypeError):
                start_datetime = None

        prepared_data = {
            "event_type": event_data['event_type'],
            "venue": place,
            "city": city,
            "event_title": event_data['title'],
            "timestamp": start_datetime,
            "time": time_info,
            "price_min": event_data.get('price_min'),
            "price_max": event_data.get('price_max'),
            "link": link,
            "tickets_info": event_data.get('tickets_info', "В наличии")
        }

        event_obj, is_new = await rq.get_or_create_or_update_event(prepared_data)

        if event_obj:
            if is_new:
                events_created_count += 1
                print(f"✅ СОЗДАНО новое событие: {event_obj.title}")
            else:
                events_updated_count += 1
                print(f"🔄 ОБНОВЛЕНО существующее событие: {event_obj.title}")
    
    print("\n--- Обработка завершена ---")
    print(f"Новых событий создано: {events_created_count}")
    print(f"Существующих событий обновлено: {events_updated_count}")


if __name__ == "__main__":
    asyncio.run(process_all_sites())