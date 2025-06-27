# Файл: parsers/test_parser.py

import asyncio
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
import logging # <-- Добавить импорт

from playwright.async_api import async_playwright, Browser, TimeoutError as PlaywrightTimeoutError

# --- ГЛОБАЛЬНЫЕ НАСТРОЙКИ (без изменений) ---
CONCURRENT_EVENTS = 5

# --- ИЗМЕНЕНИЕ 1: Обновляем модель данных ---
# Мы разделили описание на два поля для ясности.
@dataclass
class EventData:
    link: str
    title: Optional[str] = None
    place: Optional[str] = None
    # Это поле пойдет в Event.description в БД
    time_str: Optional[str] = None
    full_description: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    tickets_available: Optional[int] = None
    status: str = "ok"


# --- ИЗМЕНЕНИЕ 2: Обновляем логику парсинга одного события ---
async def parse_single_event(browser: Browser, event_url: str) -> Dict:
    """
    Собирает ВСЕ сырые данные со страницы события, но НЕ вызывает AI.
    """
    page = None
    try:
        page = await browser.new_page()
        await page.goto(event_url, timeout=60000)

        # 1. Извлекаем базовую информацию из JSON
        try:
            details_json = await page.evaluate('() => window.concertDetails')
        except Exception:
            raise ValueError("Не удалось найти window.concertDetails")

        if not details_json:
            raise ValueError("Объект window.concertDetails пуст.")

        title = details_json.get('title')
        place = details_json.get('venueDescription')
        # Сохраняем строку со временем. Она пойдет в БД в поле description.
        time_str = details_json.get('localisedStartDate')
        
        price_min_raw = details_json.get('minPrice')
        price_min = float(price_min_raw) if price_min_raw is not None else None
        price_max = None
        prices_str = details_json.get('prices', '')
        prices_list = [float(p) for p in re.findall(r'\d+\.?\d*', prices_str.replace(',', '.'))]
        if len(prices_list) > 1:
            price_max = max(prices_list)

        # 2. Извлекаем ПОЛНОЕ описание для AI
        full_description = None
        description_selector = 'div.concert_details_description_description_inner'
        if await page.locator(description_selector).count() > 0:
            raw_text = await page.locator(description_selector).inner_text()
            lines = [line.strip() for line in raw_text.split('\n')]
            full_description = '\n'.join(line for line in lines if line)

        # 3. Получаем количество билетов и ссылку на покупку
        tickets_available = 0
        shop_url = None
        shop_url_button = page.locator('button[data-shopurl]').first

        if await shop_url_button.count() > 0:
            shop_url = await shop_url_button.get_attribute('data-shopurl')
            await page.goto(shop_url, timeout=60000)
            
            ticket_cells_selector = '[data-cy="price-zone-free-places"], .cdk-column-freePlaces'
            async def find_and_sum_tickets(search_context) -> Optional[int]:
                try:
                    await search_context.wait_for_selector(ticket_cells_selector, state='visible', timeout=15000)
                    await search_context.wait_for_timeout(500)
                    all_counts_text = await search_context.locator(ticket_cells_selector).all_inner_texts()
                    if not all_counts_text: return 0
                    return sum(int(match.group(0)) for text in all_counts_text if (match := re.search(r'\d+', text)))
                except PlaywrightTimeoutError:
                    return None
            tickets_available = await find_and_sum_tickets(page)
            if tickets_available is None:
                for frame in page.frames[1:]:
                    frame_tickets = await find_and_sum_tickets(frame)
                    if frame_tickets is not None:
                        tickets_available = frame_tickets
                        break
            if tickets_available is None: tickets_available = 0
        else:
            tickets_available = 0
        
        # 4. Формируем итоговый объект с сырыми данными. БЕЗ ВЫЗОВА AI.
        event = EventData(
            link=shop_url if shop_url else event_url, 
            title=title, 
            place=place, 
            time_str=time_str,
            full_description=full_description, 
            price_min=price_min, 
            price_max=price_max, 
            tickets_available=tickets_available
        )
        print(f"✅ Сырые данные собраны: {title}", file=sys.stderr)
        return asdict(event)

    except Exception as e:
        print(f"❌ Ошибка при сборе сырых данных для {event_url}: {e}", file=sys.stderr)
        return asdict(EventData(link=event_url, title=f"Ошибка обработки", status="error"))
    finally:
        if page:
            await page.close()


# --- ИЗМЕНЕНИЕ 3: Главная функция parse_site ---
# Нужно адаптировать ее под новый формат данных
async def parse_site(config: Dict) -> List[Dict]:
    """
    Основная функция-парсер для сайта Kvitki.by с использованием Playwright.
    Принимает конфиг, возвращает список словарей с данными о событиях.
    """
    base_url = config.get('url')
    category_name = config.get('category_name', 'Unknown Category')
    if not base_url:
        print(f"❌ [Playwright] В конфиге для '{category_name}' отсутствует ключ 'url'.", file=sys.stderr)
        return []

    pages_to_parse_limit = config.get('pages_to_parse_limit', float('inf'))
    max_events_limit = config.get('max_events_to_process_limit', float('inf'))
    concurrent_events = config.get('concurrent_events', CONCURRENT_EVENTS)

    print(f"\n[INFO] Запуск Playwright-парсера для категории: '{category_name}'", file=sys.stderr)
    if pages_to_parse_limit != float('inf') or max_events_limit != float('inf'):
        print(f"⚠️ [ТЕСТОВЫЙ РЕЖИМ] Применены ограничения: страниц={int(pages_to_parse_limit)}, событий={int(max_events_limit)}", file=sys.stderr)
    
    event_links = set()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page_for_lists = await browser.new_page()

        page_num = 1
        while page_num <= pages_to_parse_limit:
            url = f"{base_url}page:{page_num}/"
            print(f"📄 Сканирую страницу: {url}", file=sys.stderr)
            try:
                await page_for_lists.goto(url, timeout=30000)
                await page_for_lists.wait_for_selector('a.event_short', timeout=10000, state='attached')
                locators = page_for_lists.locator('a.event_short')
                new_links_count = 0
                for i in range(await locators.count()):
                    if len(event_links) >= max_events_limit: break
                    link = await locators.nth(i).get_attribute('href')
                    if link and link not in event_links:
                        event_links.add(link)
                        new_links_count += 1
                if new_links_count == 0:
                    print(f"   - Новые события на странице {page_num} не найдены. Завершаю сбор.", file=sys.stderr)
                    break
                print(f"   - Найдено {new_links_count} новых ссылок. Всего собрано: {len(event_links)}", file=sys.stderr)
                if len(event_links) >= max_events_limit:
                    print("   - Достигнут лимит событий. Завершаю сбор.", file=sys.stderr)
                    break
                page_num += 1
            except PlaywrightTimeoutError:
                print(f"   - Карточки событий на странице {page_num} не найдены. Завершаю сбор.", file=sys.stderr)
                break
            except Exception as e:
                print(f"   - Произошла непредвиденная ошибка: {e}. Завершаю сбор.", file=sys.stderr)
                break
        
        await page_for_lists.close()
        
        event_links_list = list(event_links)
        print(f"\n🔗 Всего собрано {len(event_links_list)} уникальных ссылок для обработки.", file=sys.stderr)
        
        if not event_links_list:
            await browser.close()
            return []

        semaphore = asyncio.Semaphore(concurrent_events)
        tasks = []
        async def run_with_semaphore(link):
            async with semaphore:
                return await parse_single_event(browser, link)

        for link in event_links_list:
            tasks.append(asyncio.create_task(run_with_semaphore(link)))
        
        results = await asyncio.gather(*tasks)
        await browser.close()

    # Адаптируем результат под формат, который ожидает run_parsers.py
    final_results = []
    for res in results:
        if res.get('status') == 'ok':
            # Переименовываем 'time_str' в 'time' для совместимости с run_parsers.py
            # Это поле пойдет в Event.description
            res['time'] = res.pop('time_str', None)
            
            tickets_count = res.pop('tickets_available', 0)
            if tickets_count is not None and tickets_count > 0:
                res['tickets_info'] = f"{tickets_count} билетов"
            else:
                res['tickets_info'] = "В наличии" if res.get('price_min') else "Нет в наличии"
            
            res.pop('status', None)
            final_results.append(res)
            
    print(f"🎉 Сбор сырых данных для '{category_name}' завершен. Собрано: {len(final_results)} событий.", file=sys.stderr)
    return final_results


# --- Блок для автономного тестирования файла (без изменений) ---
if __name__ == '__main__':
    print("--- ЗАПУСК АВТОНОМНОГО ТЕСТА ПАРСЕРА ---")
    print("Парсер будет работать в режиме с ограничениями.")

    test_config = {
        'category_name': 'Музыка (Тест)',
        'url': 'https://www.kvitki.by/rus/bileti/muzyka/',
        'event_type': 'Концерт',
        'parsing_method': 'playwright_kvitki',
        'pages_to_parse_limit': 1,
        'max_events_to_process_limit': 3,
    }

    async def run_test():
        results = await parse_site(test_config)
        print("\n--- ИТОГОВЫЙ РЕЗУЛЬТАТ ТЕСТА (СЫРЫЕ ДАННЫЕ) ---")
        print(json.dumps(results, indent=2, ensure_ascii=False))
        print(f"\nВсего получено: {len(results)} событий.")

    try:
        asyncio.run(run_test())
    except KeyboardInterrupt:
        print("\n\nПроцесс парсинга остановлен пользователем.")
    except Exception as e:
        print(f"\nВо время тестового запуска произошла ошибка: {e}")