from datetime import datetime
import locale
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dateutil.relativedelta import relativedelta
from app.lexicon import EVENT_TYPE_EMOJI


def get_favorites_list_keyboard(favorites: list, lexicon, show_back_button: bool = False) -> InlineKeyboardMarkup:
    """
    Генерирует клавиатуру со списком избранных артистов.
    Может включать кнопку "Назад в профиль".
    """
    builder = InlineKeyboardBuilder()
    
    if favorites:
        for fav in favorites:
            button_text = fav.name[:40] + '...' if len(fav.name) > 40 else fav.name
            builder.button(text=f"⭐ {button_text}", callback_data=f"view_favorite:{fav.artist_id}")
        builder.adjust(1)
    
    # --- НОВОЕ: Условное добавление кнопки "Назад" ---
    if show_back_button:
        # Используем существующий callback "back_to_profile", который уже обрабатывается в profile.py
        builder.row(
            InlineKeyboardButton(
                text=lexicon.get('back_to_profile'), 
                callback_data="back_to_profile"
            )
        )
    # --- КОНЕЦ НОВОГО ---
    
    return builder.as_markup()

def get_single_favorite_manage_keyboard(artist_id: int, lexicon) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для управления одним конкретным избранным артистом.
    """
    builder = InlineKeyboardBuilder()
    # --- НОВАЯ КНОПКА ---
    builder.button(
        text=lexicon.get('favorite_view_events_button'),
        callback_data=f"view_events_for_favorite:{artist_id}"
    )
    # --- КОНЕЦ НОВОЙ КНОПКИ ---
    
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