# --- START OF FILE parsers/configs/liveball_by_hockey.py ---

CONFIG = {
    'site_name': 'Liveball.by (Хоккей)', # <-- ИЗМЕНЕНИЕ
    'url': 'https://liveball.my/hockey/matches/', # <-- ИЗМЕНЕНИЕ
    'event_type': 'Спорт', # Оставляем "Спорт"
    'parsing_method': 'bs4_liveball',
    'selectors': {
        # Селекторы полностью идентичны
        'list_item': 'a.match_a',
        'list_score_indicator': 'div.score',
        'detail_main_info_block': 'div#main_info',
        'detail_league_tour': 'div.league_tour a',
        'detail_vs_block': 'div.info_vs',
        'detail_left_team': 'div.l_team a span',
        'detail_right_team': 'div.r_team a span',
        'detail_time': 'span.time_score',
    }
}