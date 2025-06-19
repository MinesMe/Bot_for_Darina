# app/keyboards.py

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from .database.models import MobilityTemplate

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
    builder.button(text=lexicon.get('profile_button_subs'), callback_data="open_subscriptions")
    builder.adjust(1)
    return builder.as_markup()

# --- КЛАВИАТУРЫ ДЛЯ ОНБОРДИНГА ---
def get_country_selection_keyboard(countries: list, lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for country in countries:
        builder.button(text=country, callback_data=f"select_home_country:{country}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip_onboarding"))
    return builder.as_markup()

def get_home_city_selection_keyboard(top_cities: list, lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in top_cities:
        builder.button(text=city, callback_data=f"select_home_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔎 Найти другой город", callback_data="search_for_home_city"))
    builder.row(InlineKeyboardButton(text="➡️ Пропустить этот шаг", callback_data="skip_city_selection"))
    return builder.as_markup()

def get_found_home_cities_keyboard(found_cities: list, lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in found_cities:
        builder.button(text=city, callback_data=f"select_home_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=lexicon.get('back_button'), callback_data="back_to_city_selection"))
    return builder.as_markup()

def get_setup_filter_preference_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👍 Да, настроить", callback_data="setup_filters_yes")
    builder.button(text="👎 Нет, спасибо", callback_data="setup_filters_no")
    return builder.as_markup()

def get_event_type_selection_keyboard(lexicon, selected_types: list = None) -> InlineKeyboardMarkup:
    if selected_types is None: selected_types = []
    builder = InlineKeyboardBuilder()
    for event_type in EVENT_TYPES_RU:
        text = f"✅ {event_type}" if event_type in selected_types else f"⬜️ {event_type}"
        builder.button(text=text, callback_data=f"toggle_event_type:{event_type}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=lexicon.get('finish_button'), callback_data="finish_preferences_selection"))
    return builder.as_markup()

def get_back_to_city_selection_keyboard(lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=lexicon.get('back_button'), callback_data="back_to_city_selection")
    return builder.as_markup()

# --- КЛАВИАТУРЫ ДЛЯ МОБИЛЬНОСТИ И ПОДПИСОК ---
def get_mobility_onboarding_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👍 Да, настроить", callback_data="start_mobility_setup")
    builder.button(text="➡️ Пропустить", callback_data="skip_mobility_setup")
    return builder.as_markup()

def get_region_selection_keyboard(all_countries: list, selected_regions: list, for_template: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for country in all_countries:
        text = f"✅ {country}" if country in selected_regions else f"⬜️ {country}"
        callback_data = f"toggle_region:{country}"
        builder.button(text=text, callback_data=callback_data)
    builder.adjust(2)
    finish_callback = "finish_template_creation" if for_template else "finish_custom_region_selection"
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data=finish_callback))
    return builder.as_markup()

def get_mobility_choice_keyboard(templates: list[MobilityTemplate]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if templates:
        builder.button(text="📝 Использовать шаблон", callback_data="choose_template")
    builder.button(text="⚙️ Настроить регионы вручную", callback_data="setup_custom_regions")
    builder.adjust(1)
    return builder.as_markup()

def get_template_selection_keyboard(templates: list[MobilityTemplate]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for template in templates:
        builder.button(text=f"📄 {template.template_name}", callback_data=f"select_template:{template.template_id}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_mobility_choice"))
    return builder.as_markup()

def manage_subscriptions_keyboard(items: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if items:
        for item in items:
            builder.button(text=f"❌ {item}", callback_data=f"unsubscribe:{item}")
        builder.adjust(1)
    builder.row(
        InlineKeyboardButton(text="➕ Добавить подписку", callback_data="add_subscription_manual"),
        InlineKeyboardButton(text="📥 Импорт из плейлиста", callback_data="import_playlist")
    )
    builder.row(InlineKeyboardButton(text="🗺️ Управление шаблонами мобильности", callback_data="manage_mobility_templates"))
    return builder.as_markup()

# --- НОВЫЕ КЛАВИАТУРЫ ДЛЯ УПРАВЛЕНИЯ ШАБЛОНАМИ ---
def get_templates_management_keyboard(templates: list[MobilityTemplate]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if templates:
        builder.button(text="🗑️ Удалить шаблон", callback_data="delete_template_start")
    builder.button(text="➕ Создать новый шаблон", callback_data="create_template_start")
    builder.row(InlineKeyboardButton(text="⬅️ Назад к подпискам", callback_data="back_to_subscriptions"))
    return builder.as_markup()

def get_template_deletion_keyboard(templates: list[MobilityTemplate]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for template in templates:
        builder.button(text=f"❌ {template.template_name}", callback_data=f"delete_template_confirm:{template.template_id}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="manage_mobility_templates"))
    return builder.as_markup()

# --- ОСТАЛЬНЫЕ КЛАВИАТУРЫ ---
def found_artists_keyboard(artists: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for artist in artists:
        builder.button(text=f"✅ {artist}", callback_data=f"subscribe_to_artist:{artist}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="cancel_subscription"))
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