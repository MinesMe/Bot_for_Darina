# app/playlist_parser.py

# Импортируем парсеры из соответствующих файлов
# УДАЛЕН ИМПОРТ SPOTIFY
from .yandex_parser import parse_yandex
from .youtube_parser import parse_youtube
from .boom_parser import parse_boom
from typing import Set


async def parse_playlist_url(url: str, master_artists: Set[str] = None) -> list[str] | None:
    """
    Главная функция-диспетчер.
    Определяет сервис по URL и вызывает соответствующий парсер.
    """
    url_lower = url.lower()

    # УДАЛЕН БЛОК ПРОВЕРКИ ДЛЯ SPOTIFY
    if "music.yandex." in url_lower:
        return await parse_yandex(url)
    elif "music.youtube.com" in url_lower:
        if master_artists is None:
            print("ОШИБКА: для парсинга YouTube Music не передан мастер-лист артистов.")
            return None
        return await parse_youtube(url, master_artists=master_artists, debug=False)
    elif "vk.com/music" in url_lower or "boom.ru" in url_lower:
        return await parse_boom(url)
    else:
        # Если сервис не опознан, возвращаем None
        print(f"Не удалось распознать сервис для URL: {url}")
        return None