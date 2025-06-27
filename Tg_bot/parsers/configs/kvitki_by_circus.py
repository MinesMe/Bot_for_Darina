CONFIG = {
    'site_name': 'Kvitki.by (Цирк)',
    'url': 'https://www.kvitki.by/rus/bileti/cirk/',
    'event_type': 'Цирк',
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