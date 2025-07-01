from datetime import datetime
import locale
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dateutil.relativedelta import relativedelta
from app.lexicon import EVENT_TYPE_EMOJI

def get_general_onboarding_keyboard(lexicon) -> InlineKeyboardMarkup:
    """
    Предлагает настроить или пропустить настройку общей мобильности.
    """

    builder = InlineKeyboardBuilder()
    builder.button(text=lexicon.get('setup_general_mobility'), callback_data="setup_general_mobility")
    builder.button(text=lexicon.get('skip_general_mobility'), callback_data="skip_general_mobility")
    builder.adjust(1)
    return builder.as_markup()

def get_artist_input_keyboard(lexicon, show_setup_mobility_button: bool = False) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для экрана ввода имени артиста.
    Включает кнопки "Импорт", "Настроить мобильность" (опционально) и "Отмена".
    """
    builder = InlineKeyboardBuilder()
    
    # Кнопка "Импортировать"
    builder.button(text=lexicon.get('import_artists'), callback_data="import_artists")
    
    # Опциональная кнопка "Настроить общую мобильность"
    if show_setup_mobility_button:
        builder.button(text=lexicon.get('general_mobility_settings'), callback_data="setup_general_mobility")
    
    # Кнопка "Отмена"
    builder.button(text=lexicon.get('cancel_button'), callback_data="cancel_add_to_fav")
    
    # Каждая кнопка в своем ряду
    builder.adjust(1)
    
    return builder.as_markup()

def get_cancel_artist_input_keyboard(lexicon) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с одной кнопкой "Отмена" для прерывания ввода имени артиста.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=lexicon.get('cancel_button'),
            callback_data="cancel_add_to_fav" # Используем тот же callback, что и для отмены всего процесса
        )
    )
    return builder.as_markup()

def get_mobility_type_choice_keyboard(lexicon) -> InlineKeyboardMarkup:
    """
    Предлагает использовать общие настройки мобильности или настроить для текущей подписки.
    """
    builder = InlineKeyboardBuilder()
    # --- ИЗМЕНЕНИЕ --- Текст заменен на вызов lexicon.get()
    builder.button(text=lexicon.get('use_general_mobility_button'), callback_data="use_general_mobility")
    builder.button(text=lexicon.get('setup_custom_mobility_button'), callback_data="setup_custom_mobility")
    builder.adjust(1)
    return builder.as_markup()


def get_add_more_or_finish_keyboard(lexicon, show_setup_mobility_button: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для цикла добавления подписок.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=lexicon.get('finish_button'), 
            callback_data="finish_adding_subscriptions"
        )
    )
    return builder.as_markup()

def found_artists_keyboard(artists, lexicon) -> InlineKeyboardMarkup:
    """
    Показывает найденных артистов для подписки.
    ИЗМЕНЕНИЕ: Использует ID артиста в callback_data.
    """
    builder = InlineKeyboardBuilder()
    for artist in artists:
        button_text = artist.name[:40] + '...' if len(artist.name) > 40 else artist.name
        builder.button(text=button_text, callback_data=f"subscribe_to_artist:{artist.artist_id}")
        
    builder.adjust(1)
    # --- ИЗМЕНЕНИЕ ---
    # Текст заменен на вызов lexicon.get(). Кнопка 'cancel_artist_search' теперь будет вести
    # не на начало флоу, а на отмену, что логичнее.
    builder.row(InlineKeyboardButton(text=lexicon.get('cancel_button'), callback_data="cancel_add_to_fav"))
    return builder.as_markup()