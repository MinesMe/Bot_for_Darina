import asyncio
import logging
import re
from datetime import datetime

from sqlalchemy import func, select

# --- 1. ОБНОВЛЯЕМ ИМПОРТЫ ---
from app.database.models import async_session
from parsers.configs import ALL_CONFIGS

# Импортируем наш новый парсер и даем ему понятное имя
from parsers.test_parser import parse_site as parse_kvitki_playwright
# Импортируем AI функцию
from parsers.test_ai import getArtist
# Импортируем НОВЫЕ функции для работы с БД
from app.database.requests import (
    find_event_by_signature,
    update_event_details,
    create_event_with_artists
)
# Импортируем старые парсеры, если они нужны
from parsers.kvitki_parser import parse_site as parse_kvitki
from parsers.bezkassira_parser import parse as parse_bezkassira
from parsers.liveball_parser import parse as parse_liveball
from parsers.yandex_parser import parse as parse_yandex

from app.database.models import Artist  


# --- 1. НАСТРОЙКА ЛОГИРОВАНИЯ ---
# Настраиваем логирование, чтобы сообщения выводились и в консоль, и в файл.
# Это нужно сделать один раз в самом начале главного скрипта.

# Создаем основной логгер
logger = logging.getLogger()
logger.setLevel(logging.INFO) # Устанавливаем минимальный уровень для записи

# Создаем форматтер, который будет добавлять время и уровень сообщения
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Создаем обработчик для вывода в файл 'logs.txt'
# mode='a' означает 'append' (дозапись в конец файла)
# encoding='utf-8' для корректной работы с кириллицей
file_handler = logging.FileHandler('logs.txt', mode='a', encoding='utf-8')
file_handler.setFormatter(formatter)

# Создаем обработчик для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Добавляем оба обработчика к нашему логгеру
# Проверяем, чтобы не добавить обработчики повторно при перезапусках в IDE
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

async def populate_artists_if_needed(session):
    """
    Синхронизирует список артистов из artists.txt с базой данных.
    Добавляет только тех артистов, которых еще нет в БД, приводя имена к нижнему регистру.
    """
    logging.info("Синхронизация артистов из файла artists.txt с базой данных...")
    
    try:
        # 1. Читаем всех артистов из файла и приводим к нижнему регистру
        with open('artists.txt', 'r', encoding='utf-8') as f:
            artists_from_file = {line.strip().lower() for line in f if line.strip()}
        
        if not artists_from_file:
            logging.warning("Файл artists.txt пуст. Синхронизация не требуется.")
            return

        # 2. Получаем множество ВСЕХ артистов, которые уже есть в базе (тоже в нижнем регистре)
        # Это важно, если в базе вдруг оказались артисты в разном регистре.
        stmt = select(func.lower(Artist.name))
        existing_artists_result = await session.execute(stmt)
        existing_artists = set(existing_artists_result.scalars().all())

        # 3. Находим разницу - тех, кого нужно добавить
        artists_to_add = artists_from_file - existing_artists
        
        if not artists_to_add:
            logging.info("Все артисты из файла уже присутствуют в базе данных.")
            return

        # 4. Добавляем в сессию только новых артистов
        logging.info(f"Найдено {len(artists_to_add)} новых артистов в файле. Добавляю в сессию...")
        for artist_name in artists_to_add:
            # Имена уже в нижнем регистре
            session.add(Artist(name=artist_name))
        
        # Мы не делаем commit, он будет общий в конце.
        # Просто добавляем объекты в сессию.
        logging.info(f"Успешно добавлено в сессию {len(artists_to_add)} новых артистов.")

    except FileNotFoundError:
        logging.error("ОШИБКА: Файл artists.txt не найден. Не могу синхронизировать артистов.")
    except Exception as e:
        logging.error(f"Произошла ошибка при заполнении таблицы артистов: {e}", exc_info=True)
        # Важно пробросить исключение или обработать его, чтобы не продолжать с неполными данными
        raise   

# --- 2. ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПАРСИНГА ДАТЫ ---
def parse_datetime_from_str(date_str: str) -> datetime | None:
    """
    Парсит дату из строки, пробуя несколько известных форматов.
    """
    if not isinstance(date_str, str):
        return None

    # --- Попытка 1: Формат '24 июля 2024, 19:00' ---
    try:
        months_map = {'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04', 'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08', 'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'}
        processed_str = date_str.lower()
        for name, num in months_map.items():
            if name in processed_str:
                processed_str = processed_str.replace(name, num)
                cleaned_str = re.sub(r'[,.]| г', '', processed_str)
                cleaned_str = re.sub(r'\s+', ' ', cleaned_str).strip()
                # Если в дате есть время, используем этот формат
                if ':' in cleaned_str:
                    return datetime.strptime(cleaned_str, "%d %m %Y %H:%M")
                # Если времени нет, парсим только дату
                else:
                    return datetime.strptime(cleaned_str, "%d %m %Y")
    except ValueError:
        # Если формат не подошел, просто переходим к следующей попытке
        pass

    # --- Попытка 2: Формат 'Сб 28.06.2025' ---
    try:
        # Убираем день недели (первое слово)
        date_part = date_str.split(' ', 1)[-1]
        return datetime.strptime(date_part, "%d.%m.%Y")
    except (ValueError, IndexError):
        # Если и этот формат не подошел, логируем ошибку
        pass

    logging.warning(f"Не удалось распознать дату ни одним из известных форматов: '{date_str}'")
    return None

# --- 3. ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ИЗВЛЕЧЕНИЯ ГОРОДА ---
# Твоя функция, немного оптимизированная.
def extract_city_from_place(place_string: str) -> str:
    """
    Извлекает название города из строки, сначала проверяя известные города,
    а затем пытаясь извлечь последнее слово из очищенной строки.
    """
    if not place_string:
        return "Минск"

    # 1. Самый надежный способ: ищем точное вхождение известного города
    known_cities = ["Минск", "Брест", "Витебск", "Гомель", "Гродно", "Могилев", "Лида", "Молодечно", "Сморгонь", "Несвиж"]
    for city in known_cities:
        if city.lower() in place_string.lower():
            return city
    
    # 2. Если не нашли, пытаемся извлечь из очищенной строки
    # Удаляем скобки, запятые, точки и лишние пробелы
    cleaned_string = re.sub(r'[(),.]', ' ', place_string)
    parts = cleaned_string.strip().split()

    if len(parts) > 1 and parts[-1].isalpha():
        # Берем последнее слово, если оно состоит только из букв
        return parts[-1].capitalize()

    # 3. Город по умолчанию, если ничего не помогло
    return "Минск"

# --- 4. ОСНОВНАЯ ЛОГИКА ОРКЕСТРАТОРА (ПОЛНОСТЬЮ ПЕРЕПИСАНА) ---
async def process_all_sites():
    # Этап 1: Сбор "сырых" данных со всех сайтов
    all_raw_events = []
    parser_mapping = {
        'playwright_kvitki': parse_kvitki_playwright,
        # 'json': parse_kvitki, # Раскомментируй, если нужно
        # 'bs4_bezkassira': parse_bezkassira,
    }

    for site_config in ALL_CONFIGS:
        parsing_method = site_config.get('parsing_method')
        parser_func = parser_mapping.get(parsing_method)
        
        if not parser_func:
            print(f"Пропускаю конфиг с неизвестным методом: {parsing_method}")
            logging.warning(f"Пропускаю конфиг с неизвестным методом: {parsing_method}") # <--- ЗАМЕНА
            continue
            
        print(f"\n--- Запуск парсера '{parsing_method}' для категории '{site_config.get('event_type')}' ---")
        logging.info(f"\n--- Запуск парсера '{parsing_method}' для категории '{site_config.get('event_type')}' ---") # <--- ЗАМЕНА
        events_from_site = await parser_func(site_config)
        
        for event in events_from_site:
            event['event_type'] = site_config.get('event_type', 'Другое')
        all_raw_events.extend(events_from_site)

    if not all_raw_events:
        print("События не найдены ни на одном из сайтов. Завершаю работу.")
        logging.info("События не найдены ни на одном из сайтов. Завершаю работу.") # <--- ЗАМЕНА
        return

    # Этап 2: Обработка сырых данных и синхронизация с БД
    print(f"\n--- Всего собрано {len(all_raw_events)} сырых событий. Начинаю обработку и сверку с БД... ---")
    logging.info(f"\n--- Всего собрано {len(all_raw_events)} сырых событий. Начинаю обработку и сверку с БД... ---")
    
    events_created_count = 0
    events_updated_count = 0
    
    async with async_session() as session:
        await populate_artists_if_needed(session)
        for event_data in all_raw_events:
            title = event_data.get('title')
            if not title or "Ошибка обработки" in title:
                continue
            
            # 1. Подготовка ключевых данных для поиска и создания
            time_str = event_data.get('time')
            timestamp = parse_datetime_from_str(time_str)
            
            # 2. Поиск существующего события в БД по уникальной сигнатуре
            existing_event = await find_event_by_signature(session, title=title, date_start=timestamp)
            
            # 3. Принятие решения: обновить или создать
            if existing_event:
                # ---- СЦЕНАРИЙ ОБНОВЛЕНИЯ ----
                update_data = {
                    "price_min": event_data.get('price_min'),
                    "price_max": event_data.get('price_max'),
                    "tickets_info": event_data.get('tickets_info'),
                    "link": event_data.get('link')
                }
                await update_event_details(session, event_id=existing_event.event_id, event_data=update_data)
                events_updated_count += 1
                print(f"🔄 ОБНОВЛЕНО: {title} | {time_str}")
                logging.info(f"🔄 ОБНОВЛЕНО: {title} | {time_str}") # <--- ЗАМЕНА
                
            else:
                # ---- СЦЕНАРИЙ СОЗДАНИЯ ----
                print(f"  - Найдено новое событие: '{title}'.")
                logging.info(f"  - Найдено новое событие: '{title}'.")
                
                full_description = event_data.get('full_description')
                artist_names = []
                if full_description:
                    print(f"    - Вызываю AI для поиска артистов...")
                    logging.info(f"    - Вызываю AI для поиска артистов...")
                    artist_names = await getArtist(full_description)
                    print(f"    - AI нашел: {artist_names if artist_names else 'нет артистов'}")
                    logging.info(f"    - AI нашел: {artist_names if artist_names else 'нет артистов'}")
                
                # --- ИЗМЕНЕНИЕ: Достаем имя страны из конфига ---
                # Используем Беларусь по умолчанию, если в конфиге не указано
                country_name = site_config.get('country_name', 'Беларусь')

                # Собираем полный пакет данных для создания
                creation_data = {
                    "event_title": title,
                    "event_type": event_data['event_type'],
                    "venue": event_data.get('place', 'Место не указано'),
                    "city": extract_city_from_place(event_data.get('place')),
                    "country_name": country_name, # <--- И ДОБАВЛЯЕМ ЕГО СЮДА
                    "time": time_str,
                    "timestamp": timestamp,
                    "price_min": event_data.get('price_min'),
                    "price_max": event_data.get('price_max'),
                    "link": event_data.get('link'),
                    "tickets_info": event_data.get('tickets_info'),
                }
                
                new_event_obj = await create_event_with_artists(session, event_data=creation_data, artist_names=artist_names)
                if new_event_obj:
                    events_created_count += 1
                    print(f"✅ СОЗДАНО: {new_event_obj.title} | {time_str}")
                    logging.info(f"✅ СОЗДАНО: {new_event_obj.title} | {time_str}") # <--- ЗАМЕНА
        
        # 4. Сохраняем все изменения в БД одной большой транзакцией
        print("\nСохраняю все изменения в базе данных...")
        await session.commit()
        print("Изменения успешно сохранены.")

    print("\n--- Обработка завершена ---")
    print(f"Новых событий создано: {events_created_count}")
    print(f"Существующих событий обновлено: {events_updated_count}")

if __name__ == "__main__":
    asyncio.run(process_all_sites())