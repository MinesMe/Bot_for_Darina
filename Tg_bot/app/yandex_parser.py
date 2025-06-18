import asyncio
from playwright.async_api import async_playwright, TimeoutError

# Селекторы, которые мы ищем на странице. Их можно будет обновлять, если Яндекс изменит верстку.
TRACK_CONTAINER_SELECTOR = '.d-track'  # Контейнер одного трека
ARTIST_LINK_SELECTOR = '.d-track__artists a'  # Ссылка на исполнителя внутри трека


async def parse_yandex(url: str) -> list[str] | None:
    """
    Парсер для плейлистов Яндекс.Музыки с использованием Playwright.
    """
    print(f"Вызван парсер Яндекс.Музыки для URL: {url}")

    try:
        async with async_playwright() as p:
            # Запускаем браузер. headless=True означает, что мы не увидим окно браузера.
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 1. Переходим по ссылке
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)

            # 2. Ждем, пока на странице появятся треки.
            # Это ключевой момент: мы даем JS время на загрузку контента.
            await page.wait_for_selector(TRACK_CONTAINER_SELECTOR, timeout=15000)

            # 3. Находим все контейнеры треков
            track_elements = await page.query_selector_all(TRACK_CONTAINER_SELECTOR)

            if not track_elements:
                print("Не найдено треков на странице.")
                await browser.close()
                return []

            artists = set()  # Используем set, чтобы автоматически убирать дубликаты

            # 4. Проходим по каждому треку и извлекаем исполнителей
            for track in track_elements:
                artist_links = await track.query_selector_all(ARTIST_LINK_SELECTOR)
                for link in artist_links:
                    artist_name = await link.inner_text()
                    if artist_name:
                        artists.add(artist_name.strip())

            await browser.close()

            print(f"Найдено уникальных исполнителей: {len(artists)}")
            return list(artists)

    except TimeoutError:
        print(
            f"Ошибка: Не удалось загрузить содержимое страницы {url} за установленное время. Возможно, плейлист приватный или страница изменилась.")
        return None
    except Exception as e:
        print(f"Произошла непредвиденная ошибка при парсинге Яндекс.Музыки: {e}")
        return None