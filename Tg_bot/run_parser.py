import asyncio
import logging
import re
from datetime import datetime, timedelta

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
    Парсит дату из строки, пробуя несколько известных форматов,
    включая относительные даты ("сегодня", "завтра") и даты без года.
    """
    if not isinstance(date_str, str):
        return None

    cleaned_str = date_str.lower().strip()
    now = datetime.now()
    
    # --- Попытка 1: Относительные даты "сегодня" и "завтра" ---
    try:
        time_part = "00:00"
        time_match = re.search(r'(\d{1,2}:\d{2})', cleaned_str)
        if time_match:
            time_part = time_match.group(1)

        target_date = None
        if "сегодня" in cleaned_str:
            target_date = now.date()
        elif "завтра" in cleaned_str:
            target_date = (now + timedelta(days=1)).date()

        if target_date:
            return datetime.strptime(f"{target_date.strftime('%Y-%m-%d')} {time_part}", "%Y-%m-%d %H:%M")
    except (ValueError, IndexError):
        pass

    # --- Попытка 2: Формат '24 июля 2024, 19:00' (Kvitki) или '28 июня 2024' ---
    try:
        months_map = {'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04', 'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08', 'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'}
        processed_str = cleaned_str
        for name, num in months_map.items():
            if name in processed_str:
                processed_str = processed_str.replace(name, num)
                
                # Убираем дни недели и лишние символы
                processed_str = re.sub(r'^[а-я]{2},?\s*', '', processed_str) # "сб," -> ""
                processed_str = re.sub(r'[,.]| г', '', processed_str)
                processed_str = re.sub(r'\s+', ' ', processed_str).strip()

                # Сценарий А: Есть год ('28 06 2024 19:00')
                if re.search(r'\d{4}', processed_str):
                    if ':' in processed_str:
                        return datetime.strptime(processed_str, "%d %m %Y %H:%M")
                    else:
                        return datetime.strptime(processed_str, "%d %m %Y")
                
                # Сценарий Б: Нет года ('28 06 19:00')
                else:
                    format_str = "%d %m %H:%M" if ':' in processed_str else "%d %m"
                    # Парсим без года (по умолчанию будет 1900-й год)
                    temp_date = datetime.strptime(processed_str, format_str)
                    
                    # Заменяем год на текущий
                    final_date = temp_date.replace(year=now.year)
                    
                    # Если получившаяся дата уже прошла в этом году (например, сегодня июль, а событие в июне),
                    # значит, оно будет в следующем году.
                    if final_date < now:
                        final_date = final_date.replace(year=now.year + 1)
                    
                    return final_date

    except (ValueError, IndexError):
        pass

    # --- Попытка 3: Формат 'Сб 28.06.2025' (старый формат Яндекса) ---
    try:
        # Убираем день недели (первое слово и возможную запятую)
        date_part = re.sub(r'^[а-яА-Я]+,?\s*', '', cleaned_str)
        return datetime.strptime(date_part, "%d.%m.%Y")
    except (ValueError, IndexError):
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
        'selenium_yandex': parse_yandex,
    }

    for site_config in ALL_CONFIGS:
        parsing_method = site_config.get('parsing_method')
        parser_func = parser_mapping.get(parsing_method)
        
        if not parser_func:
            logging.warning(f"Пропускаю конфиг с неизвестным методом: {parsing_method}")
            continue
            
        logging.info(f"\n--- Запуск парсера '{parsing_method}' для категории '{site_config.get('site_name')}' ---")
        events_from_site = await parser_func(site_config)
        
        # ОБОГАЩАЕМ КАЖДОЕ СОБЫТИЕ ДАННЫМИ ИЗ КОНФИГА
        for event in events_from_site:
            event['event_type'] = site_config.get('event_type', 'Другое')
            event['config'] = site_config # <-- Просто передаем весь конфиг дальше!

        all_raw_events.extend(events_from_site)

    if not all_raw_events:
        logging.info("События не найдены ни на одном из сайтов. Завершаю работу.")
        return

    # Этап 2: Обработка сырых данных и синхронизация с БД
    logging.info(f"\n--- Всего собрано {len(all_raw_events)} сырых событий. Начинаю обработку и сверку с БД... ---")
    
    events_created_count = 0
    events_updated_count = 0
    
    async with async_session() as session:
        await populate_artists_if_needed(session)
        for event_data in all_raw_events:
            title = event_data.get('title')
            current_config = event_data.get('config') # <-- Извлекаем прикрепленный конфиг

            if not title or "Ошибка обработки" in title or not current_config:
                continue
            
            time_str = event_data.get('time')
            timestamp = parse_datetime_from_str(time_str)
            
            existing_event = await find_event_by_signature(session, title=title, date_start=timestamp)
            
            if existing_event:
                update_data = {
                    "price_min": event_data.get('price_min'),
                    "price_max": event_data.get('price_max'),
                    "tickets_info": event_data.get('tickets_info'),
                    "link": event_data.get('link')
                }
                await update_event_details(session, event_id=existing_event.event_id, event_data=update_data)
                events_updated_count += 1
                logging.info(f"🔄 ОБНОВЛЕНО: {title} | {time_str}")
                
            else:
                logging.info(f"  - Найдено новое событие: '{title}'.")
                
                full_description = event_data.get('full_description')
                artist_names = []
                if full_description:
                    logging.info(f"    - Вызываю AI для поиска артистов...")
                    artist_names = await getArtist(full_description)
                    logging.info(f"    - AI нашел: {artist_names if artist_names else 'нет артистов'}")
                
                # --- НОВАЯ ЛОГИКА ОПРЕДЕЛЕНИЯ ГОРОДА И СТРАНЫ ---
                place_str = event_data.get('place')
                
                # Способ 1: Получаем город и страну напрямую из конфига (приоритетный)
                city = current_config.get('city_name')
                country_name = current_config.get('country_name') # Он должен быть
                
                # Способ 2: Если в конфиге города нет, извлекаем его из строки
                if not city:
                    city = extract_city_from_place(place_str)

                creation_data = {
                    "event_title": title,
                    "event_type": event_data['event_type'],
                    "venue": place_str or 'Место не указано',
                    "city": city,
                    "country_name": country_name,
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
                    logging.info(f"✅ СОЗДАНО: {new_event_obj.title} | {time_str}")
        
        # 4. Сохраняем все изменения в БД одной большой транзакцией
        print("\nСохраняю все изменения в базе данных...")
        await session.commit()
        print("Изменения успешно сохранены.")

    print("\n--- Обработка завершена ---")
    print(f"Новых событий создано: {events_created_count}")
    print(f"Существующих событий обновлено: {events_updated_count}")

if __name__ == "__main__":
    asyncio.run(process_all_sites())