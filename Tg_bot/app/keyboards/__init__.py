from .profile_kb import get_profile_keyboard,get_manage_subscriptions_keyboard,get_edit_country_keyboard,get_edit_city_keyboard,get_edit_event_type_keyboard,get_edit_found_cities_keyboard
from .keyboards import get_main_menu_keyboard,get_home_city_selection_keyboard,get_event_type_selection_keyboard,get_back_to_city_selection_keyboard,get_region_selection_keyboard,get_recommended_artists_keyboard
from .onboarding_kb import get_country_selection_keyboard,get_main_geo_settings,get_found_home_cities_keyboard,get_single_subscription_manage_keyboard
from .subscriptions_kb import get_general_onboarding_keyboard, get_add_sub_action_keyboard,get_mobility_type_choice_keyboard,get_add_more_or_finish_keyboard,found_artists_keyboard
from .afisha_kb import get_afisha_actions_keyboard,get_date_period_keyboard,get_month_choice_keyboard,get_filter_type_choice_keyboard
from .favorities_kb import get_favorites_list_keyboard,get_single_favorite_manage_keyboard

# (Опционально) Можно определить __all__, чтобы контролировать,
# что будет импортировано через "from keyboards import *"
__all__ = [
    # afisha_kb
    'get_afisha_actions_keyboard',
    'get_date_period_keyboard',
    'get_filter_type_choice_keyboard',
    'get_month_choice_keyboard',

    # favorities_kb
    'get_favorites_list_keyboard',
    'get_single_favorite_manage_keyboard',

    # keyboards (основные)
    'get_back_to_city_selection_keyboard',
    'get_event_type_selection_keyboard',
    'get_home_city_selection_keyboard',
    'get_main_menu_keyboard',
    'get_region_selection_keyboard',
    "get_recommended_artists_keyboard"

    # onboarding_kb
    'get_country_selection_keyboard',
    'get_found_home_cities_keyboard',
    'get_main_geo_settings',
    'get_single_subscription_manage_keyboard',

    # profile_kb
    'get_edit_city_keyboard',
    'get_edit_country_keyboard',
    'get_edit_event_type_keyboard',
    'get_edit_found_cities_keyboard',
    'get_manage_subscriptions_keyboard',
    'get_profile_keyboard',

    # subscriptions_kb
    'found_artists_keyboard',
    'get_add_more_or_finish_keyboard',
    'get_add_sub_action_keyboard',
    'get_general_onboarding_keyboard',
    'get_mobility_type_choice_keyboard',
]