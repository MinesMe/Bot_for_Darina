from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest

from ..database.requests import requests as db
from app import keyboards as kb
from ..lexicon import Lexicon

async def start_city_search(callback: CallbackQuery, state: FSMContext, new_state: State, back_callback: str):
    """
    Общая функция для начала поиска города.
    Переводит в новое состояние и просит ввести город.
    """
    await state.set_state(new_state)
    await state.update_data(msg_id_to_edit=callback.message.message_id)
    lexicon = Lexicon(callback.from_user.language_code)
    
    await callback.message.edit_text(
        lexicon.get('search_city_prompt'),
        # Передаем правильный callback для кнопки "Назад"
        reply_markup=kb.get_back_to_city_selection_keyboard(lexicon, back_callback)
    )
    await callback.answer()


async def process_city_input(message: Message, state: FSMContext, country_key: str, return_state: State, found_cities_kb: callable, back_callback):
    """
    Общая функция для обработки введенного города.
    """
    data = await state.get_data()
    country_name = data.get(country_key)
    msg_id_to_edit = data.get("msg_id_to_edit")
    lexicon = Lexicon(message.from_user.language_code)

    await message.delete()
    if not msg_id_to_edit or not country_name:
        return

    best_matches = await db.find_cities_fuzzy(country_name, message.text)
    
    try:
        if not best_matches:
            # ГОРОД НЕ НАЙДЕН
            # --- ИЗМЕНЕНИЕ: Определяем правильный callback для кнопки "Назад" ---
            current_state_str = str(await state.get_state())
            back_callback = "back_to_city_selection" # Онбординг по умолчанию
            if 'EditMainGeoFSM' in current_state_str:
                back_callback = "back_to_edit_city_list"
            elif 'AfishaFlowFSM' in current_state_str:
                back_callback = "back_to_temp_country_choice"
            
            await message.bot.edit_message_text(
                chat_id=message.chat.id, message_id=msg_id_to_edit,
                text=lexicon.get('city_not_found'),
                reply_markup=kb.get_back_to_city_selection_keyboard(lexicon, back_callback)
            )
            # Важно: НЕ меняем состояние, остаемся в ожидании ввода
        else:
            # ГОРОД НАЙДЕН
            await state.set_state(return_state)
            await message.bot.edit_message_text(
                chat_id=message.chat.id, message_id=msg_id_to_edit,
                text=lexicon.get('city_found_prompt'),
                reply_markup=found_cities_kb(best_matches, lexicon)
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

async def back_to_city_list(callback: CallbackQuery, state: FSMContext, country_key: str, city_prompt_key: str, city_selection_kb: callable):
    """
    Общая функция для возврата к списку городов по умолчанию.
    """
    data = await state.get_data()
    country_name = data.get(country_key)
    lexicon = Lexicon(callback.from_user.language_code)

    if not country_name:
        await callback.answer(lexicon.get('generic_error_try_again'), show_alert=True)
        await state.clear()
        return

    top_cities = await db.get_top_cities_for_country(country_name)
    text = lexicon.get(city_prompt_key).format(country_name=hbold(country_name))
    
    # --- ИЗМЕНЕНИЕ: Передаем правильный callback в клавиатуру ---
    # Определяем, к какому именно списку городов возвращаться
    current_state_str = str(await state.get_state())
    back_callback = "back_to_country_selection" # Онбординг по умолчанию
    if 'EditMainGeoFSM' in current_state_str:
        back_callback = "back_to_edit_country"
    elif 'AfishaFlowFSM' in current_state_str:
        back_callback = "back_to_filter_type_choice" # В афише мы возвращаемся к выбору типа фильтра

    # Передаем back_callback в функцию генерации клавиатуры
    await callback.message.edit_text(
        text,
        reply_markup=city_selection_kb(top_cities, lexicon, back_callback_data=back_callback),
        parse_mode=ParseMode.HTML
    )
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---
    await callback.answer()