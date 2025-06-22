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
        await populate_artists_if_needed(session)

        all_events_with_types = []
        for site_config in ALL_CONFIGS:
            event_type_name = site_config.get('event_type', 'Другое')
            events_from_site = []
            parsing_method = site_config.get('parsing_method')

            if parsing_method == 'json':
                events_from_site = parse_kvitki(site_config)
            elif parsing_method == 'bs4_bezkassira':
                events_from_site = parse_bezkassira(site_config)
            elif parsing_method == 'bs4_liveball':
                events_from_site = parse_liveball(site_config)
            elif parsing_method == 'selenium_yandex':
                events_from_site = parse_yandex(site_config)
            else:
                print(
                    f"ПРЕДУПРЕЖДЕНИЕ: Неизвестный метод парсинга '{parsing_method}' для сайта '{site_config['site_name']}'. Пропускаю.")
                continue

            for event in events_from_site:
                event['event_type'] = event_type_name
            all_events_with_types.extend(events_from_site)

        if not all_events_with_types:
            print("События не найдены ни на одном из сайтов. Завершаю работу.")
            return

        print(f"Всего найдено {len(all_events_with_types)} событий. Начинаю обработку и сохранение в базу данных...")

        # Получаем или создаем страны. Теперь нужно и для России.
        country_belarus = await rq.get_or_create(session, Country, name="Беларусь")
        country_russia = await rq.get_or_create(session, Country, name="Россия")

        for event_data in all_events_with_types:
            city = extract_city_from_place(event_data['place'])
            print(city)
            country_id_to_use = country_russia.country_id if city == "Москва" else country_belarus.country_id

            start_datetime = None
            if event_data.get('timestamp'):
                try:
                    start_datetime = datetime.fromtimestamp(event_data['timestamp'])
                except (ValueError, TypeError):
                    start_datetime = None
            event_data_for_test = { 
                "event_type": event_data['event_type'],      # Используется для event_type_obj
                'venue': event_data['place'],
                "city": city, # Используется для venue (и extract_city_from_place)
                "country": country_id_to_use, # Используется для venue (country_id)
                "event_title": event_data['title'],    # Используется для artist (name)
                "timestamp": start_datetime, # Используется для date_start (timestamp), можно None
                "time": event_data['time'],    # Используется для description нового Event
                "price_min": event_data.get('price_min'),              # Используется для price_min нового Event (опционально)
                "price_max": event_data.get('price_max'),             # Используется для price_max нового Event (опционально)
                "link": event_data['link'] # Используется для EventLink (url)
            }


            await rq.add_unique_event(event_data_for_test)
            

        await session.commit()
    print("Обработка завершена. Новые данные успешно сохранены в базу.")


if __name__ == "__main__":
    asyncio.run(process_all_sites())