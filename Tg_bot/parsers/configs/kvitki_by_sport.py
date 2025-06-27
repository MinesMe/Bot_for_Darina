CONFIG = {
    'site_name': 'Kvitki.by (Спорт)',
    'url': 'https://www.kvitki.by/rus/bileti/sport/',
    'event_type': 'Спорт',
    'country_name': 'Беларусь', # <-- ОБЯЗАТЕЛЬНОЕ ПОЛЕ
    'category_name': 'Музыка Playwright',
    'parsing_method': 'playwright_kvitki',
    # 'parsing_method': 'json',
    # 'json_regex': r'window\.concertsListEvents\s*=\s*(\[.*?\]);',
    # 'json_keys': {
    #     'title': 'title',
    #     'place': 'venueDescription',
    #     'time': 'localisedStartDate',
    #     'link': 'shortUrl'
    # }
}