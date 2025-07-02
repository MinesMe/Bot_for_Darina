# app/keyboards.py

from datetime import datetime
import locale
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dateutil.relativedelta import relativedelta
from app.lexicon import (
    EVENT_TYPE_EMOJI,
    get_event_type_keys,
    get_event_type_display_name,
    get_event_type_storage_value
)

# --- КОНСТАНТЫ ---

TOP_COUNTRIES = ["Беларусь", "Россия", "Казахстан", "Грузия", "Узбекистан", "Сербия", "Таиланд", "ОАЭ"]

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





def get_home_city_selection_keyboard(top_cities: list, lexicon, back_callback_data: str = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in top_cities:
        builder.button(text=city, callback_data=f"select_home_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=lexicon.get('find_another_city'), callback_data="search_for_home_city"))
    # --- НОВОЕ: Добавляем кнопку "Назад", если передан callback ---
    if back_callback_data:
        builder.row(InlineKeyboardButton(text=lexicon.get('back_button'), callback_data=back_callback_data))
    # -----------------------------------------------------------
    return builder.as_markup()



def get_event_type_selection_keyboard(lexicon, selected_types: list = None) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру выбора типов событий с кнопкой "Выбрать все".
    - `selected_types` ожидает список русских названий.
    """
    if selected_types is None:
        selected_types = []
    builder = InlineKeyboardBuilder()

    event_keys = get_event_type_keys()
    all_event_storage_values = [get_event_type_storage_value(key) for key in event_keys]

    # --- ИЗМЕНЕНИЕ 1: Добавляем кнопку "Выбрать/Снять все" ---
    # Проверяем, все ли типы уже выбраны
    all_selected = set(all_event_storage_values) == set(selected_types)
    
    # Текст кнопки меняется в зависимости от состояния
    select_all_text = lexicon.get('unselect_all_button') if all_selected else lexicon.get('select_all_button')
    
    # Добавляем кнопку в первую очередь
    
    # --- КОНЕЦ ИЗМЕНЕНИЯ 1 ---

    builder.button(text=select_all_text, callback_data="toggle_event_type:all")

    # Генерируем кнопки для каждого типа событий (этот код у вас уже есть)
    for key in event_keys:
        display_name = get_event_type_display_name(key, lexicon.lang_code)
        storage_value = get_event_type_storage_value(key)
        text = f"✅ {display_name}" if storage_value in selected_types else f"⬜️ {display_name}"
        builder.button(text=text, callback_data=f"toggle_event_type:{storage_value}")

    
    # --- ИЗМЕНЕНИЕ 2: Адаптируем расположение кнопок ---
    # Первая кнопка ("Выбрать все") будет в своем ряду, остальные по 2 в ряду.
    builder.adjust(1,2)
    # --- КОНЕЦ ИЗМЕНЕНИЯ 2 ---
    
    builder.row(InlineKeyboardButton(text=lexicon.get('finish_button'), callback_data="finish_preferences_selection:True"))
    return builder.as_markup()


def get_back_to_city_selection_keyboard(lexicon, back_callback_data: str = "back_to_city_selection") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    # --- ИЗМЕНЕНИЕ: Используем переданный callback ---
    builder.button(text=lexicon.get('back_button'), callback_data=back_callback_data)
    # --------------------------------------------------
    return builder.as_markup()

# --- НОВЫЕ И ПЕРЕРАБОТАННЫЕ КЛАВИАТУРЫ ДЛЯ ПОДПИСОК ---





    








def get_region_selection_keyboard(
    selected_regions: list,
    finish_callback: str,
    back_callback: str,
    search_callback: str, # <-- Новый параметр для поиска
    lexicon
) -> InlineKeyboardMarkup:
    """
    Универсальная клавиатура для выбора стран с топом, поиском и выбранными регионами.
    """
    builder = InlineKeyboardBuilder()

    # Собираем уникальный список стран для отображения: топ + уже выбранные
    countries_to_show = sorted(list(set(TOP_COUNTRIES + selected_regions)))

    for country in countries_to_show:
        text = f"✅ {country}" if country in selected_regions else f"⬜️ {country}"
        builder.button(text=text, callback_data=f"toggle_region:{country}")
    
    builder.adjust(2)

    # Добавляем кнопки управления
    builder.row(InlineKeyboardButton(text=lexicon.get('find_another_country'), callback_data=search_callback))
    builder.row(InlineKeyboardButton(text=lexicon.get('finish_button'), callback_data=finish_callback))
    builder.row(InlineKeyboardButton(text=lexicon.get('back_button'), callback_data=back_callback))

    return builder.as_markup()

def get_found_countries_keyboard(found_countries: list, lexicon, back_callback: str) -> InlineKeyboardMarkup:
    """Клавиатура для показа найденных стран."""
    builder = InlineKeyboardBuilder()
    for country in found_countries:
        # Используем тот же callback, что и на основном экране
        builder.button(text=country, callback_data=f"toggle_region:{country}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=lexicon.get('back_button'), callback_data=back_callback))
    return builder.as_markup()

def get_back_to_country_selection_keyboard(lexicon, back_callback: str) -> InlineKeyboardMarkup:
    """Клавиатура с одной кнопкой "Назад" для экрана поиска."""
    builder = InlineKeyboardBuilder()
    builder.button(text=lexicon.get('back_button'), callback_data=back_callback)
    return builder.as_markup()



def get_recommended_artists_keyboard(
    artists_data: list[dict], # <-- Ожидает список словарей
    lexicon,
    selected_artist_ids: set = None
) -> InlineKeyboardMarkup:
    # ...
    builder = InlineKeyboardBuilder()

    if selected_artist_ids is None:
        selected_artist_ids = set()

    for artist_dict in artists_data: # <-- итерируемся по словарям
        artist_id = artist_dict['artist_id']
        artist_name = artist_dict['name']
        display_name = artist_name.title()
        
        text = f"✅ {display_name}" if artist_id in selected_artist_ids else f"⬜️ {display_name}"
        builder.button(text=text, callback_data=f"rec_toggle:{artist_id}")

    builder.adjust(1)
    
    
    builder.row(
        InlineKeyboardButton(
            text=lexicon.get('finish_button'),
            callback_data="rec_finish"
        )
    )
        
    return builder.as_markup()

