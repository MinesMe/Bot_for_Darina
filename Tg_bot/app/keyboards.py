from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🗓 Афиша"),
        KeyboardButton(text="⭐ Мои подписки")
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки"),
        KeyboardButton(text="🔎 Поиск")
    )
    return builder.as_markup(resize_keyboard=True)

def get_country_selection_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🇧🇾 Беларусь", callback_data="select_country:belarus")
    return builder.as_markup()

def get_region_selection_keyboard(all_regions: list, selected_regions: list = None) -> InlineKeyboardMarkup:
    if selected_regions is None:
        selected_regions = []
    builder = InlineKeyboardBuilder()
    for region in all_regions:
        text = f"✅ {region}" if region in selected_regions else f"⬜️ {region}"
        builder.button(text=text, callback_data=f"toggle_region:{region}")
    builder.adjust(2)
    if selected_regions:
        builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="finish_region_selection"))
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