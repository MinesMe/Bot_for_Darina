from datetime import datetime
import locale
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dateutil.relativedelta import relativedelta
from app.lexicon import EVENT_TYPE_EMOJI

def get_country_selection_keyboard(countries: list, lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for country in countries:
        builder.button(text=country, callback_data=f"main_geo_settings:{country}")
    builder.adjust(2)
    return builder.as_markup()

def get_main_geo_settings(lexicon)-> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Настроить", callback_data=f"select_home_country"))
    builder.row(InlineKeyboardButton(text="Пропустить настройку", callback_data=f"finish_preferences_selection:{False}"))
    return builder.as_markup()

def get_found_home_cities_keyboard(found_cities: list, lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in found_cities:
        builder.button(text=city, callback_data=f"select_home_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=lexicon.get('back_button'), callback_data="back_to_city_selection"))
    return builder.as_markup()

def get_single_subscription_manage_keyboard(event_id: int, current_status: str, lexicon) -> InlineKeyboardMarkup:
    """
    Клавиатура для управления одной конкретной подпиской.
    """
    builder = InlineKeyboardBuilder()
    
    # Умная кнопка паузы/возобновления
    if current_status == 'active':
        toggle_button_text = lexicon.get('subs_pause_button') # "⏸️ Поставить на паузу"
    else:
        toggle_button_text = lexicon.get('subs_resume_button') # "▶️ Возобновить"
        
    builder.button(text=toggle_button_text, callback_data=f"toggle_sub_status:{event_id}")
    builder.button(text=lexicon.get('subs_unsubscribe_button'), callback_data=f"delete_subscription:{event_id}") # Используем delete_subscription, как в хэндлере
    
    builder.row(InlineKeyboardButton(text=lexicon.get('back_to_subscriptions_list_button'), callback_data="back_to_subscriptions_list"))
    return builder.as_markup()