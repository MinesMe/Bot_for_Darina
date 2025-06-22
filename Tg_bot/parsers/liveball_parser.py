# --- START OF FILE parsers/liveball_parser.py ---

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import locale
import time

try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'Russian_Russia.1251')
    except locale.Error:
        print("ПРЕДУПРЕЖДЕНИЕ: Не удалось установить русскую локаль.")


def combine_date_and_time_str(date_obj: datetime, time_str: str) -> datetime | None:
    """Объединяет объект даты со строкой времени."""
    try:
        clean_time_str = time_str.split('<')[0].strip()
        time_parts = datetime.strptime(clean_time_str, "%H:%M").time()
        return date_obj.replace(hour=time_parts.hour, minute=time_parts.minute, second=0, microsecond=0)
    except (ValueError, TypeError):
        return None


def parse(config: dict) -> list[dict]:
    site_name = config['site_name']
    base_url = "https://liveball.my"
    final_events = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    }
    selectors = config['selectors']

    print(f"Начинаю парсинг BS4: {site_name}")

    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    dates_to_parse = [today, tomorrow]

    for date_obj in dates_to_parse:
        date_str_url = date_obj.strftime("%Y-%m-%d")
        list_url = f"{config['url']}{date_str_url}"

        try:
            response = requests.get(list_url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
        except requests.RequestException:
            continue

        match_links = soup.select(selectors['list_item'])

        upcoming_matches_urls = []
        for link_tag in match_links:
            if link_tag.select_one(selectors['list_score_indicator']):
                continue
            upcoming_matches_urls.append(base_url + link_tag['href'])

        for detail_url in upcoming_matches_urls:
            try:
                detail_response = requests.get(detail_url, headers=headers, timeout=10)
                detail_response.raise_for_status()
                detail_soup = BeautifulSoup(detail_response.text, 'lxml')

                main_info_block = detail_soup.select_one(selectors['detail_main_info_block'])
                if not main_info_block:
                    continue

                league_tour_element = main_info_block.select_one(selectors['detail_league_tour'])
                left_team_element = main_info_block.select_one(selectors['detail_left_team'])
                right_team_element = main_info_block.select_one(selectors['detail_right_team'])

                if not (left_team_element and right_team_element):
                    continue

                league_tour = league_tour_element.get_text(strip=True) if league_tour_element else "Турнир"
                left_team = left_team_element.get_text(strip=True)
                right_team = right_team_element.get_text(strip=True)
                title = f"{league_tour}: {left_team} - {right_team}"

                time_str_for_user = "Время уточняйте"
                dt_object = None
                timestamp = None

                info_vs_block = main_info_block.select_one(selectors['detail_vs_block'])
                if info_vs_block:
                    time_element = info_vs_block.select_one(selectors['detail_time'])
                    if time_element:
                        time_str = time_element.get_text(strip=True)
                        time_str_for_user = time_str.split('<')[0].strip()
                        dt_object = combine_date_and_time_str(date_obj, time_str)
                        if dt_object:
                            timestamp = int(dt_object.timestamp())

                if not dt_object:
                    # Если время не найдено, ставим полночь дня, за который парсим
                    dt_object = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
                    timestamp = int(dt_object.timestamp())

                event_info = {
                    'title': title,
                    'place': "Место не указано",  # <- значение по умолчанию
                    'time': time_str_for_user,  # <- чистое время или "Время уточняйте"
                    'link': detail_url,
                    'timestamp': timestamp,
                    'price_min': None,
                    'price_max': None
                }
                final_events.append(event_info)
                time.sleep(0.1)

            except Exception:
                continue

    print(f"Сайт {site_name} спарсен. Найдено событий: {len(final_events)}")
    return final_events