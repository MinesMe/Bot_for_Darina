import asyncio
import re
import json
from datetime import datetime
from sqlalchemy import select, delete, inspect, func

# from Bot_for_Darina.Tg_bot.app.database.requests import extract_city_from_place, get_or_create
from app.database.models import async_session, engine, Country, Venue, EventType, Artist, Event, EventLink, EventArtist
from parsers.configs import ALL_CONFIGS
from parsers.main_parser import parse_site

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


async def clear_event_data(session):
    print("Очистка старых данных о событиях...")
    await session.execute(delete(EventArtist))
    await session.execute(delete(EventLink))
    await session.execute(delete(Event))
    await session.execute(delete(Venue))
    await session.execute(delete(EventType))
    # Таблицу Artist теперь не очищаем!
    await session.commit()
    print("Старые данные о событиях удалены.")







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
            events_from_site = parse_site(site_config)
            for event in events_from_site:
                event['event_type'] = event_type_name
            all_events_with_types.extend(events_from_site)

        if not all_events_with_types:
            print("События не найдены ни на одном из сайтов. Завершаю работу.")
            return

        print(f"Всего найдено {len(all_events_with_types)} событий. Начинаю обработку и сохранение в базу данных...")

        country_belarus = await rq.get_or_create(session, Country, name="Беларусь")

        for event_data in all_events_with_types:
            start_datetime = None
            if event_data.get('timestamp'):
                try:
                    start_datetime = datetime.fromtimestamp(event_data['timestamp'])
                except (ValueError, TypeError):
                    start_datetime = None
            event_data_for_test = {
                "event_type": event_data['event_type'],      # Используется для event_type_obj
                "place": event_data['place'], # Используется для venue (и extract_city_from_place)
                "country": country_belarus.country_id, # Используется для venue (country_id)
                "event_title": event_data['title'],    # Используется для artist (name)
                "timestamp": start_datetime, # Используется для date_start (timestamp), можно None
                "time": event_data['time'],    # Используется для description нового Event
                "price_min": event_data.get('price_min'),              # Используется для price_min нового Event (опционально)
                "price_max": event_data.get('price_max'),             # Используется для price_max нового Event (опционально)
                "link": event_data['link'] # Используется для EventLink (url)
            }
            
            await rq.add_unique_event(event_data_for_test)
            


    print("Обработка завершена. Новые данные успешно сохранены в базу.")


if __name__ == "__main__":
    asyncio.run(process_all_sites())