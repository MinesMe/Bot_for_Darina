# --- START OF FILE parsers/configs/__init__.py ---

# ... (все старые импорты для kvitki и liveball) ...
from .kvitki_by_music import CONFIG as kvitki_by_music_config
from .kvitki_by_theatre import CONFIG as kvitki_by_theatre_config
from .kvitki_by_bolshoi_theatre import CONFIG as kvitki_by_bolshoi_theatre_config
from .kvitki_by_circus import CONFIG as kvitki_by_circus_config
from .kvitki_by_sport import CONFIG as kvitki_by_sport_config
from .kvitki_by_kz_minsk import CONFIG as kvitki_by_kz_minsk_config
from .bezkassira_by_sport import CONFIG as bezkassira_by_sport_config
from .liveball_by_sport import CONFIG as liveball_by_sport_config
from .liveball_by_basketball import CONFIG as liveball_by_basketball_config
from .liveball_by_hockey import CONFIG as liveball_by_hockey_config

# --- НОВОЕ: Добавляем импорты для Яндекса ---
from .yandex_by_sport import CONFIG as yandex_by_sport_config
from .yandex_by_festival import CONFIG as yandex_by_festival_config
from .yandex_by_art import CONFIG as yandex_by_art_config
from .yandex_by_theatre import CONFIG as yandex_by_theatre_config
from .yandex_by_cinema import CONFIG as yandex_by_cinema_config
from .yandex_by_concert import CONFIG as yandex_by_concert_config


ALL_CONFIGS = [
    # ... (все старые конфиги) ...
    kvitki_by_music_config,
    kvitki_by_theatre_config,
    kvitki_by_bolshoi_theatre_config,
    kvitki_by_circus_config,
    kvitki_by_sport_config,
    kvitki_by_kz_minsk_config,
    # bezkassira_by_sport_config,
    # liveball_by_sport_config,
    # liveball_by_basketball_config,
    # liveball_by_hockey_config,

    # --- НОВОЕ: Добавляем конфиги Яндекса в общий список ---
    # yandex_by_sport_config,
    # yandex_by_festival_config,
    # yandex_by_art_config,
    # yandex_by_theatre_config,
    # yandex_by_cinema_config,
    # yandex_by_concert_config,
]