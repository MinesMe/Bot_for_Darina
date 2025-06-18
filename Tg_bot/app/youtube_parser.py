# Tg_bot/app/youtube_parser.py

import asyncio
import re
from playwright.async_api import async_playwright, TimeoutError
from typing import Set

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# Оставляем только нужные селекторы
PLAYLIST_ITEM_SELECTOR = 'ytmusic-responsive-list-item-renderer'
ARTIST_SELECTOR = 'yt-formatted-string.flex-column a'


async def parse_youtube(url: str, master_artists: Set[str], debug: bool = False) -> list[str] | None:
    """
    Парсит плейлист YouTube Music и выполняет поиск совпадений,
    проверяя ТОЛЬКО поле исполнителя.
    """
    print(f"Вызван парсер YouTube Music для URL: {url}")
    print("--- РЕЖИМ ПОИСКА: Только в поле исполнителя ---")
    if not master_artists:
        print("Мастер-лист исполнителей пуст. Поиск невозможен.")
        return []

    launch_options = {'headless': not debug}
    if debug:
        launch_options['slow_mo'] = 50

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_options)
            context = await browser.new_context(user_agent=USER_AGENT, locale="en-US")
            page = await context.new_page()

            page.set_default_timeout(45000)
            await page.goto(url, wait_until="domcontentloaded")

            # ... (логика cookie без изменений) ...
            try:
                print("Проверка на наличие окна о cookie...")
                accept_button = page.locator('button[aria-label*="Accept"], button:has-text("Accept all")').first
                await accept_button.click(timeout=10000)
                print("Окно о cookie найдено и закрыто.")
                await page.wait_for_timeout(1500)
            except (TimeoutError, Exception):
                print("Окно о cookie не появилось или не удалось закрыть, продолжаю.")
                pass

            await page.wait_for_selector(PLAYLIST_ITEM_SELECTOR, timeout=30000)

            print("Начинаю скроллинг страницы...")
            last_height = await page.evaluate("document.body.scrollHeight")
            while True:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
            print("Скроллинг завершен.")

            playlist_items = await page.query_selector_all(PLAYLIST_ITEM_SELECTOR)
            if not playlist_items:
                print("Не найдено треков на странице.")
                await browser.close()
                return []

            matched_artists_from_master_list = set()
            print(f"\n--- Начинаю анализ {len(playlist_items)} треков и сравнение с мастер-листом ---")

            # --- УПРОЩЕННАЯ ЛОГИКА ПОИСКА ТОЛЬКО ПО АВТОРУ ---
            for item in playlist_items:
                # 1. Извлекаем ТОЛЬКО имя автора
                artist_element = await item.query_selector(ARTIST_SELECTOR)
                artist_name = (await artist_element.inner_text()).strip() if artist_element else ""

                # Если имя автора не найдено, пропускаем этот трек
                if not artist_name:
                    continue

                artist_lower = artist_name.lower()

                # 2. Ищем совпадения в имени автора
                for master_artist in master_artists:
                    pattern = r'\b' + re.escape(master_artist) + r'\b'

                    if re.search(pattern, artist_lower):
                        print(
                            f"✅ НАЙДЕНО СОВПАДЕНИЕ: '{master_artist}' из мастер-листа найден в поле автора: '{artist_name}'")
                        matched_artists_from_master_list.add(master_artist)

            print("\n--- Анализ треков завершен ---")

            if debug:
                print(f"--- ПАУЗА 5 СЕКУНД ПЕРЕД ЗАКРЫТИЕМ ---")
                await page.wait_for_timeout(5000)

            await browser.close()

            print(f"Всего найдено совпадений с мастер-листом: {len(matched_artists_from_master_list)}")
            return list(matched_artists_from_master_list)

    except TimeoutError as e:
        print(f"Критическая ошибка: Не удалось выполнить действие за установленное время. {e}")
        return None
    except Exception as e:
        import traceback
        print(f"Произошла непредвиденная ошибка при парсинге YouTube Music: {e}")
        traceback.print_exc()
        return None