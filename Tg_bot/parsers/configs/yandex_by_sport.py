# --- START OF FILE parsers/configs/yandex_by_sport.py ---
CONFIG = {
    'site_name': 'Yandex.Afisha (Спорт)',
    'url': 'https://afisha.yandex.ru/moscow/sport',
    'country_name': 'Россия',           # <-- ОБЯЗАТЕЛЬНОЕ ПОЛЕ
    'city_name': 'Москва',
    'event_type': 'Спорт',
    'period': 365,
    'parsing_method': 'selenium_yandex', # Уникальный метод для этого парсера
}