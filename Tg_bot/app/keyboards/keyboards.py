# app/keyboards.py

from datetime import datetime
import locale
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dateutil.relativedelta import relativedelta
from app.lexicon import EVENT_TYPE_EMOJI

# --- КОНСТАНТЫ ---



# --- ОСНОВНЫЕ КЛАВИАТУРЫ ---
def get_main_menu_keyboard(lexicon) -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text=lexicon.get('main_menu_button_afisha')),
        KeyboardButton(text=lexicon.get('main_menu_button_subs'))
    )
    builder.row(
        KeyboardButton(text=lexicon.get('main_menu_button_profile')),
        KeyboardButton(text=lexicon.get('main_menu_button_favorites')),
    )
    return builder.as_markup(resize_keyboard=True)



# --- КЛАВИАТУРЫ ДЛЯ ОНБОРДИНГА ---





def get_home_city_selection_keyboard(top_cities: list, lexicon) -> InlineKeyboardMarkup: 
    builder = InlineKeyboardBuilder()
    for city in top_cities:
        builder.button(text=city, callback_data=f"select_home_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔎 Найти другой город", callback_data="search_for_home_city"))
    return builder.as_markup()



def get_event_type_selection_keyboard(lexicon, selected_types: list = None) -> InlineKeyboardMarkup:
    if selected_types is None: selected_types = []
    builder = InlineKeyboardBuilder()
    for event_type in lexicon.EVENT_TYPES:
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





    








def get_region_selection_keyboard(
    all_countries: list, 
    selected_regions: list, 
    finish_callback: str,
    back_callback: str  # <--- Просто добавляем этот параметр
) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура для выбора стран.
    Принимает finish_callback для кнопки 'Готово' и back_callback для кнопки 'Назад'.
    """
    builder = InlineKeyboardBuilder()
    for country in all_countries:
        text = f"✅ {country}" if country in selected_regions else f"⬜️ {country}"
        builder.button(text=text, callback_data=f"toggle_region:{country}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data=finish_callback))  
    
    # ИЗМЕНЕНИЕ: Добавляем кнопку "Назад" с переданным callback_, вы правы. Прошу прощения, я усложнил иdata
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=back_callback))
    
    return builder.as_markup()










# --- ОСТАЛЬНЫЕ КЛАВИАТУРЫ ---



# def get_paginated_artists_keyboard(all_artists: list, selected_artists: set, page: int = 0) -> InlineKeyboardMarkup:
#     builder = InlineKeyboardBuilder()
#     PAGE_SIZE = 5
#     start, end = page * PAGE_SIZE, (page + 1) * PAGE_SIZE
#     artists_on_page = all_artists[start:end]
#     for artist in artists_on_page:
#         text = f"✅ {artist}" if artist in selected_artists else f"⬜️ {artist}"
#         builder.button(text=text, callback_data=f"toggle_artist_subscribe:{artist}")
#     builder.adjust(1)
#     total_pages = (len(all_artists) + PAGE_SIZE - 1) // PAGE_SIZE
#     if total_pages > 1:
#         pagination_buttons = []
#         if page > 0:
#             pagination_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"paginate_artists:{page - 1}"))
#         pagination_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))
#         if page < total_pages - 1:
#             pagination_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"paginate_artists:{page + 1}"))
#         builder.row(*pagination_buttons)
#     builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="finish_artist_selection"))
#     return builder.as_markup()


# def get_cities_keyboard(cities: list, category: str) -> InlineKeyboardMarkup:
#     builder = InlineKeyboardBuilder()
#     for city in cities:
#         builder.button(text=city, callback_data=f"city:{city}:{category}")
#     builder.adjust(2)
#     return builder.as_markup()

#---------- АФИША ----------

# def get_afisha_settings()-> InlineKeyboardMarkup:
#     builder = InlineKeyboardBuilder()
#     builder.row(InlineKeyboardButton(text="Настроить", callback_data=f"afisha_main_geo_settings"))
#     builder.row(InlineKeyboardButton(text="Пропустить настройку", callback_data=f"skip_afisha_main_geo"))
#     return builder.as_markup()

# def get_afisha_settings_type()-> InlineKeyboardMarkup:
#     builder = InlineKeyboardBuilder()
#     builder.row(InlineKeyboardButton(text="По мои настройкам", callback_data=f"afisha_defautl_type_settings"))
#     builder.row(InlineKeyboardButton(text="Другую", callback_data=f"afisha_another_type_settings"))
#     return builder.as_markup()









# --- НОВЫЙ БЛОК: Клавиатуры для раздела "Избранное" ---

# def get_favorites_menu_keyboard( favorites: list, lexicon) -> InlineKeyboardMarkup:
#     """Генерирует клавиатуру для главного меню 'Избранное'."""
#     builder = InlineKeyboardBuilder()
    
#     if favorites:
#         for fav in favorites:
#             # Обрезаем текст кнопки, чтобы избежать ошибки Telegram
#             button_text = fav.name[:40] + '...' if len(fav.name) > 40 else fav.name
#             builder.button(text=f"⭐ {button_text}", callback_data=f"view_favorite:{fav.artist_id}")
#         builder.adjust(1)
    
#     # Кнопка "Добавить" переехала в другой модуль.
#     # Кнопка "Настроить мобильность" теперь в меню управления конкретным артистом.
    
#     return builder.as_markup()





