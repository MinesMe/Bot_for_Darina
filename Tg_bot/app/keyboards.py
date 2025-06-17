from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


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

def get_country_selection_keyboard(all_countries: list, lexicon, is_multiselect: bool = False,
                                   home_country: str | None = None,
                                   selected_countries: list = None) -> InlineKeyboardMarkup:
    if selected_countries is None:
        selected_countries = []
    builder = InlineKeyboardBuilder()

    for country in all_countries:
        if is_multiselect:
            country_text = f"📍 {country}" if country == home_country else country
            text = f"✅ {country_text}" if country in selected_countries else f"⬜️ {country_text}"
            callback_data = f"toggle_country:{country}"
        else:
            text = country
            callback_data = f"select_country:{country}"
        builder.button(text=text, callback_data=callback_data)

    builder.adjust(2)

    if is_multiselect:
        builder.row(InlineKeyboardButton(text=lexicon.get('finish_button'), callback_data="finish_country_selection"))

    return builder.as_markup()

def get_city_selection_keyboard(top_cities: list, lexicon, selected_cities: list = None) -> InlineKeyboardMarkup:
    if selected_cities is None:
        selected_cities = []
    builder = InlineKeyboardBuilder()

    for city in top_cities:
        text = f"✅ {city}" if city in selected_cities else f"⬜️ {city}"
        builder.button(text=text, callback_data=f"toggle_city:{city}")
    builder.adjust(3)

    builder.row(
        InlineKeyboardButton(text="🔎 Найти другой город", callback_data="search_for_city")
    )
    builder.row(
        InlineKeyboardButton(text=lexicon.get('finish_button'), callback_data="finish_city_selection")
    )
    return builder.as_markup()

def get_found_cities_keyboard(found_cities: list, lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in found_cities:
        builder.button(text=f"✅ {city}", callback_data=f"toggle_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=lexicon.get('back_button'), callback_data="back_to_city_selection"))
    return builder.as_markup()

# --- НОВАЯ КЛАВИАТУРА ---
def get_back_to_city_selection_keyboard(lexicon) -> InlineKeyboardMarkup:
    """Клавиатура с одной кнопкой 'Назад'."""
    builder = InlineKeyboardBuilder()
    builder.button(text=lexicon.get('back_button'), callback_data="back_to_city_selection")
    return builder.as_markup()

def get_categories_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎵 Концерты", callback_data="category:Концерт")
    builder.button(text="🎭 Театр", callback_data="category:Театр")
    builder.button(text="🏅 Спорт", callback_data="category:Спорт")
    builder.button(text="🎪 Цирк", callback_data="category:Цирк")
    builder.button(text="🎨 Выставки", callback_data="category:Выставка")
    builder.button(text="🎉 Фестивали", callback_data="category:Фестиваль")
    builder.adjust(2)
    return builder.as_markup()

def get_cities_keyboard(cities: list, category: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in cities:
        builder.button(text=city, callback_data=f"city:{city}:{category}")
    builder.adjust(2)
    return builder.as_markup()

def manage_subscriptions_keyboard(items: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if items:
        for item in items:
            builder.button(text=f"❌ {item}", callback_data=f"unsubscribe:{item}")
        builder.adjust(1)
    builder.row(InlineKeyboardButton(text="➕ Добавить подписку", callback_data="add_subscription"))
    return builder.as_markup()

def found_artists_keyboard(artists: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for artist in artists:
        builder.button(text=f"✅ {artist}", callback_data=f"subscribe_to_artist:{artist}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="cancel_subscription"))
    return builder.as_markup()