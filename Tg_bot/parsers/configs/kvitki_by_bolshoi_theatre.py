CONFIG = {
    'site_name': 'Kvitki.by (Большой Театр)',
    'url': 'https://www.kvitki.by/rus/bileti/bolshoj-teatr/',
    'event_type': 'Театр',
    'parsing_method': 'json',
    'json_regex': r'window\.concertsListEvents\s*=\s*(\[.*?\]);',
    'json_keys': {
        'title': 'title',
        'place': 'venueDescription',
        'time': 'localisedStartDate',
        'link': 'shortUrl'
    }
}