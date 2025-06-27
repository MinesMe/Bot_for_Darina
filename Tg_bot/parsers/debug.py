import asyncio
import sys
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth

async def save_event_page(event_url: str) -> None:
    """
    Загружает страницу события, сохраняет HTML и скриншот, пытается извлечь заголовок.
    
    Args:
        event_url (str): URL страницы события (например, https://afisha.yandex.ru/moscow/standup/standup-action)
    """
    print(f"\n[INFO] Запуск парсера для URL: '{event_url}' (в стелс-режиме)", file=sys.stderr)

    async with Stealth().use_async(async_playwright()) as p:
        browser = None
        page = None
        try:
            # Запускаем браузер в видимом режиме
            browser = await p.chromium.launch(headless=False, slow_mo=150)
            page = await browser.new_page()
            await page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
            })

            # Логируем сетевые запросы
            async def log_request(route):
                print(f"   - Request: {route.request.url}", file=sys.stderr)
                await route.continue_()
            await page.route("**/*", log_request)

            print("   - Загружаю страницу события...", file=sys.stderr)
            await page.goto(event_url, timeout=120000, wait_until='domcontentloaded')

            # Ожидаем загрузки DOM
            await page.wait_for_load_state('domcontentloaded', timeout=90000)

            # Обработка баннеров
            try:
                await page.locator('button:text-matches("Принять все|Allow all|Согласиться", "i")').click(timeout=15000)
                print("   - Cookie-баннер нажат.", file=sys.stderr)
            except PlaywrightTimeoutError:
                print("   - Cookie-баннер не найден.", file=sys.stderr)

            try:
                await page.locator('div[class*="Popup-sc-"] button[class*="Close-sc-"], button:text("Закрыть")').click(timeout=10000)
                print("   - Баннер с подпиской закрыт.", file=sys.stderr)
            except PlaywrightTimeoutError:
                print("   - Баннер с подпиской не найден.", file=sys.stderr)

            # Проверяем наличие заголовка для отладки
            try:
                await page.wait_for_function(
                    "() => document.querySelector('h1[class*=\"Title-sc-\"]') !== null || document.querySelector('h1') !== null",
                    timeout=30000
                )
                title_locator = page.locator('h1[class*="Title-sc-"]')
                if await title_locator.count() > 0 and await title_locator.is_visible():
                    title = await title_locator.inner_text()
                    print(f"   - Найден заголовок (Title-sc-): {title}", file=sys.stderr)
                else:
                    title = await page.locator('h1').inner_text() or "Название не найдено"
                    print(f"   - Найден запасной заголовок: {title}", file=sys.stderr)
            except PlaywrightTimeoutError:
                print("   - Заголовок не найден.", file=sys.stderr)

            # Сохраняем HTML и скриншот
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html = await page.content()
            with open(f"event_page_{timestamp}.html", "w", encoding="utf-8") as f:
                f.write(html)
            await page.screenshot(path=f"event_screenshot_{timestamp}.png", full_page=True)
            print(f"   - Сохранены файлы: event_page_{timestamp}.html, event_screenshot_{timestamp}.png", file=sys.stderr)

        except PlaywrightTimeoutError as e:
            print(f"❌ [Playwright] Ошибка таймаута: {e}", file=sys.stderr)
            if page:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                html = await page.content()
                with open(f"error_page_{timestamp}.html", "w", encoding="utf-8") as f:
                    f.write(html)
                await page.screenshot(path=f"error_screenshot_{timestamp}.png", full_page=True)
                print(f"   - Сохранены файлы при ошибке: error_page_{timestamp}.html, error_screenshot_{timestamp}.png", file=sys.stderr)
        except Exception as e:
            print(f"❌ [Playwright] Ошибка: {e}", file=sys.stderr)
        finally:
            if page:
                await page.close()
            if browser:
                await browser.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Парсер страницы события Яндекс Афиши")
    parser.add_argument('url', type=str, help='URL страницы события')
    args = parser.parse_args()

    print("--- ЗАПУСК ПАРСЕРА СТРАНИЦЫ СОБЫТИЯ ---")
    try:
        asyncio.run(save_event_page(args.url))
        print("\n--- ПАРСИНГ ЗАВЕРШЕН ---")
    except KeyboardInterrupt:
        print("\nПроцесс остановлен пользователем.")