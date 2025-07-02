import asyncio
import logging
import re
import random
import time
from datetime import datetime, timedelta
from calendar import monthrange
import requests

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# --- Инициализация и константы ---
logger = logging.getLogger()
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]

# --- Самая продвинутая функция парсинга дат ---
def parse_datetime_range(date_str: str) -> tuple[datetime | None, datetime | None]:
    """
    Извлекает НАЧАЛЬНУЮ и КОНЕЧНУЮ дату, находя все упоминания дат в строке
    и выбирая из них минимальную и максимальную.
    """
    if not isinstance(date_str, str) or not date_str.strip():
        return None, None

    cleaned_str = date_str.lower().strip()
    now = datetime.now()
    
    months_map = {
        'январь': 1, 'января': 1, 'февраль': 2, 'февраля': 2, 'март': 3, 'марта': 3,
        'апрель': 4, 'апреля': 4, 'май': 5, 'мая': 5, 'июнь': 6, 'июня': 6,
        'июль': 7, 'июля': 7, 'август': 8, 'августа': 8, 'сентябрь': 9, 'сентября': 9,
        'октябрь': 10, 'октября': 10, 'ноябрь': 11, 'ноября': 11, 'декабрь': 12, 'декабря': 12,
    }
    
    def _construct_date(day, month_num, year=None, time_str="00:00"):
        if year is None: year = now.year
        hour, minute = map(int, time_str.split(':'))
        try:
            temp_date_this_year = datetime(now.year, month_num, day)
            if temp_date_this_year < now.replace(hour=0, minute=0, second=0, microsecond=0):
                year = now.year + 1
            return datetime(year, month_num, day, hour, minute)
        except ValueError: return None

    if "постоянно" in cleaned_str: return None, None
    
    time_match = re.search(r'(\d{1,2}:\d{2})', cleaned_str)
    time_part = time_match.group(1) if time_match else "00:00"
    if time_match: cleaned_str = cleaned_str.replace(time_match.group(0), '').strip()

    all_found_dates = []
    # Находим все полные пары "число месяц"
    full_matches = list(re.finditer(r'(\d{1,2})\s+([а-я]+)', cleaned_str))
    
    # Сохраняем последний найденный месяц для обработки "одиноких" чисел
    last_month_num = None
    for m in full_matches:
        day, month_name = int(m.group(1)), m.group(2)
        if month_name in months_map:
            month_num = months_map[month_name]
            date_obj = _construct_date(day, month_num, time_str=time_part)
            if date_obj:
                all_found_dates.append(date_obj)
            last_month_num = month_num

    # Теперь ищем "одинокие" числа (например, '2' в '12 июля, 2')
    # Для этого удалим уже обработанные полные даты из строки
    temp_str = cleaned_str
    for m in full_matches:
        temp_str = temp_str.replace(m.group(0), '')
        
    if last_month_num:
        lonely_days = re.findall(r'(\d+)', temp_str)
        for day_str in lonely_days:
            date_obj = _construct_date(int(day_str), last_month_num, time_str=time_part)
            if date_obj:
                all_found_dates.append(date_obj)

    if all_found_dates:
        start_date = min(all_found_dates)
        end_date = max(all_found_dates)
        if start_date != end_date:
            end_date = end_date.replace(hour=23, minute=59)
        return start_date, end_date

    # Если не нашли пар "число-месяц", ищем только месяцы
    found_months_nums = [num for name, num in months_map.items() if name in cleaned_str]
    unique_months = sorted(list(set(found_months_nums)))
    if unique_months:
        start_month_num, end_month_num = min(unique_months), max(unique_months)
        start_date = _construct_date(1, start_month_num)
        if not start_date: return None, None
        end_year = start_date.year + (1 if end_month_num < start_month_num else 0)
        _, last_day_of_month = monthrange(end_year, end_month_num)
        end_date = datetime(end_year, end_month_num, last_day_of_month, 23, 59)
        return start_date, end_date

    logger.warning(f"Не удалось распознать дату из строки: '{date_str}'")
    return None, None

# --- Функция решения капчи ---
def _solve_yandex_captcha(driver: webdriver.Chrome, api_key: str, max_attempts: int = 2) -> bool:
    for attempt in range(max_attempts):
        logger.info(f"🤖 Обнаружена Yandex Smart Captcha. Попытка решения #{attempt + 1}/{max_attempts}...")
        # ... (полный код решателя капчи) ...
    return False # Placeholder

# --- Основная функция парсинга ---
def _parse_sync(config: dict) -> list[dict]:
    site_name = config['site_name']
    today_str = datetime.now().strftime("%Y-%m-%d")
    base_url = f"{config['url']}?date={today_str}&period={config['period']}"
    rucaptcha_api_key = config.get('RUCAPTCHA_API_KEY')
    max_pages_to_parse = config.get('max_pages', 10)

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    # ... другие опции ...

    all_events_data = []
    seen_event_links = set()
    logger.info(f"Начинаю парсинг: {site_name}")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        for page_num in range(1, max_pages_to_parse + 1):
            current_url = f"{base_url}&page={page_num}"
            logger.info(f"Обрабатываю страницу {page_num}/{max_pages_to_parse}: {current_url}")
            driver.get(current_url)
            
            # ... (блок проверки и решения капчи) ...

            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test-id="eventCard.root"]')))
            except TimeoutException:
                logger.info(f"На странице {page_num} нет событий. Завершаю.")
                break

            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            event_cards = soup.find_all("div", attrs={"data-test-id": "eventCard.root"})
            if not event_cards: break

            current_page_links = {
                link.get('href') for card in event_cards 
                if (link := card.find("a", attrs={"data-test-id": "eventCard.link"}))
            }
            if not current_page_links.difference(seen_event_links):
                logger.info("Новых событий на этой странице не найдено. Завершаю парсинг.")
                break

            for card in event_cards:
                try:
                    link_element = card.find("a", attrs={"data-test-id": "eventCard.link"})
                    href = link_element.get('href') if link_element else None
                    if not href or href in seen_event_links: continue
                    seen_event_links.add(href)
                    
                    title = card.find("h2", attrs={"data-test-id": "eventCard.eventInfoTitle"}).get_text(strip=True)
                    link = "https://afisha.yandex.ru" + href
                    
                    details_list = card.find("ul", attrs={"data-test-id": "eventCard.eventInfoDetails"})
                    place, date_str = "Место не указано", "Дата не указана"
                    if details_list:
                        details_items = details_list.find_all("li")
                        if len(details_items) > 0: date_str = details_items[0].get_text(strip=True)
                        if len(details_items) > 1:
                            place_link = details_items[1].find('a')
                            place = place_link.get_text(strip=True) if place_link else details_items[1].get_text(strip=True)
                    
                    price_min = None
                    price_element = card.find("span", string=re.compile(r'от \d+'))
                    if price_element:
                        price_match = re.search(r'\d+', price_element.get_text(strip=True).replace(' ', ''))
                        if price_match: price_min = float(price_match.group(0))
                    
                    time_start, time_end = parse_datetime_range(date_str)
                    
                    event_data = {
                        'title': title, 'place': place, 'time_string': date_str, 'link': link,
                        'price_min': price_min, 'time_start': time_start, 'time_end': time_end,
                        'price_max': None, 'tickets_info': None, 'full_description': None,
                    }
                    all_events_data.append(event_data)
                except Exception as e:
                    logger.warning(f"Ошибка парсинга карточки: {e}")
            time.sleep(random.uniform(2.0, 4.0))
    except Exception as e:
         logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()
            logger.info("Драйвер успешно закрыт.")
    logger.info(f"Сайт {site_name} спарсен. Найдено уникальных событий: {len(all_events_data)}")
    return all_events_data

# --- Асинхронная обертка ---
async def parse(config: dict) -> list[dict]:
    logger.info(f"Запускаю парсер Yandex для '{config['site_name']}' в фоновом потоке...")
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _parse_sync, config)

# --- Блок для автономного запуска ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    TEST_CONFIG = {
        'site_name': 'Yandex.Afisha (Спорт) - ТЕСТОВЫЙ ЗАПУСК',
        'url': 'https://afisha.yandex.ru/moscow/sport',
        'period': 365, 'max_pages': 10,
        'RUCAPTCHA_API_KEY': '863b567c1d376398b65ad121498f89a1' # 🔴 ВАЖНО: Используйте свой ключ
    }
    async def run_test():
        print("\n--- ЗАПУСК ПАРСЕРА С ПОЛНОЙ ОБРАБОТКОЙ ДАННЫХ ---")
        if not TEST_CONFIG.get('RUCAPTCHA_API_KEY'):
            print("🔴 ВНИМАНИЕ: Не указан API ключ для RuCaptcha.")
        results = await parse(TEST_CONFIG)
        if results:
            print(f"\n✅  Парсинг завершен. Найдено событий: {len(results)}\n")
            for i, event in enumerate(results, 1):
                start_str = event['time_start'].strftime('%Y-%m-%d %H:%M') if event['time_start'] else 'N/A'
                end_str = event['time_end'].strftime('%Y-%m-%d %H:%M') if event['time_end'] else 'N/A'
                print(f"--- Событие #{i} ---")
                print(f"  Название:         {event.get('title', 'N/A')}")
                print(f"  Место:            {event.get('place', 'N/A')}")
                print(f"  Исходная строка:  {event.get('time_string', 'N/A')}")
                print(f"  НАЧАЛО (time_start): {start_str}")
                print(f"  КОНЕЦ (time_end):   {end_str}")
                print(f"  Цена от:          {event.get('price_min', 'N/A')}")
                print(f"  Ссылка:           {event.get('link', 'N/A')}")
        else:
            print("\n❌ События не найдены или произошла ошибка.")
    asyncio.run(run_test())