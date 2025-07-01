from datetime import datetime
import locale
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from dateutil.relativedelta import relativedelta
from app.lexicon import EVENT_TYPE_EMOJI

def get_afisha_actions_keyboard(lexicon) -> InlineKeyboardMarkup:
    """
    Клавиатура с действиями после показа списка событий (из Афиши или после добавления в избранное).
    """
    builder = InlineKeyboardBuilder()
    builder.button(
        text=lexicon.get('afisha_add_to_subs_button'), 
        callback_data="add_events_to_subs"
    )
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
        month_name = lexicon.MONTH_NAMES[month_date.month - 1]
        
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
    # --- ИЗМЕНЕНИЕ: callback кнопки "Назад" теперь ведет на предыдущий шаг ---
    builder.row(InlineKeyboardButton(text=lexicon.get('back_to_date_choice_button'), callback_data="back_to_date_choice"))
    return builder.as_markup()

def get_temp_country_selection_keyboard(lexicon) -> InlineKeyboardMarkup:
    """Создает клавиатуру для выбора страны во временном поиске Афиши."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Беларусь", callback_data="temp_select_country:Беларусь")
    builder.button(text="Россия", callback_data="temp_select_country:Россия")
    builder.adjust(2)
    # Кнопка "Назад" ведет к выбору типа фильтра
    builder.row(InlineKeyboardButton(text=lexicon.get('back_button'), callback_data="back_to_filter_type_choice"))
    return builder.as_markup()