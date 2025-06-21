# app/keyboards.py

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- КОНСТАНТЫ ---
EVENT_TYPES_RU = ["Концерт", "Театр", "Спорт", "Цирк", "Выставка", "Фестиваль"]
EVENT_TYPE_EMOJI = {
    "Концерт": "🎵", "Театр": "🎭", "Спорт": "🏅", "Цирк": "🎪",
    "Выставка": "🎨", "Фестиваль": "🎉",
}

# --- ОСНОВНЫЕ КЛАВИАТУРЫ ---
def get_main_menu_keyboard(lexicon) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=lexicon.get('main_menu_button_afisha')),
        KeyboardButton(text=lexicon.get('main_menu_button_subs'))
    )
    builder.row(
        KeyboardButton(text=lexicon.get('main_menu_button_profile')),
        KeyboardButton(text=lexicon.get('main_menu_button_search'))
    )
    return builder.as_markup(resize_keyboard=True)

def get_profile_keyboard(lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=lexicon.get('profile_button_location'), callback_data="change_location")
    builder.button(text=lexicon.get('profile_button_subs'), callback_data="show_my_subscriptions_from_profile")
    builder.adjust(1)
    return builder.as_markup()

# --- КЛАВИАТУРЫ ДЛЯ ОНБОРДИНГА ---
def get_country_selection_keyboard(countries: list, lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for country in countries:
        builder.button(text=country, callback_data=f"main_geo_settings:{country}")
    builder.adjust(2)
    return builder.as_markup()

def get_main_geo_settings(lexicon)-> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Настроить", callback_data=f"select_home_country"))
    builder.row(InlineKeyboardButton(text="Пропустить настройку", callback_data=f"finish_preferences_selection:{False}"))
    return builder.as_markup()

def get_home_city_selection_keyboard(top_cities: list, lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in top_cities:
        builder.button(text=city, callback_data=f"select_home_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔎 Найти другой город", callback_data="search_for_home_city"))
    return builder.as_markup()

def get_found_home_cities_keyboard(found_cities: list, lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in found_cities:
        builder.button(text=city, callback_data=f"select_home_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=lexicon.get('back_button'), callback_data="back_to_city_selection"))
    return builder.as_markup()

def get_event_type_selection_keyboard(lexicon, selected_types: list = None) -> InlineKeyboardMarkup:
    if selected_types is None: selected_types = []
    builder = InlineKeyboardBuilder()
    for event_type in EVENT_TYPES_RU:
        text = f"✅ {event_type}" if event_type in selected_types else f"⬜️ {event_type}"
        builder.button(text=text, callback_data=f"toggle_event_type:{event_type}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=lexicon.get('finish_button'), callback_data="finish_preferences_selection:{True}"))
    return builder.as_markup()

def get_back_to_city_selection_keyboard(lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=lexicon.get('back_button'), callback_data="back_to_city_selection")
    return builder.as_markup()

# --- НОВЫЕ И ПЕРЕРАБОТАННЫЕ КЛАВИАТУРЫ ДЛЯ ПОДПИСОК ---

def get_my_subscriptions_keyboard(items: list) -> InlineKeyboardMarkup:
    """
    Показывает список подписок для удаления и кнопку "Добавить/найти".
    """
    builder = InlineKeyboardBuilder()
    if items:
        for item in items:
            builder.button(text=f"❌ {item}", callback_data=f"unsubscribe:{item}")
        builder.adjust(1)
    builder.row(InlineKeyboardButton(text="➕ Добавить/найти исполнителя", callback_data="add_new_subscription"))
    return builder.as_markup()

def get_general_onboarding_keyboard() -> InlineKeyboardMarkup:
    """
    Предлагает настроить или пропустить настройку общей мобильности.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="👍 Да, настроить", callback_data="setup_general_mobility")
    builder.button(text="➡️ Пропустить", callback_data="skip_general_mobility")
    builder.adjust(1)
    return builder.as_markup()

def get_region_selection_keyboard(all_countries: list, selected_regions: list, for_general: bool = False) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура для выбора стран.
    В зависимости от флага for_general меняет callback для кнопки "Готово".
    """
    builder = InlineKeyboardBuilder()
    for country in all_countries:
        text = f"✅ {country}" if country in selected_regions else f"⬜️ {country}"
        builder.button(text=text, callback_data=f"toggle_region:{country}")
    builder.adjust(2)
    finish_callback = "finish_general_selection" if for_general else "finish_custom_selection"
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data=finish_callback))
    return builder.as_markup()

def get_add_sub_action_keyboard(show_setup_mobility_button: bool = False) -> InlineKeyboardMarkup:
    """
    Предлагает выбор: написать имя артиста вручную или импортировать.
    Может также включать кнопку настройки общей мобильности.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Написать артиста", callback_data="write_artist")
    builder.button(text="📥 Импортировать", callback_data="import_artists")
    builder.adjust(1)
    if show_setup_mobility_button:
        builder.row(InlineKeyboardButton(text="🛠️ Настроить общую мобильность", callback_data="setup_general_mobility"))
    return builder.as_markup()


def get_mobility_type_choice_keyboard() -> InlineKeyboardMarkup:
    """
    Предлагает использовать общие настройки мобильности или настроить для текущей подписки.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🌍 Использовать общие", callback_data="use_general_mobility")
    builder.button(text="⚙️ Настроить для этой подписки", callback_data="setup_custom_mobility")
    builder.adjust(1)
    return builder.as_markup()

def get_add_more_or_finish_keyboard(show_setup_mobility_button: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для цикла добавления подписок.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Добавить еще артиста", callback_data="write_artist")
    builder.button(text="📥 Импортировать еще", callback_data="import_artists")
    if show_setup_mobility_button:
         builder.row(InlineKeyboardButton(text="🛠️ Настроить общую мобильность", callback_data="setup_general_mobility"))
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="finish_adding_subscriptions"))
    return builder.as_markup()


# --- ОСТАЛЬНЫЕ КЛАВИАТУРЫ ---

def found_artists_keyboard(artists: list) -> InlineKeyboardMarkup:
    """
    Показывает найденных артистов для подписки.
    """
    builder = InlineKeyboardBuilder()
    for artist in artists:
        builder.button(text=f"{artist}", callback_data=f"subscribe_to_artist:{artist}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="cancel_artist_search"))
    return builder.as_markup()

def get_paginated_artists_keyboard(all_artists: list, selected_artists: set, page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    PAGE_SIZE = 5
    start, end = page * PAGE_SIZE, (page + 1) * PAGE_SIZE
    artists_on_page = all_artists[start:end]
    for artist in artists_on_page:
        text = f"✅ {artist}" if artist in selected_artists else f"⬜️ {artist}"
        builder.button(text=text, callback_data=f"toggle_artist_subscribe:{artist}")
    builder.adjust(1)
    total_pages = (len(all_artists) + PAGE_SIZE - 1) // PAGE_SIZE
    if total_pages > 1:
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"paginate_artists:{page - 1}"))
        pagination_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))
        if page < total_pages - 1:
            pagination_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"paginate_artists:{page + 1}"))
        builder.row(*pagination_buttons)
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="finish_artist_selection"))
    return builder.as_markup()

def get_categories_keyboard(categories: list = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    source_list = categories if categories else EVENT_TYPES_RU
    for category in source_list:
        emoji = EVENT_TYPE_EMOJI.get(category, "🔹")
        builder.button(text=f"{emoji} {category}", callback_data=f"category:{category}")
    builder.adjust(2)
    return builder.as_markup()

def get_cities_keyboard(cities: list, category: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in cities:
        builder.button(text=city, callback_data=f"city:{city}:{category}")
    builder.adjust(2)
    return builder.as_markup()

#---------- АФИША ----------

def get_afisha_settings()-> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Настроить", callback_data=f"afisha_main_geo_settings"))
    builder.row(InlineKeyboardButton(text="Пропустить настройку", callback_data=f"skip_afisha_main_geo"))
    return builder.as_markup()

def get_afisha_settings_type()-> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="По мои настройкам", callback_data=f"afisha_defautl_type_settings"))
    builder.row(InlineKeyboardButton(text="Другую", callback_data=f"afisha_another_type_settings"))
    return builder.as_markup()