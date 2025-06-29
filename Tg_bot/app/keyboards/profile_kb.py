from datetime import datetime
import locale
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dateutil.relativedelta import relativedelta
from app.lexicon import EVENT_TYPE_EMOJI
from ..lexicon import get_event_type_keys, get_event_type_display_name, get_event_type_storage_value

def get_profile_keyboard(lexicon) -> InlineKeyboardMarkup:
    """
    Новая клавиатура для меню профиля.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text=lexicon.get('profile_button_location'), callback_data="edit_main_geo")
    builder.button(text=lexicon.get('profile_general_geo'), callback_data="edit_general_mobility")
    builder.button(text=lexicon.get('profile_button_manage_subs'), callback_data="manage_my_subscriptions")
    builder.adjust(1) # Каждая кнопка на новой строке
    return builder.as_markup()

def get_manage_subscriptions_keyboard(subscriptions: list, lexicon) -> InlineKeyboardMarkup:
    """
    Показывает список подписок. Нажатие на подписку открывает ее для просмотра/редактирования.
    НЕ содержит кнопки "Добавить".
    """
    builder = InlineKeyboardBuilder()
    if subscriptions:
        for sub_event in subscriptions:
            # Ищем подписку текущего пользователя среди всех подписок на это событие
            # (в 99% случаев она будет одна, но это самый надежный способ)
            user_subscription = next((sub for sub in sub_event.subscriptions), None)
            
            status_emoji = ""
            if user_subscription:
                status_emoji = "▶️" if user_subscription.status == 'active' else "⏸️"

            button_text = f"{status_emoji} {sub_event.title}"
            
            builder.button(
                text=button_text, 
                callback_data=f"view_subscription:{sub_event.event_id}"
            )
        builder.adjust(1)
    
    builder.row(InlineKeyboardButton(text=lexicon.get('back_button'), callback_data="back_to_profile"))
    return builder.as_markup()


def get_edit_country_keyboard(countries: list, lexicon) -> InlineKeyboardMarkup:
    """Новая клавиатура для выбора страны в профиле."""
    builder = InlineKeyboardBuilder()
    for country in countries:
        builder.button(text=country, callback_data=f"edit_country:{country}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=lexicon.get('back_to_profile'), callback_data="back_to_profile"))
    return builder.as_markup()

def get_edit_city_keyboard(top_cities: list, lexicon) -> InlineKeyboardMarkup:
    """Новая клавиатура для выбора города в профиле."""
    builder = InlineKeyboardBuilder()
    for city in top_cities:
        builder.button(text=city, callback_data=f"edit_city:{city}")
    builder.adjust(2)
    # --- ДОБАВЛЕНА КНОПКА ПОИСКА С УНИКАЛЬНЫМ CALLBACK ---
    builder.row(InlineKeyboardButton(text=lexicon.get('find_another_city'), callback_data="edit_search_for_city"))
    builder.row(InlineKeyboardButton(text=lexicon.get('back_to_choose_country'), callback_data="back_to_edit_country"))
    return builder.as_markup()

def get_edit_event_type_keyboard(lexicon, selected_types: list = None) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора типов событий в профиле с кнопкой "Выбрать все".
    """
    all_event_keys = get_event_type_keys()
    all_storage_values = [get_event_type_storage_value(key) for key in all_event_keys]
    if selected_types:
        # Оставляем в selected_types только те значения, которые есть в all_storage_values
        valid_selected_types = [t for t in selected_types if t in all_storage_values]
    else:
        valid_selected_types = []
    builder = InlineKeyboardBuilder()

    
    all_storage_values = [get_event_type_storage_value(key) for key in all_event_keys]

    # --- ДОБАВЛЕНА КНОПКА "ВЫБРАТЬ/СНЯТЬ ВСЕ" ---
    all_selected = set(all_storage_values) == set(valid_selected_types)
    select_all_text = lexicon.get('unselect_all_button') if all_selected else lexicon.get('select_all_button')
    
    # Используем уникальный callback_data для флоу редактирования
    builder.button(text=select_all_text, callback_data="edit_toggle_event_type:all")
    # --- КОНЕЦ ---

    for key in all_event_keys:
        display_name = get_event_type_display_name(key, lexicon.lang_code)
        storage_value = get_event_type_storage_value(key)
        
        text = f"✅ {display_name}" if storage_value in selected_types else f"⬜️ {display_name}"
        # Уникальный callback_data для обычных кнопок
        builder.button(text=text, callback_data=f"edit_toggle_event_type:{storage_value}")
    
    # Адаптируем расположение
    builder.adjust(1, 2)
    
    builder.row(InlineKeyboardButton(text=lexicon.get('save_changes'), callback_data="finish_edit_preferences"))
    # Можно добавить кнопку "Назад к выбору города" для лучшего UX
    # builder.row(InlineKeyboardButton(text=lexicon.get('back_to_choose_city'), callback_data="..."))
    return builder.as_markup()

def get_edit_found_cities_keyboard(found_cities: list, lexicon) -> InlineKeyboardMarkup:
    """Новая клавиатура для показа найденных городов в профиле."""
    builder = InlineKeyboardBuilder()
    for city in found_cities:
        builder.button(text=city, callback_data=f"edit_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=lexicon.get('back_to_choose_city'), callback_data="back_to_edit_city_list"))
    return builder.as_markup()