CONFIG = {
    'site_name': 'Kvitki.by (КЗ Минск)',
    'url': 'https://www.kvitki.by/rus/bileti/kz-minsk/',
    'event_type': 'Концерт',
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