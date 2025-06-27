import asyncio
import re
import sys
import json
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
# --- ПРАВИЛЬНЫЙ ИМПОРТ СОГЛАСНО ДОКУМЕНТАЦИИ ---
from playwright_stealth import stealth_async

# --- Модель данных (без изменений) ---
@dataclass
class EventData:
    link: str
    title: Optional[str] = None
    place: Optional[str] = None
    time_str: Optional[str] = None
    full_description: Optional[str] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    status: str = "ok"

# --- Функция парсинга одной страницы (с правильным вызовом stealth) ---
async def parse_single_event(browser: Browser, event_url: str) -> Dict:
    page = None
    try:
        page = await browser.new_page()
        # --- ПРАВИЛЬНЫЙ ВЫЗОВ ---
        await stealth_async(page)
        
        await page.goto(event_url, timeout=90000, wait_until='domcontentloaded')
        
        await page.wait_for_selector('h1[class*="Title-sc-"]', timeout=45000)
        title = await page.locator('h1[class*="Title-sc-"]').inner_text()
        
        place_time_locator = page.locator('div[class*="EventDescription-sc-"]')
        place = await place_time_locator.locator('a[class*="Link-sc-"]').first.inner_text()
        time_str = await place_time_locator.locator('div[class*="EventDate-sc-"]').first.inner_text()

        description_locator = page.locator('div[class*="Description-sc-"]')
        full_description = await description_locator.inner_text() if await description_locator.count() > 0 else ""

        price_min, price_max = None, None
        price_locator = page.locator('span[class*="Price-sc-"]')
        if await price_locator.count() > 0:
            price_text = await price_locator.first.inner_text()
            prices = [float(p) for p in re.findall(r'\d+', price_text.replace(' ', ''))]
            if prices:
                price_min = min(prices)
                if len(prices) > 1:
                    price_max = max(prices)
        
        event = EventData(
            link=event_url, title=title, place=place, time_str=time_str, 
            full_description=full_description, price_min=price_min, price_max=price_max
        )
        print(f"✅ [Playwright] Собраны данные: {title}", file=sys.stderr)
        return asdict(event)

    except Exception as e:
        print(f"❌ [Playwright] Ошибка при сборе данных для {event_url}: {e}", file=sys.stderr)
        return asdict(EventData(link=event_url, title=f"Ошибка обработки", status="error"))
    finally:
        if page:
            await page.close()


async def parse_site(config: Dict) -> List[Dict]:
    """
    Основная функция-парсер для сайта Yandex.Afisha с использованием Playwright и Stealth.
    """
    base_url = config.get('url')
    if not base_url:
        print(f"❌ [Playwright] В конфиге отсутствует ключ 'url'.", file=sys.stderr)
        return []
        
    max_events_limit = config.get('max_events_to_process_limit', 15)
    concurrent_events = config.get('concurrent_events', 2)

    print(f"\n[INFO] Запуск Playwright-парсера для URL: '{base_url}' (в стелс-режиме)", file=sys.stderr)
    
    event_links = set()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page_for_lists = await browser.new_page()

        # --- ПРАВИЛЬНЫЙ ВЫЗОВ ---
        await stealth_async(page_for_lists)

        try:
            print("   - Загружаю страницу со списком событий...", file=sys.stderr)
            await page_for_lists.goto(base_url, timeout=90000, wait_until='domcontentloaded')

            try:
                cookie_button_selector = 'button:text-matches("Принять все|Allow all", "i")'
                print("   - Ищу cookie-баннер...", file=sys.stderr)
                await page_for_lists.locator(cookie_button_selector).click(timeout=10000)
                print("   - Cookie-баннер нажат.", file=sys.stderr)
            except PlaywrightTimeoutError:
                print("   - Cookie-баннер не найден, продолжаю.", file=sys.stderr)
            
            try:
                close_button_selector = 'div[class*="Popup-sc-"] button[class*="Close-sc-"]'
                print("   - Ищу баннер с подпиской...", file=sys.stderr)
                await page_for_lists.locator(close_button_selector).click(timeout=5000)
                print("   - Баннер с подпиской закрыт.", file=sys.stderr)
            except PlaywrightTimeoutError:
                print("   - Баннер с подпиской не найден, продолжаю.", file=sys.stderr)

            event_card_selector = 'a[data-test-id="eventCard.link"]'
            await page_for_lists.wait_for_selector(event_card_selector, timeout=30000)
            print("   - Страница очищена и готова, начинаю сбор ссылок...", file=sys.stderr)

            for _ in range(10): 
                if len(event_links) >= max_events_limit: break
                locators = page_for_lists.locator(event_card_selector)
                for i in range(await locators.count()):
                    if len(event_links) >= max_events_limit: break
                    link = await locators.nth(i).get_attribute('href')
                    if link and not link.startswith('http'):
                        event_links.add(f"https://afisha.yandex.ru{link}")
                print(f"   - Собрано {len(event_links)}/{max_events_limit} ссылок.", file=sys.stderr)
                if len(event_links) >= max_events_limit: break
                
                show_more_button = page_for_lists.locator('button:has-text("Показать ещё")')
                if await show_more_button.count() > 0 and await show_more_button.is_visible():
                    await show_more_button.click()
                    await page_for_lists.wait_for_timeout(3000)
                else: break
        except Exception as e:
            print(f"   - Ошибка при сборе ссылок: {e}", file=sys.stderr)
        finally:
            await page_for_lists.close()
            
        event_links_list = list(event_links)
        print(f"\n🔗 Всего найдено {len(event_links_list)} уникальных ссылок для обработки.", file=sys.stderr)
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
    
    final_results = []
    for res in results:
        if res.get('status') == 'ok':
            res['time'] = res.pop('time_str', None)
            res['tickets_info'] = "В наличии" if res.get('price_min') is not None else "Нет в наличии"
            res.pop('status', None)
            final_results.append(res)
    print(f"🎉 Сбор данных завершен. Собрано: {len(final_results)} событий.", file=sys.stderr)
    return final_results

if __name__ == '__main__':
    print("--- ЗАПУСК АВТОНОМНОГО ТЕСТА ПАРСЕРА YANDEX (PLAYWRIGHT+STEALTH) ---")
    
    test_config = {
        'url': 'https://afisha.yandex.ru/moscow/selections/all-events-concert',
        'max_events_to_process_limit': 5,
        'concurrent_events': 2,
    }
    
    try:
        results = asyncio.run(parse_site(test_config))
        print("\n--- ИТОГОВЫЙ РЕЗУЛЬТАТ ТЕСТА ---")
        print(json.dumps(results, indent=2, ensure_ascii=False))

    except KeyboardInterrupt:
        print("\nПроцесс остановлен пользователем.")