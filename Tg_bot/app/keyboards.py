# app/keyboards.py

from datetime import datetime
import locale
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dateutil.relativedelta import relativedelta

# --- КОНСТАНТЫ ---
EVENT_TYPES_RU = ["Концерт", "Театр", "Спорт", "Цирк", "Выставка", "Фестиваль"]
EVENT_TYPE_EMOJI = {
    "Концерт": "🎵", "Театр": "🎭", "Спорт": "🏅", "Цирк": "🎪",
    "Выставка": "🎨", "Фестиваль": "🎉",
}

RU_MONTH_NAMES = [
    "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
]


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

def get_profile_keyboard(lexicon) -> InlineKeyboardMarkup:
    """
    Новая клавиатура для меню профиля.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="📍 Изменить основное гео", callback_data="edit_main_geo")
    builder.button(text="🌍 Изменить общую мобильность", callback_data="edit_general_mobility")
    builder.button(text="⭐ Мои подписки", callback_data="manage_my_subscriptions")
    builder.adjust(1) # Каждая кнопка на новой строке
    return builder.as_markup()

# --- КЛАВИАТУРЫ ДЛЯ ОНБОРДИНГА ---
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

def get_home_city_selection_keyboard(top_cities: list, lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in top_cities:
        builder.button(text=city, callback_data=f"select_home_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="🔎 Найти другой город", callback_data="search_for_home_city"))
    return builder.as_markup()

def get_found_home_cities_keyboard(found_cities: list, lexicon) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in found_cities:
        builder.button(text=city, callback_data=f"select_home_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=lexicon.get('back_button'), callback_data="back_to_city_selection"))
    return builder.as_markup()

def get_event_type_selection_keyboard(lexicon, selected_types: list = None) -> InlineKeyboardMarkup:
    if selected_types is None: selected_types = []
    builder = InlineKeyboardBuilder()
    for event_type in EVENT_TYPES_RU:
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
    
    builder.row(InlineKeyboardButton(text=lexicon.get('back_to_profile_button'), callback_data="back_to_profile"))
    return builder.as_markup()

def get_edit_country_keyboard(countries: list, lexicon) -> InlineKeyboardMarkup:
    """Новая клавиатура для выбора страны в профиле."""
    builder = InlineKeyboardBuilder()
    for country in countries:
        builder.button(text=country, callback_data=f"edit_country:{country}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ Назад в профиль", callback_data="back_to_profile"))
    return builder.as_markup()

def get_edit_city_keyboard(top_cities: list, lexicon) -> InlineKeyboardMarkup:
    """Новая клавиатура для выбора города в профиле."""
    builder = InlineKeyboardBuilder()
    for city in top_cities:
        builder.button(text=city, callback_data=f"edit_city:{city}")
    builder.adjust(2)
    # --- ДОБАВЛЕНА КНОПКА ПОИСКА С УНИКАЛЬНЫМ CALLBACK ---
    builder.row(InlineKeyboardButton(text="🔎 Найти другой город", callback_data="edit_search_for_city"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к выбору страны", callback_data="back_to_edit_country"))
    return builder.as_markup()
    
def get_edit_event_type_keyboard(lexicon, selected_types: list = None) -> InlineKeyboardMarkup:
    """Новая клавиатура для выбора типов событий в профиле."""
    if selected_types is None: selected_types = []
    builder = InlineKeyboardBuilder()
    for event_type in EVENT_TYPES_RU:
        text = f"✅ {event_type}" if event_type in selected_types else f"⬜️ {event_type}"
        builder.button(text=text, callback_data=f"edit_toggle_event_type:{event_type}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="✅ Сохранить изменения", callback_data="finish_edit_preferences"))
    return builder.as_markup()

def get_edit_found_cities_keyboard(found_cities: list, lexicon) -> InlineKeyboardMarkup:
    """Новая клавиатура для показа найденных городов в профиле."""
    builder = InlineKeyboardBuilder()
    for city in found_cities:
        builder.button(text=city, callback_data=f"edit_city:{city}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="⬅️ Назад к выбору города", callback_data="back_to_edit_city_list"))
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

def get_general_onboarding_keyboard() -> InlineKeyboardMarkup:
    """
    Предлагает настроить или пропустить настройку общей мобильности.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="👍 Да, настроить", callback_data="setup_general_mobility")
    builder.button(text="➡️ Пропустить", callback_data="skip_general_mobility")
    builder.adjust(1)
    return builder.as_markup()

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


# --- ОСТАЛЬНЫЕ КЛАВИАТУРЫ ---

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

def get_paginated_artists_keyboard(all_artists: list, selected_artists: set, page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    PAGE_SIZE = 5
    start, end = page * PAGE_SIZE, (page + 1) * PAGE_SIZE
    artists_on_page = all_artists[start:end]
    for artist in artists_on_page:
        text = f"✅ {artist}" if artist in selected_artists else f"⬜️ {artist}"
        builder.button(text=text, callback_data=f"toggle_artist_subscribe:{artist}")
    builder.adjust(1)
    total_pages = (len(all_artists) + PAGE_SIZE - 1) // PAGE_SIZE
    if total_pages > 1:
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"paginate_artists:{page - 1}"))
        pagination_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ignore"))
        if page < total_pages - 1:
            pagination_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"paginate_artists:{page + 1}"))
        builder.row(*pagination_buttons)
    builder.row(InlineKeyboardButton(text="✅ Готово", callback_data="finish_artist_selection"))
    return builder.as_markup()

def get_categories_keyboard(categories: list = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    source_list = categories if categories else EVENT_TYPES_RU
    for category in source_list:
        emoji = EVENT_TYPE_EMOJI.get(category, "🔹")
        builder.button(text=f"{emoji} {category}", callback_data=f"category:{category}")
    builder.adjust(2)
    return builder.as_markup()

def get_cities_keyboard(cities: list, category: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for city in cities:
        builder.button(text=city, callback_data=f"city:{city}:{category}")
    builder.adjust(2)
    return builder.as_markup()

#---------- АФИША ----------

def get_afisha_settings()-> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Настроить", callback_data=f"afisha_main_geo_settings"))
    builder.row(InlineKeyboardButton(text="Пропустить настройку", callback_data=f"skip_afisha_main_geo"))
    return builder.as_markup()

def get_afisha_settings_type()-> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="По мои настройкам", callback_data=f"afisha_defautl_type_settings"))
    builder.row(InlineKeyboardButton(text="Другую", callback_data=f"afisha_another_type_settings"))
    return builder.as_markup()

def get_afisha_actions_keyboard(lexicon) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с действиями, доступными после просмотра списка событий.
    На данный момент это только кнопка "Добавить в подписки".
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=lexicon.get('afisha_add_to_subs_button'), 
        callback_data="add_events_to_subs"
    )
    # В будущем сюда можно добавить кнопки "Отфильтровать еще" или "Поделиться"
    return builder.as_markup()

def get_date_period_keyboard(lexicon) -> InlineKeyboardMarkup:
    """Создает клавиатуру для первоначального выбора периода."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=lexicon.get('period_today'), callback_data="select_period:today"),
        InlineKeyboardButton(text=lexicon.get('period_tomorrow'), callback_data="select_period:tomorrow")
    )
    builder.row(
        InlineKeyboardButton(text=lexicon.get('period_this_week'), callback_data="select_period:this_week"),
        InlineKeyboardButton(text=lexicon.get('period_this_weekend'), callback_data="select_period:this_weekend")
    )
    builder.row(InlineKeyboardButton(text=lexicon.get('period_this_month'), callback_data="select_period:this_month"))
    builder.row(InlineKeyboardButton(text=lexicon.get('period_other_month'), callback_data="select_period:other_month"))
    return builder.as_markup()

def get_month_choice_keyboard(lexicon) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора одного из следующих 12 месяцев."""
    builder = InlineKeyboardBuilder()
    current_date = datetime.now()
    
    # УДАЛЕНО: Блок try-except с locale.setlocale()
    
    for i in range(12):
        month_date = current_date + relativedelta(months=+i)
        
        # ИЗМЕНЕНИЕ: Получаем название месяца из нашего списка, а не через strftime
        # month_date.month вернет число от 1 до 12. В списках индексация с 0, поэтому -1.
        month_name = RU_MONTH_NAMES[month_date.month - 1]
        
        # Формируем текст для кнопки
        button_text = f"{month_name} {month_date.strftime('%Y')}"
        
        callback_data = month_date.strftime("select_month:%Y-%m")
        builder.button(text=button_text, callback_data=callback_data)
        
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text=lexicon.get('back_to_date_choice_button'), callback_data="back_to_date_choice"))
    return builder.as_markup()

def get_filter_type_choice_keyboard(lexicon) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора типа фильтрации после выбора даты."""
    builder = InlineKeyboardBuilder()
    builder.button(text=lexicon.get('afisha_filter_by_my_prefs_button'), callback_data="filter_type:my_prefs")
    builder.button(text=lexicon.get('afisha_filter_by_temporary_button'), callback_data="filter_type:temporary")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text=lexicon.get('back_to_date_choice_button'), callback_data="back_to_date_choice"))
    return builder.as_markup()

# --- НОВЫЙ БЛОК: Клавиатуры для раздела "Избранное" ---

def get_favorites_menu_keyboard( favorites: list, lexicon) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для главного меню 'Избранное'."""
    builder = InlineKeyboardBuilder()
    
    if favorites:
        for fav in favorites:
            # Обрезаем текст кнопки, чтобы избежать ошибки Telegram
            button_text = fav.name[:40] + '...' if len(fav.name) > 40 else fav.name
            builder.button(text=f"⭐ {button_text}", callback_data=f"view_favorite:{fav.artist_id}")
        builder.adjust(1)
    
    # Кнопка "Добавить" переехала в другой модуль.
    # Кнопка "Настроить мобильность" теперь в меню управления конкретным артистом.
    
    return builder.as_markup()

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

# def get_found_artists_for_favorites_keyboard(artists: list, lexicon) -> InlineKeyboardMarkup:
#     """Показывает найденных артистов для добавления в избранное."""
#     builder = InlineKeyboardBuilder()
#     for artist in artists:
#         builder.button(text=artist.name, callback_data=f"add_fav_artist:{artist.artist_id}")
#     builder.adjust(1)
#     builder.row(InlineKeyboardButton(text=lexicon.get('back_to_favorites_menu_button'), callback_data="back_to_favorites_menu"))
#     return builder.as_markup()

# def get_favorites_not_found_keyboard(lexicon) -> InlineKeyboardMarkup:
#     """Клавиатура на случай, если поиск по избранному ничего не дал."""
#     builder = InlineKeyboardBuilder()
#     builder.button(text=lexicon.get('back_to_favorites_menu_button'), callback_data="back_to_favorites_menu")
#     return builder.as_markup()

# def get_remove_from_favorites_keyboard(favorites: list, lexicon ) -> InlineKeyboardMarkup:
#     """Показывает список избранных, где каждая кнопка - для удаления."""
#     builder = InlineKeyboardBuilder()
#     for fav in favorites:
#         builder.button(text=f"🗑️ {fav.name}", callback_data=f"remove_fav_artist:{fav.artist_id}")
#     builder.adjust(1)
#     builder.row(InlineKeyboardButton(text=lexicon.get('back_to_favorites_menu_button'), callback_data="back_to_favorites_menu"))
#     return builder.as_markup()