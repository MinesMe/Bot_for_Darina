import asyncio
import re
from datetime import datetime
from sqlalchemy import select, delete, inspect, func
from sqlalchemy.orm import selectinload

from app.database.models import async_session, engine, Country, City, Venue, EventType, Artist, Event, EventLink, \
    EventArtist
from parsers.configs import ALL_CONFIGS
from parsers.main_parser import parse_site


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
    await session.commit()
    print("Старые данные о событиях удалены.")


async def get_or_create(session, model, **kwargs):
    instance = await session.execute(select(model).filter_by(**kwargs))
    instance = instance.scalar_one_or_none()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        await session.flush()
        return instance


def extract_city_from_place(place_string: str) -> str | None:
    if not place_string:
        return None
    # Пробуем найти город по запятой
    parts = place_string.split(',')
    if len(parts) > 1:
        city_candidate = parts[-1].strip()
        # Простая проверка, что это не номер дома или что-то подобное
        if not any(char.isdigit() for char in city_candidate) and len(city_candidate) > 2:
            return city_candidate

    # Если по запятой не нашли, ищем по ключевым словам в строке
    # Этот список можно расширить городами, которые часто встречаются в афишах
    known_cities_pattern = r'\b(Минск|Брест|Витебск|Гомель|Гродно|Могилев|Лида|Москва|Питер|СПб)\b'
    match = re.search(known_cities_pattern, place_string, re.IGNORECASE)
    if match:
        city = match.group(1)
        if city.lower() in ['питер', 'спб']:
            return 'Санкт-Петербург'
        return city

    return None


async def process_all_sites():
    tables_exist = await check_tables_exist()
    if not tables_exist:
        print("\nОШИБКА: Таблицы в базе данных не найдены.")
        print("Пожалуйста, сначала запустите main.py, чтобы создать структуру базы, а затем остановите его (Ctrl+C).")
        return

    async with async_session() as session:
        await populate_artists_if_needed(session)
        await clear_event_data(session)

        print("Кэширование стран и городов из базы данных...")
        cities_res = await session.execute(select(City).options(selectinload(City.country)))
        cities_cache = {city.name.lower(): (city.city_id, city.country.country_id) for city in cities_res.scalars()}
        print("Кэширование завершено.")

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

        for event_data in all_events_with_types:
            event_type_obj = await get_or_create(session, EventType, name=event_data['event_type'])

            parsed_city_name = extract_city_from_place(event_data['place'])

            if not parsed_city_name:
                print(
                    f"  - ПРЕДУПРЕЖДЕНИЕ: Не удалось определить город для '{event_data['place']}'. Пропускаю событие '{event_data['title']}'.")
                continue

            city_info = cities_cache.get(parsed_city_name.lower())

            if not city_info:
                print(
                    f"  - ПРЕДУПРЕЖДЕНИЕ: Город '{parsed_city_name}' не найден в базе. Пропускаю событие '{event_data['title']}'.")
                continue

            city_id, country_id = city_info

            venue = await get_or_create(session, Venue, name=event_data['place'], city_id=city_id,
                                        country_id=country_id)

            artist = await get_or_create(session, Artist, name=event_data['title'])

            start_datetime = None
            if event_data.get('timestamp'):
                try:
                    start_datetime = datetime.fromtimestamp(event_data['timestamp'])
                except (ValueError, TypeError):
                    start_datetime = None

            new_event = Event(
                title=event_data['title'],
                description=event_data['time'],
                type_id=event_type_obj.type_id,
                venue_id=venue.venue_id,
                date_start=start_datetime,
                price_min=event_data.get('price_min'),
                price_max=event_data.get('price_max')
            )

            event_artist_link = EventArtist(event=new_event, artist=artist)
            event_url_link = EventLink(event=new_event, url=event_data['link'], type="bilety")

            session.add_all([new_event, event_artist_link, event_url_link])

        await session.commit()
    print("Обработка завершена. Новые данные успешно сохранены в базу.")


if __name__ == "__main__":
    asyncio.run(process_all_sites())