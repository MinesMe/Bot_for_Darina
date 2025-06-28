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

def get_add_sub_action_keyboard(lexicon, show_setup_mobility_button: bool = False ) -> InlineKeyboardMarkup:
    """
    Предлагает выбор: написать имя артиста вручную или импортировать.
    Может также включать кнопку настройки общей мобильности.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=lexicon.get('write_artist'), callback_data="write_artist")
    builder.button(text=lexicon.get('import_artists'), callback_data="import_artists")
    builder.adjust(1)
    if show_setup_mobility_button:
        builder.row(InlineKeyboardButton(text=lexicon.get('general_mobility_settings'), callback_data="setup_general_mobility"))
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
    # --- ИЗМЕНЕНИЕ --- Текст заменен на вызов lexicon.get()
    builder.button(text=lexicon.get('add_another_artist_button'), callback_data="write_artist")
    builder.button(text=lexicon.get('import_more_button'), callback_data="import_artists")
    if show_setup_mobility_button:
         # --- ИЗМЕНЕНИЕ --- Текст заменен на вызов lexicon.get()
         builder.row(InlineKeyboardButton(text=lexicon.get('general_mobility_settings'), callback_data="setup_general_mobility"))
    # --- ИЗМЕНЕНИЕ --- Текст заменен на вызов lexicon.get(), использован существующий ключ
    builder.row(InlineKeyboardButton(text=lexicon.get('finish_button'), callback_data="finish_adding_subscriptions"))
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
    # --- ИЗМЕНЕНИЕ --- Текст заменен на вызов lexicon.get()
    builder.row(InlineKeyboardButton(text=lexicon.get('cancel_button'), callback_data="cancel_artist_search"))
    return builder.as_markup()