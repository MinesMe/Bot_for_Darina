from datetime import datetime
import locale
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dateutil.relativedelta import relativedelta
from app.lexicon import EVENT_TYPE_EMOJI

def get_general_onboarding_keyboard() -> InlineKeyboardMarkup:
    """
    Предлагает настроить или пропустить настройку общей мобильности.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="👍 Да, настроить", callback_data="setup_general_mobility")
    builder.button(text="➡️ Пропустить", callback_data="skip_general_mobility")
    builder.adjust(1)
    return builder.as_markup()

def get_add_sub_action_keyboard(show_setup_mobility_button: bool = False) -> InlineKeyboardMarkup:
    """
    Предлагает выбор: написать имя артиста вручную или импортировать.
    Может также включать кнопку настройки общей мобильности.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Написать артиста", callback_data="write_artist")
    builder.button(text="📥 Импортировать", callback_data="import_artists")
    builder.adjust(1)
    if show_setup_mobility_button:
        builder.row(InlineKeyboardButton(text="🛠️ Настроить общую мобильность", callback_data="setup_general_mobility"))
    return builder.as_markup()

def get_mobility_type_choice_keyboard() -> InlineKeyboardMarkup:
    """
    Предлагает использовать общие настройки мобильности или настроить для текущей подписки.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="🌍 Использовать общие", callback_data="use_general_mobility")
    builder.button(text="⚙️ Настроить для этой подписки", callback_data="setup_custom_mobility")
    builder.adjust(1)
    return builder.as_markup()


def get_add_more_or_finish_keyboard(show_setup_mobility_button: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для цикла добавления подписок.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Добавить еще артиста", callback_data="write_artist")
    builder.button(text="📥 Импортировать еще", callback_data="import_artists")
    if show_setup_mobility_button:
         builder.row(InlineKeyboardButton(text="🛠️ Настроить общую мобильность", callback_data="setup_general_mobility"))
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="finish_adding_subscriptions"))
    return builder.as_markup()

def found_artists_keyboard(artists) -> InlineKeyboardMarkup:
    """
    Показывает найденных артистов для подписки.
    ИЗМЕНЕНИЕ: Использует ID артиста в callback_data.
    """
    builder = InlineKeyboardBuilder()
    for artist in artists:
        # Текст кнопки по-прежнему обрезаем на всякий случай
        button_text = artist.name[:40] + '...' if len(artist.name) > 40 else artist.name
        
        # ИЗМЕНЕНИЕ: В callback_data передаем ID, а не имя
        builder.button(text=button_text, callback_data=f"subscribe_to_artist:{artist.artist_id}")
        
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="cancel_artist_search"))
    return builder.as_markup()