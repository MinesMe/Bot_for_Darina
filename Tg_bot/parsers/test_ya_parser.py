import asyncio
import logging
import re
from datetime import datetime
import time  # <-- ИЗМЕНЕНО: Импортируем стандартный time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Используем тот же логгер, что и в основном приложении
logger = logging.getLogger()


def _parse_sync(config: dict) -> list[dict]:
    """
    Синхронная функция, которая выполняет всю грязную работу с Selenium.
    Она будет запущена в отдельном потоке.
    """
    site_name = config['site_name']
    today_str = datetime.now().strftime("%Y-%m-%d")
    base_url = f"{config['url']}?date={today_str}&period={config['period']}"

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    # Дополнительные флаги для стабильности в Docker/Linux
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


    all_events_data = []
    logger.info(f"Начинаю парсинг Selenium: {site_name}")

    driver = None  # Инициализируем заранее для блока finally
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        for page_num in range(1, 11): # Просматриваем до 10 страниц
            current_url = f"{base_url}&page={page_num}"
            logger.info(f"  - Обрабатываю страницу {page_num}/10: {current_url}")
            driver.get(current_url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//*[@data-test-id='eventCard.root']"))
                )
            except TimeoutException:
                logger.info(f"  - На странице {page_num} нет событий или они не загрузились. Завершаю парсинг для '{site_name}'.")
                break
            
            # ИСПРАВЛЕНИЕ: Используем time.sleep() внутри синхронной функции
            time.sleep(2)

            html = driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            event_cards = soup.find_all("div", attrs={"data-test-id": "eventCard.root"})

            if not event_cards:
                logger.info(f"  - BeautifulSoup не нашел карточек на странице {page_num}, хотя они должны были быть. Завершаю.")
                break

            for card in event_cards:
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
                        place = place_link.get_text(strip=True) if place_link else details_items[1].get_text(strip=True)

                price_min = None
                price_element = card.find("span", string=re.compile(r'от \d+'))
                if price_element:
                    price_str = price_element.get_text(strip=True)
                    price_match = re.search(r'\d+', price_str.replace(' ', ''))
                    if price_match:
                        price_min = float(price_match.group(0))

                # Формируем словарь, соответствующий другим парсерам
                event_data = {
                    'title': title,
                    'place': place,
                    'time': date_str,      # Строковое представление даты
                    'link': link,
                    'price_min': price_min,
                    # Добавляем заглушки для полей, которых нет в Яндексе
                    'price_max': None,
                    'tickets_info': None,
                    'full_description': None, # AI будет работать с пустым описанием, ничего страшного
                }
                all_events_data.append(event_data)
    
    except WebDriverException as e:
         logger.error(f"Ошибка Selenium при парсинге {site_name}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Произошла глобальная ошибка при парсинге {site_name}: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit() # Гарантированно закрываем браузер
            logger.info(f"Драйвер для {site_name} успешно закрыт.")

    logger.info(f"Сайт {site_name} спарсен. Найдено событий: {len(all_events_data)}")
    return all_events_data


async def parse(config: dict) -> list[dict]:
    """
    Асинхронная обертка для запуска синхронного парсера в отдельном потоке.
    """
    logger.info(f"Запускаю парсер Yandex для '{config['site_name']}' в фоновом потоке...")
    loop = asyncio.get_running_loop()
    
    # Запускаем _parse_sync в executor'е пула потоков по умолчанию
    result = await loop.run_in_executor(
        None, 
        _parse_sync, 
        config
    )
    return result