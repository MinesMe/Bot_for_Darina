# --- START OF FILE parsers/configs/yandex_by_cinema.py ---
CONFIG = {
    'site_name': 'Yandex.Afisha (Кино)',
    'url': 'https://afisha.yandex.ru/moscow/cinema',
    'country_name': 'Россия',           # <-- ОБЯЗАТЕЛЬНОЕ ПОЛЕ
    'city_name': 'Москва',
    'event_type': 'Кино', # Можно добавить новый тип, если нужно
    'period': 30, # Для кино нет смысла смотреть на год вперед
    'parsing_method': 'selenium_yandex',
}