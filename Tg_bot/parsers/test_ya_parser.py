import asyncio
import re
import sys
import json
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

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

async def parse_single_event(browser: Browser, event_url: str, max_retries: int = 2) -> Dict:
    page = None
    for attempt in range(max_retries):
        try:
            page = await browser.new_page()
            print(f"   - [Attempt {attempt + 1}] Загружаю страницу события: {event_url}", file=sys.stderr)
            await page.goto(event_url, timeout=120000, wait_until='domcontentloaded')

            # Ожидаем полной загрузки контента
            await page.wait_for_load_state('networkidle', timeout=90000)

            # Проверяем наличие заголовка через JavaScript
            await page.wait_for_function(
                "() => document.querySelector('h1[class*=\"Title-sc-\"]') !== null || document.querySelector('h1') !== null",
                timeout=90000
            )
            # Пробуем основной селектор, затем запасной
            title_locator = page.locator('h1[class*="Title-sc-"]')
            if await title_locator.count() > 0 and await title_locator.is_visible():
                title = await title_locator.inner_text()
            else:
                title = await page.locator('h1').inner_text() or "Название не найдено"

            place_time_locator = page.locator('div[class*="EventDescription-sc-"]')
            place = await place_time_locator.locator('a[class*="Link-sc-"]').first.inner_text() or "Место не найдено"
            time_str = await place_time_locator.locator('div[class*="EventDate-sc-"]').first.inner_text() or "Время не найдено"

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

        except PlaywrightTimeoutError as e:
            print(f"❌ [Playwright] Таймаут при попытке {attempt + 1} для {event_url}: {e}", file=sys.stderr)
            if page and attempt == max_retries - 1:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                await page.screenshot(path=f"error_screenshot_event_{timestamp}.png")
                html = await page.content()
                with open(f"error_page_event_{timestamp}.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"   - Сохранены скриншот и HTML: error_screenshot_event_{timestamp}.png, error_page_event_{timestamp}.html", file=sys.stderr)
            if attempt < max_retries - 1:
                print(f"   - Повторяю попытку...", file=sys.stderr)
                await asyncio.sleep(3)
                continue
            return asdict(EventData(link=event_url, title="Ошибка обработки (таймаут)", status="error"))
        except Exception as e:
            print(f"❌ [Playwright] Ошибка при сборе данных для {event_url}: {e}", file=sys.stderr)
            return asdict(EventData(link=event_url, title="Ошибка обработки", status="error"))
        finally:
            if page:
                await page.close()

async def parse_site(config: Dict) -> List[Dict]:
    base_url = config.get('url')
    if not base_url:
        print(f"❌ [Playwright] В конфиге отсутствует ключ 'url'.", file=sys.stderr)
        return []

    max_events_limit = config.get('max_events_to_process_limit', 15)
    concurrent_events = config.get('concurrent_events', 2)

    print(f"\n[INFO] Запуск Playwright-парсера для URL: '{base_url}' (в стелс-режиме)", file=sys.stderr)

    event_links = set()

    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=False, slow_mo=150)
        page_for_lists = await browser.new_page()
        await page_for_lists.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
        })

        try:
            print("   - Загружаю страницу со списком событий...", file=sys.stderr)
            await page_for_lists.goto(base_url, timeout=120000, wait_until='networkidle')

            # Обработка баннеров
            try:
                await page_for_lists.locator('button:text-matches("Принять все|Allow all|Согласиться", "i")').click(timeout=15000)
                print("   - Cookie-баннер нажат.", file=sys.stderr)
            except PlaywrightTimeoutError:
                print("   - Cookie-баннер не найден.", file=sys.stderr)

            try:
                await page_for_lists.locator('div[class*="Popup-sc-"] button[class*="Close-sc-"], button:text("Закрыть")').click(timeout=10000)
                print("   - Баннер с подпиской закрыт.", file=sys.stderr)
            except PlaywrightTimeoutError:
                print("   - Баннер с подпиской не найден.", file=sys.stderr)

            # Ожидание и сбор ссылок
            event_card_selector = 'a[data-test-id="eventCard.link"]'
            print("   - Ожидаю загрузку карточек событий...", file=sys.stderr)
            await page_for_lists.wait_for_function(
                f"() => document.querySelectorAll('{event_card_selector}').length > 0 && Array.from(document.querySelectorAll('{event_card_selector}')).every(el => el.offsetParent !== null)",
                timeout=60000
            )
            print("   - Карточки событий найдены, начинаю сбор ссылок...", file=sys.stderr)

            for _ in range(10):
                if len(event_links) >= max_events_limit: break
                locators = page_for_lists.locator(event_card_selector)
                count = await locators.count()
                print(f"   - Найдено {count} карточек событий на странице.", file=sys.stderr)
                for i in range(count):
                    if len(event_links) >= max_events_limit: break
                    link = await locators.nth(i).get_attribute('href')
                    if link and not link.startswith('http'):
                        event_links.add(f"https://afisha.yandex.ru{link}")
                print(f"   - Собрано {len(event_links)}/{max_events_limit} ссылок.", file=sys.stderr)
                if len(event_links) >= max_events_limit: break

                show_more_button = page_for_lists.locator('button:has-text("Показать ещё")')
                if await show_more_button.count() > 0 and await show_more_button.is_visible():
                    print("   - Нажимаю кнопку 'Показать ещё'...", file=sys.stderr)
                    await show_more_button.click()
                    await page_for_lists.wait_for_load_state('networkidle', timeout=10000)
                else:
                    print("   - Кнопка 'Показать ещё' не найдена или не видима.", file=sys.stderr)
                    break
        except PlaywrightTimeoutError as e:
            print(f"   - Ошибка при сборе ссылок (таймаут): {e}", file=sys.stderr)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            await page_for_lists.screenshot(path=f"error_screenshot_list_{timestamp}.png")
            html = await page_for_lists.content()
            with open(f"error_page_list_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"   - Сохранены скриншот и HTML: error_screenshot_list_{timestamp}.png, error_page_list_{timestamp}.html", file=sys.stderr)
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
    print("--- ЗАПУСК АВТОНОМНОГО ТЕСТА ПАРСЕРА YANDEX ---")

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