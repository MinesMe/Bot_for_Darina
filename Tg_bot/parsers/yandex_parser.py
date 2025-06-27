# --- START OF FILE parsers/yandex_parser.py ---

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime


def parse(config: dict) -> list[dict]:
    site_name = config['site_name']

    # --- Формируем URL из конфига ---
    today_str = datetime.now().strftime("%Y-%m-%d")
    base_url = f"{config['url']}?date={today_str}&period={config['period']}"

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    all_events_data = []

    print(f"Начинаю парсинг Selenium: {site_name}")

    try:
        with webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options) as driver:

            # Просматриваем до 10 страниц
            for page_num in range(1, 11):
                current_url = f"{base_url}&page={page_num}"
                print(f"  - Обрабатываю страницу {page_num}/10: {current_url}")
                driver.get(current_url)

                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//*[@data-test-id='eventCard.root']"))
                    )
                except TimeoutException:
                    print(f"  - На странице {page_num} нет событий. Завершаю парсинг для '{site_name}'.")
                    break

                time.sleep(2)

                html = driver.page_source
                soup = BeautifulSoup(html, 'lxml')
                event_cards = soup.find_all("div", attrs={"data-test-id": "eventCard.root"})

                if not event_cards:
                    break

                for card in event_cards:
                    # Логика парсинга карточки
                    title_element = card.find("h2", attrs={"data-test-id": "eventCard.eventInfoTitle"})
                    title = title_element.get_text(strip=True) if title_element else "Название не найдено"

                    link_element = card.find("a", attrs={"data-test-id": "eventCard.link"})
                    link = "https://afisha.yandex.ru" + link_element['href'] if link_element else "Ссылка не найдена"

                    details_list = card.find("ul", attrs={"data-test-id": "eventCard.eventInfoDetails"})
                    place = "Место не указано"
                    date_str = "Дата не указана"

                    if details_list:
                        details_items = details_list.find_all("li")
                        if len(details_items) > 0:
                            date_str = details_items[0].get_text(strip=True)
                        if len(details_items) > 1:
                            place_link = details_items[1].find('a')
                            place = place_link.get_text(strip=True) if place_link else details_items[1].get_text(
                                strip=True)

                    price_min = None
                    price_element = card.find("span", string=re.compile(r'от \d+'))
                    if price_element:
                        price_str = price_element.get_text(strip=True)
                        price_match = re.search(r'\d+', price_str.replace(' ', ''))
                        if price_match:
                            price_min = float(price_match.group(0))

                    event_data = {
                        'title': title,
                        'place': place,
                        'time': date_str,  # В поле 'time' кладем текстовую дату
                        'link': link,
                        'timestamp': None,  # Timestamp для Яндекса мы не получаем
                        'price_min': price_min,
                        'price_max': None  # Макс. цену не парсим
                    }
                    all_events_data.append(event_data)

    except Exception as e:
        print(f"Произошла глобальная ошибка при парсинге {site_name}: {e}")

    print(f"Сайт {site_name} спарсен. Найдено событий: {len(all_events_data)}")
    print(all_events_data)
    return all_events_data