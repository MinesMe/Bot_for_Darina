import asyncio
from playwright.async_api import async_playwright

# --- ВСТАВЬ СЮДА ССЫЛКУ НА СТРАНИЦУ ПОКУПКИ (shop_url) ---
# Это должна быть ссылка, которая начинается с https://store.kvitki.by/...
# и где ты точно видишь таблицу с data-cy="price-zone-free-places"
SHOP_URL_TO_DEBUG = "https://store.kvitki.by/public/ru/event/469637/purchase/sector/48057?sp=rus"
# -------------------------------------------------------------

async def main():
    print("--- ЗАПУСК ФИНАЛЬНОГО ОТЛАДОЧНОГО СКРИПТА ---")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Запускаем в видимом режиме
        page = await browser.new_page()

        print(f"1. Перехожу на страницу покупки: {SHOP_URL_TO_DEBUG}")
        try:
            await page.goto(SHOP_URL_TO_DEBUG, timeout=60000)
            
            # Ждем 10 секунд, чтобы все точно прогрузилось
            print("2. Жду 10 секунд для полной загрузки JavaScript...")
            await page.wait_for_timeout(10000)

            # Делаем скриншот всей страницы
            await page.screenshot(path="debug_full_page.png", full_page=True)
            print("3. Скриншот всей страницы сохранен в 'debug_full_page.png'")

            # Сохраняем HTML
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            print("4. HTML-код страницы сохранен в 'debug_page.html'")

            # Пытаемся найти таблицу и сделать ее скриншот
            table_selector = 'app-price-zones-table' # Селектор для всей таблицы
            table_element = page.locator(table_selector)
            
            if await table_element.count() > 0:
                await table_element.screenshot(path="debug_table_screenshot.png")
                print("5. Скриншот только таблицы сохранен в 'debug_table_screenshot.png'")
            else:
                print("5. Не удалось найти таблицу по селектору 'app-price-zones-table'.")

        except Exception as e:
            print(f"\n❌ Произошла ошибка: {e}")
            await page.screenshot(path="debug_error_page.png")
            print("Скриншот страницы с ошибкой сохранен в 'debug_error_page.png'")

        print("\n--- БРАУЗЕР ОСТАНОВЛЕН ---")
        print("Посмотри на окно. Чтобы завершить, закрой его вручную.")
        await page.pause()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())