# --- START OF FILE parsers/configs/liveball_by_sport.py ---

CONFIG = {
    'site_name': 'Liveball.by (Спорт)',
    'url': 'https://liveball.my/matches/',
    'event_type': 'Спорт',
    'parsing_method': 'bs4_liveball',
    'selectors': {
        # Селекторы для списка матчей
        'list_item': 'a.match_a',
        'list_score_indicator': 'div.score',

        # Селекторы для страницы детального матча
        'detail_main_info_block': 'div#main_info',
        'detail_league_tour': 'div.league_tour a',
        'detail_vs_block': 'div.info_vs',
        'detail_left_team': 'div.l_team a span',
        'detail_right_team': 'div.r_team a span',
        'detail_time': 'span.time_score',
        # Селекторы для места убраны, т.к. мы его не парсим
    }
}