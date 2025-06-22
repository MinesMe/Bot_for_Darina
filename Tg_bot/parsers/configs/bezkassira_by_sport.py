# --- START OF FILE parsers/configs/bezkassira_by_sport.py ---

CONFIG = {
    'site_name': 'Bezkassira.by (Спорт)',
    'url': 'https://bezkassira.by/events/sport_event-minsk/',
    'event_type': 'Спорт',
    'parsing_method': 'bs4_bezkassira', # Уникальное имя для нового метода
    'selectors': {
        'event_card': 'div.thumbnail',  # <--- ГЛАВНОЕ ИЗМЕНЕНИЕ
        'caption': 'div.caption',       # Блок с названием и ссылкой
        'title': 'a',                   # Название внутри caption
        'link': 'a',                    # Ссылка внутри caption
        'date': 'div.date',             # Дата
        'place': 'small.hint'           # Место
    }
}