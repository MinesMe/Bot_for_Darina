from datetime import datetime
import locale
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dateutil.relativedelta import relativedelta
from app.lexicon import EVENT_TYPE_EMOJI

def get_favorites_list_keyboard(favorites: list, lexicon) -> InlineKeyboardMarkup:
    """
    Генерирует клавиатуру со списком избранных артистов.
    Каждый артист - это кнопка для перехода в меню управления.
    """
    builder = InlineKeyboardBuilder()
    
    # Создаем кнопки для каждого избранного артиста
    if favorites:
        for fav in favorites:
            # Обрезаем длинные названия, чтобы избежать ошибки Telegram
            button_text = fav.name[:40] + '...' if len(fav.name) > 40 else fav.name
            builder.button(text=f"⭐ {button_text}", callback_data=f"view_favorite:{fav.artist_id}")
        
        # Располагаем каждую кнопку с артистом на новой строке
        builder.adjust(1)
    
    # Кнопка "Добавить" находится в другом разделе ("Найти/добавить артиста")
    # Кнопка "Настроить мобильность" находится глубже, в меню конкретного артиста
    # Поэтому здесь больше нет никаких кнопок действий.
    
    return builder.as_markup()

def get_single_favorite_manage_keyboard(artist_id: int, lexicon) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для управления одним конкретным избранным артистом.
    """
    builder = InlineKeyboardBuilder()
    
    # ИЗМЕНЕНИЕ: Меняем текст кнопки и ее callback_data для ясности
    builder.button(
        text=lexicon.get('favorite_edit_regions_button'),
        callback_data=f"edit_fav_regions:{artist_id}"
    )
    builder.button(
        text=lexicon.get('favorites_remove_button'),
        callback_data=f"delete_favorite:{artist_id}"
    )
    
    builder.adjust(1)
    
    builder.row(
        InlineKeyboardButton(
            text=lexicon.get('back_to_favorites_list_button'),
            callback_data="back_to_favorites_list"
        )
    )
    return builder.as_markup()