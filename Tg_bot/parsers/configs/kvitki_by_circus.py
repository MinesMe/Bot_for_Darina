CONFIG = {
    'site_name': 'Kvitki.by (Цирк)',
    'url': 'https://www.kvitki.by/rus/bileti/cirk/',
    'event_type': 'Цирк',
    'parsing_method': 'json',
    'json_regex': r'window\.concertsListEvents\s*=\s*(\[.*?\]);',
    'json_keys': {
        'title': 'title',
        'place': 'venueDescription',
        'time': 'localisedStartDate',
        'link': 'shortUrl'
    }
}