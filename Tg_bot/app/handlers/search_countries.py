# app/handlers/search_countries.py
# (Создайте новый файл с этим содержимым)

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from ..database.requests import requests as db
from app import keyboards as kb
from ..lexicon import Lexicon

async def start_country_search(callback: CallbackQuery, state: FSMContext, new_state: State, back_callback: str):
    """
    Общая функция для начала поиска страны.
    Переводит в новое состояние и просит ввести название страны.
    """
    await state.set_state(new_state)
    await state.update_data(msg_id_to_edit=callback.message.message_id)
    lexicon = Lexicon(callback.from_user.language_code)
    
    await callback.message.edit_text(
        lexicon.get('search_country_prompt'), # <-- Новый ключ лексикона
        reply_markup=kb.get_back_to_country_selection_keyboard(lexicon, back_callback)
    )
    await callback.answer()

async def process_country_input(message: Message, state: FSMContext, return_state: State, back_callback: str):
    """
    Общая функция для обработки введенного названия страны.
    """
    data = await state.get_data()
    msg_id_to_edit = data.get("msg_id_to_edit")
    lexicon = Lexicon(message.from_user.language_code)

    await message.delete()
    if not msg_id_to_edit:
        return

    best_matches = await db.find_countries_fuzzy(message.text)
    
    try:
        if not best_matches:
            await message.bot.edit_message_text(
                chat_id=message.chat.id, message_id=msg_id_to_edit,
                text=lexicon.get('country_not_found'), # <-- Новый ключ лексикона
                reply_markup=kb.get_back_to_country_selection_keyboard(lexicon, back_callback)
            )
        else:
            # Важно: не меняем состояние, остаемся в ожидании ввода,
            # но показываем найденные варианты.
            # Выбор страны обработается хендлером toggle_region.
            await message.bot.edit_message_text(
                chat_id=message.chat.id, message_id=msg_id_to_edit,
                text=lexicon.get('country_found_prompt'), # <-- Новый ключ лексикона
                reply_markup=kb.get_found_countries_keyboard(best_matches, lexicon, back_callback)
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise