# --- START OF FILE parsers/configs/liveball_by_basketball.py ---

CONFIG = {
    'site_name': 'Liveball.by (Баскетбол)', # <-- ИЗМЕНЕНИЕ
    'url': 'https://liveball.my/basketball/matches/', # <-- ИЗМЕНЕНИЕ
    'event_type': 'Спорт', # Оставляем "Спорт", т.к. это общая категория
    'parsing_method': 'bs4_liveball',
    'selectors': {
        # Все селекторы остаются точно такими же, как для футбола
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