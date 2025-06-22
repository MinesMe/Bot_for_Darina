# --- START OF FILE parsers/bezkassira_parser.py ---

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import locale
import time

# Устанавливаем русскую локаль для корректного парсинга названий месяцев
try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Russian_Russia.1251')
    except locale.Error:
        print("ПРЕДУПРЕЖДЕНИЕ: Не удалось установить русскую локаль. Даты могут не парситься.")


def parse_date(date_str: str) -> datetime | None:
    """Преобразует строку типа '19 июня 2025' в объект datetime."""
    try:
        clean_date_str = " ".join(date_str.lower().split())
        return datetime.strptime(clean_date_str, "%d %B %Y")
    except (ValueError, TypeError):
        return None


def parse(config: dict) -> list[dict]:
    site_name = config['site_name']
    url = config['url']
    final_events = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }

    print(f"Начинаю парсинг BS4: {site_name}")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  - Ошибка при запросе к сайту {site_name}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'lxml')
    selectors = config['selectors']

    # Теперь мы ищем родительскую карточку
    event_cards = soup.select(selectors['event_card'])

    if not event_cards:
        print(f"  - Не найдено карточек событий для {site_name} по селектору '{selectors['event_card']}'.")
        return []

    print(f"  - Найдено {len(event_cards)} событий для {site_name}. Начинаю обработку...")

    for i, card in enumerate(event_cards):
        # Ищем элементы внутри родительской карточки
        caption_div = card.select_one(selectors['caption'])
        if not caption_div:
            continue

        title_element = caption_div.select_one(selectors['title'])
        link_element = caption_div.select_one(selectors['link'])
        date_element = card.select_one(selectors['date'])
        place_element = card.select_one(selectors['place'])

        if not all([title_element, link_element, date_element, place_element]):
            # print(f"  - Пропускаю карточку {i+1}, не все данные найдены.")
            continue

        title = title_element.get_text(strip=True)
        link = link_element['href']

        if not link.startswith('http'):
            link = "https://bezkassira.by" + link

        date_str = date_element.get_text(strip=True)
        place_str = place_element.get_text(separator=" ", strip=True)

        dt_object = parse_date(date_str)
        timestamp = int(dt_object.timestamp()) if dt_object else None

        # Цены не парсим с главной, оставляем None
        event_info = {
            'title': title,
            'place': place_str,
            'time': "Время уточняйте на сайте",
            'link': link,
            'timestamp': timestamp,
            'price_min': None,
            'price_max': None
        }
        final_events.append(event_info)
        # print(f"    - Обработка {i + 1}/{len(event_cards)}: {title}")
        time.sleep(0.1)  # Небольшая задержка

    print(f"Сайт {site_name} спарсен. Найдено событий: {len(final_events)}")
    return final_events