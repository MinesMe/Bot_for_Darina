import asyncio
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Optional, Dict


from playwright.async_api import async_playwright, Browser, TimeoutError as PlaywrightTimeoutError

from test_ai import getArtist

# --- КОНФИГУРАЦИЯ ---
CATEGORY_URL = 'https://www.kvitki.by/rus/bileti/teatr/'
PAGES_TO_PARSE = 1
CONCURRENT_EVENTS = 3
MAX_EVENTS_TO_PROCESS = 25

# --- МОДЕЛЬ ДАННЫХ ---
@dataclass
class EventData:
    link: str
    title: Optional[str] = None
    place: Optional[str] = None
    time_str: Optional[str] = None
    description: Optional[str] = None  ### <--- ИЗМЕНЕНИЕ 1: ДОБАВЛЕНО ПОЛЕ
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    tickets_available: Optional[int] = None
    status: str = "ok"

# --- ОСНОВНАЯ ЛОГИКА ПАРСИНГА ОДНОГО СОБЫТИЯ ---
async def parse_single_event(browser: Browser, event_url: str) -> Dict:
    page = None
    try:
        page = await browser.new_page()
        await page.goto(event_url, timeout=35000)

        # 1. Извлекаем базовую информацию (без изменений)
        try:
            details_json = await page.evaluate('() => window.concertDetails')
        except Exception:
            raise ValueError("Не удалось найти window.concertDetails")

        if not details_json:
            raise ValueError("Объект window.concertDetails пуст.")

        title = details_json.get('title')
        place = details_json.get('venueDescription')
        time_str = details_json.get('localisedStartDate')
        
        price_min_raw = details_json.get('minPrice')
        price_min = float(price_min_raw) if price_min_raw is not None else None
        
        price_max = None
        prices_str = details_json.get('prices', '')
        prices_list = [float(p) for p in re.findall(r'\d+\.?\d*', prices_str.replace(',', '.'))]
        if len(prices_list) > 1:
            price_max = max(prices_list)
        
        description = None
        description_selector = 'div.concert_details_description_description_inner'
        if await page.locator(description_selector).count() > 0:
            raw_text = await page.locator(description_selector).inner_text()
            lines = [line.strip() for line in raw_text.split('\n')]
            description = '\n'.join(line for line in lines if line)

        # 2. Получаем количество билетов (НОВАЯ УНИВЕРСАЛЬНАЯ ЛОГИКА)
        tickets_available = 0
        shop_url_button = page.locator('button[data-shopurl]').first
        
        if await shop_url_button.count() > 0:
            shop_url = await shop_url_button.get_attribute('data-shopurl')
            await page.goto(shop_url, timeout=35000)
            
            # Универсальный селектор для всех типов таблиц
            ticket_cells_selector = '[data-cy="price-zone-free-places"], .cdk-column-freePlaces'
            
            # Функция для поиска и подсчета билетов
            async def find_and_sum_tickets(search_context) -> Optional[int]:
                try:
                    # Ждем появления элементов на странице или во фрейме
                    await search_context.wait_for_selector(ticket_cells_selector, state='visible', timeout=10000)
                    await search_context.wait_for_timeout(500) # Доп. задержка
                    
                    all_counts_text = await search_context.locator(ticket_cells_selector).all_inner_texts()
                    
                    if not all_counts_text:
                        return 0
                    
                    total_tickets = 0
                    for text in all_counts_text:
                        match = re.search(r'\d+', text)
                        if match:
                            total_tickets += int(match.group(0))
                    return total_tickets
                except PlaywrightTimeoutError:
                    return None # Возвращаем None, если ничего не найдено

            # План А: Ищем на основной странице
            tickets_available = await find_and_sum_tickets(page)

            # План Б: Если на основной странице ничего нет, ищем во всех iframe
            if tickets_available is None:
                # Находим все iframe на странице
                frames = page.frames
                for frame in frames[1:]: # Пропускаем главный фрейм (саму страницу)
                    # Пытаемся найти и посчитать билеты внутри каждого фрейма
                    frame_tickets = await find_and_sum_tickets(frame)
                    if frame_tickets is not None:
                        tickets_available = frame_tickets
                        break # Нашли в первом же фрейме, выходим
            
            # Если после всех поисков ничего не нашли, считаем, что билетов 0
            if tickets_available is None:
                tickets_available = 0
        else:
            tickets_available = 0
        
        artists = await getArtist(description) # Твоя функция для AI
        event = EventData(
            title=title, place=place, time_str=time_str, link=event_url,
            description=artists, 
            price_min=price_min, price_max=price_max, tickets_available=tickets_available
        )
        print(f"✅ Успешно: {title} | Билетов: {tickets_available}", file=sys.stderr)
        return asdict(event)

    except Exception as e:
        print(f"❌ Ошибка при обработке {event_url}: {e}", file=sys.stderr)
        return asdict(EventData(link=event_url, title=f"Ошибка обработки", status="error"))
    finally:
        if page:
            await page.close()

# --- ГЛАВНАЯ ФУНКЦИЯ-ОРКЕСТРАТОР ---
async def main():
    print("🚀 Запуск парсера на Playwright...", file=sys.stderr)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 1. Собираем ссылки на все ивенты
        event_links = set()
        for page_num in range(1, PAGES_TO_PARSE + 1):
            url = f"{CATEGORY_URL}page:{page_num}/"
            print(f"📄 Сканирую страницу со списком: {url}", file=sys.stderr)
            try:
                await page.goto(url, timeout=30000)
                await page.wait_for_selector('a.event_short', timeout=15000)
            except PlaywrightTimeoutError:
                print("   - Карточки событий не найдены.", file=sys.stderr)
                break

            locators = page.locator('a.event_short')
            count = await locators.count()
            for i in range(count):
                link = await locators.nth(i).get_attribute('href')
                if link:
                    event_links.add(link)
            print(f"   - Найдено {count} ссылок.", file=sys.stderr)

        await page.close()
        
        event_links_list = list(event_links)[:MAX_EVENTS_TO_PROCESS]
        print(f"\n🔗 Всего собрано {len(event_links)} ссылок. Обрабатываю первые {len(event_links_list)}...", file=sys.stderr)
        
        # 2. Запускаем парсинг событий параллельно
        semaphore = asyncio.Semaphore(CONCURRENT_EVENTS)
        tasks = []

        async def run_with_semaphore(link):
            async with semaphore:
                return await parse_single_event(browser, link)

        for link in event_links_list:
            tasks.append(asyncio.create_task(run_with_semaphore(link)))
        
        results = await asyncio.gather(*tasks)
        await browser.close()

        # 3. Выводим результат
        final_results = [res for res in results if res['status'] == 'ok']
        
        print(f"\n🎉 ПАРСИНГ ЗАВЕРШЕН. Успешно обработано: {len(final_results)} событий.", file=sys.stderr)
        
        json_output = json.dumps(final_results, indent=2, ensure_ascii=False)
        print(json_output)


if __name__ == "__main__":
    asyncio.run(main())