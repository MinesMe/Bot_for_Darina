CONFIG = {
    'site_name': 'Kvitki.by (Большой Театр)',
    'url': 'https://www.kvitki.by/rus/bileti/bolshoj-teatr/',
    'country_name': 'Беларусь', # <-- ОБЯЗАТЕЛЬНОЕ ПОЛЕ
    'category_name': 'Музыка Playwright',
    'event_type': 'Театр',
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