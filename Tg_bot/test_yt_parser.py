# Tg_bot/test_yt_parser.py

import asyncio
import sys
import os
from typing import Set

# ВАЖНО: Этот код для Windows должен оставаться
if sys.platform == "win64":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Tg_bot.app.youtube_parser import parse_youtube

# --- НАСТРОЙКИ ТЕСТА ---
TEST_URL = "https://music.youtube.com/playlist?list=PLkcq1BWdjwh4ipce_heXxM0r1PIKawZqV"

# --- ИЗМЕНЕНИЕ ДЛЯ HEADLESS-РЕЖИМА ---
DEBUG_MODE = False  # Устанавливаем в False, чтобы скрыть браузер
# -----------------------------------

# Путь к файлу 'artists.txt', который лежит в той же папке
MASTER_LIST_FILENAME = "artists.txt"
MASTER_LIST_PATH = os.path.join(os.path.dirname(__file__), MASTER_LIST_FILENAME)


def load_master_artist_list(path: str) -> Set[str]:
    """Загружает мастер-лист исполнителей из файла."""
    print(f"--- Загрузка мастер-листа из файла: {path} ---")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            artists = {line.strip().lower() for line in f if line.strip()}
        print(f"--- Загружено {len(artists)} уникальных исполнителей в мастер-лист ---")
        return artists
    except FileNotFoundError:
        print(f"!!! КРИТИЧЕСКАЯ ОШИБКА: Файл с мастер-листом не найден по пути: {path}")
        return set()


async def main():
    print("--- Запуск теста парсера YouTube Music (в фоновом режиме) ---")

    master_artists = load_master_artist_list(MASTER_LIST_PATH)
    if not master_artists:
        print("--- Тест прерван из-за отсутствия мастер-листа ---")
        return

    print(f"\nURL для теста: {TEST_URL}")

    found_artists = await parse_youtube(TEST_URL, master_artists=master_artists, debug=DEBUG_MODE)

    if found_artists is None:
        print("\n--- Результат ---")
        print("Парсер вернул None. Произошла критическая ошибка.")
    elif not found_artists:
        print("\n--- Результат ---")
        print("Парсер вернул пустой список. Совпадений с вашим мастер-листом не найдено.")
    else:
        print(f"\n--- Итоговый результат (найдено {len(found_artists)} уникальных исполнителей из вашего списка) ---")
        found_artists.sort()
        for i, artist in enumerate(found_artists, 1):
            print(f"{i}. {artist}")

    print("\n--- Тест завершен ---")


if __name__ == "__main__":
    asyncio.run(main())