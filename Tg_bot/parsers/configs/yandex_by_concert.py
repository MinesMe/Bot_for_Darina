# --- START OF FILE parsers/configs/yandex_by_concert.py ---
CONFIG = {
    'site_name': 'Yandex.Afisha (Концерты)',
    'url': 'https://afisha.yandex.ru/moscow/concert',
    'country_name': 'Россия',           # <-- ОБЯЗАТЕЛЬНОЕ ПОЛЕ
    'city_name': 'Москва',
    'event_type': 'Концерт',
    'period': 365,
    'parsing_method': 'selenium_yandex',
}