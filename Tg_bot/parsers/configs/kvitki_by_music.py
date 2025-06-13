CONFIG = {
    'site_name': 'Kvitki.by (Музыка)',
    'url': 'https://www.kvitki.by/rus/bileti/muzyka/',
    'event_type': 'Концерт',
    'parsing_method': 'json',
    'json_regex': r'window\.concertsListEvents\s*=\s*(\[.*?\]);',
    'json_keys': {
        'title': 'title',
        'place': 'venueDescription',
        'time': 'localisedStartDate',
        'link': 'shortUrl'
    }
}