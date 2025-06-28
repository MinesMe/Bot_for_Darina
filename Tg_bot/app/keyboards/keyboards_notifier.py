# app/keyboards_notifier.py

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_add_to_subscriptions_keyboard(event_id: int, lexicon) -> InlineKeyboardMarkup:
    """Создает клавиатуру с одной кнопкой 'Добавить в подписки'."""
    builder = InlineKeyboardBuilder()
    builder.button(
        text=lexicon.get('afisha_add_to_subs_button'),
        callback_data=f"add_to_subs_from_notify:{event_id}"
    )
    return builder.as_markup()

