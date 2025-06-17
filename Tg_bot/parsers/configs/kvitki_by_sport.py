CONFIG = {
    'site_name': 'Kvitki.by (Спорт)',
    'url': 'https://www.kvitki.by/rus/bileti/sport/',
    'event_type': 'Спорт',
    'parsing_method': 'json',
    'json_regex': r'window\.concertsListEvents\s*=\s*(\[.*?\]);',
    'json_keys': {
        'title': 'title',
        'place': 'venueDescription',
        'time': 'localisedStartDate',
        'link': 'shortUrl'
    }
}