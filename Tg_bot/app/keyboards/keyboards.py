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
    builder.row(InlineKeyboardButton(text=lexicon.get('find_another_city'), callback_data="search_for_home_city"))
    return builder.as_markup()



def get_event_type_selection_keyboard(lexicon, selected_types: list = None) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру выбора типов событий.
    - Текст на кнопке зависит от языка пользователя.
    - В callback_data всегда отправляется РУССКОЕ название.
    - `selected_types` теперь ожидает список русских названий.
    """
    if selected_types is None:
        selected_types = []
    builder = InlineKeyboardBuilder()

    # 1. Получаем список универсальных ключей ('concert', 'theater'...)
    event_keys = get_event_type_keys()

    # 2. Итерируемся по ключам, а не по названиям
    for key in event_keys:
        # 3. Получаем текст для отображения на языке пользователя
        display_name = get_event_type_display_name(key, lexicon.lang_code)

        # 4. Получаем значение для сохранения в БД (всегда русское)
        storage_value = get_event_type_storage_value(key)

        # 5. Проверяем, выбрано ли уже это значение
        text = f"✅ {display_name}" if storage_value in selected_types else f"⬜️ {display_name}"

        # 6. Создаем кнопку: текст для юзера, русское значение для хэндлера
        builder.button(text=text, callback_data=f"toggle_event_type:{storage_value}")

    builder.adjust(2)
    # Ваша кнопка "Готово" остается без изменений
    builder.row(InlineKeyboardButton(text=lexicon.get('finish_button'), callback_data="finish_preferences_selection:True"))
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
    back_callback: str,
    lexicon  # <--- Просто добавляем этот параметр
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
    builder.row(InlineKeyboardButton(text=lexicon.get('finish_button'), callback_data=finish_callback))  
    
    # ИЗМЕНЕНИЕ: Добавляем кнопку "Назад" с переданным callback_, вы правы. Прошу прощения, я усложнил иdata
    builder.row(InlineKeyboardButton(text=lexicon.get('back_button'), callback_data=back_callback))
    
    return builder.as_markup()



def get_recommended_artists_keyboard(
    artists_data: list[dict],
    lexicon,
    selected_artist_ids: set = None
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для выбора рекомендованных артистов.
    Кнопка "Готово" отображается всегда.
    """
    if selected_artist_ids is None:
        selected_artist_ids = set()
        
    builder = InlineKeyboardBuilder()

    for artist_dict in artists_data:
        artist_id = artist_dict['artist_id']
        artist_name = artist_dict['name']
        display_name = artist_name.title()
        
        text = f"✅ {display_name}" if artist_id in selected_artist_ids else f"⬜️ {display_name}"
        builder.button(text=text, callback_data=f"rec_toggle:{artist_id}")

    builder.adjust(1)
    
    # --- ИЗМЕНЕНИЕ: Убираем условие, кнопка "Готово" теперь есть всегда ---
    builder.row(
        InlineKeyboardButton(
            text=lexicon.get('finish_button'),
            callback_data="rec_finish"
        )
    )
        
    return builder.as_markup()

