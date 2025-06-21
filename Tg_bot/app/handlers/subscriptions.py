# app/handlers/subscriptions.py

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold

from ..database import requests as db
from .. import keyboards as kb
from .common import format_events_for_response

router = Router()

class SubscriptionFlow(StatesGroup):
    # Онбординг общей мобильности
    general_mobility_onboarding = State()
    selecting_general_regions = State()
    # Основной флоу добавления
    waiting_for_action = State()
    waiting_for_artist_name = State()
    choosing_mobility_type = State()
    selecting_custom_regions = State()

async def show_subscriptions_menu(message_or_cbq: Message | CallbackQuery):
    """Показывает текущие подписки пользователя с кнопкой 'Добавить'."""
    user_id = message_or_cbq.from_user.id
    subs = await db.get_user_subscriptions(user_id)
    text = "Твои подписки:\n"
    if subs:
        for sub in subs:
            text += f"▫️ {hbold(sub)}\n"
    else:
        text = "У тебя пока нет подписок."

    markup = kb.get_my_subscriptions_keyboard(subs)

    if isinstance(message_or_cbq, CallbackQuery):
        await message_or_cbq.message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await message_or_cbq.answer(text, reply_markup=markup, parse_mode="HTML")

@router.message(F.text.in_(['➕ Найти/добавить артиста', '➕ Find/Add Artist', '➕ Знайсці/дадаць выканаўцу'])) 
async def menu_add_subscriptions(message: Message, state: FSMContext):
    """
    Точка входа в флоу ДОБАВЛЕНИЯ подписки.
    """
    await state.clear()
    user_id = message.from_user.id
    onboarding_done = await db.check_general_geo_onboarding_status(user_id)

    if not onboarding_done:
        # Случай 1: Пользователь здесь в самый первый раз.
        await state.set_state(SubscriptionFlow.general_mobility_onboarding)
        await message.answer(
            "Для добавления артиста вам надо настроить страны, куда вы готовы полететь. "
            "Это общая настройка, которую можно будет использовать для всех подписок. Вы можете пропустить этот шаг.",
            reply_markup=kb.get_general_onboarding_keyboard()
        )
    else:
        # Пользователь уже проходил онбординг.
        general_mobility_regions = await db.get_general_mobility(user_id)
        await state.set_state(SubscriptionFlow.waiting_for_action)
        await state.update_data(pending_subscriptions=[])

        if not general_mobility_regions:
            # Случай 2: Онбординг пройден, но мобильность не настроена (пропущена).
            # Показываем дополнительную кнопку.
            await message.answer(
                "Напиши исполнителя/событие для отслеживания. Также ты можешь сначала настроить общую мобильность.",
                reply_markup=kb.get_add_sub_action_keyboard(show_setup_mobility_button=True)
            )
        else:
            # Случай 3: Все настроено.
            # Стандартный флоу без лишних кнопок.
            await message.answer(
                "Напиши исполнителя/событие для отслеживания. Также я могу импортировать их.",
                reply_markup=kb.get_add_sub_action_keyboard(show_setup_mobility_button=False)
            )

@router.callback_query(F.data == "show_my_subscriptions_from_profile")
async def cq_show_my_subscriptions_from_profile(callback: CallbackQuery, state: FSMContext):
    """Точка входа в раздел 'Мои подписки' из меню профиля."""
    await state.clear()
    await callback.message.delete()
    await show_subscriptions_menu(callback.message)
    await callback.answer()

@router.callback_query(F.data == "add_new_subscription")
async def start_subscription_add_flow(callback: CallbackQuery, state: FSMContext):
    """Начало флоу добавления подписки."""
    user_id = callback.from_user.id
    onboarding_done = await db.check_general_geo_onboarding_status(user_id)

    if not onboarding_done:
        await state.set_state(SubscriptionFlow.general_mobility_onboarding)
        await callback.message.edit_text(
            "Для добавления артиста вам надо настроить страны, куда вы готовы полететь. "
            "Это общая настройка, которую можно будет использовать для всех подписок. Вы можете пропустить этот шаг.",
            reply_markup=kb.get_general_onboarding_keyboard()
        )
    else:
        await state.set_state(SubscriptionFlow.waiting_for_action)
        await state.update_data(pending_subscriptions=[])
        await callback.message.edit_text(
            "Напиши исполнителя/событие для отслеживания. Также я могу импортировать их.",
            reply_markup=kb.get_add_sub_action_keyboard()
        )
    await callback.answer()



@router.callback_query(SubscriptionFlow.general_mobility_onboarding, F.data.in_(['setup_general_mobility', 'skip_general_mobility']))
async def handle_general_onboarding_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора в онбординге общей мобильности."""
    await db.set_general_geo_onboarding_completed(callback.from_user.id)

    if callback.data == 'setup_general_mobility':
        await state.set_state(SubscriptionFlow.selecting_general_regions)
        await state.update_data(selected_regions=[])
        all_countries = await db.get_countries()
        await callback.message.edit_text(
            "Отлично! Выбери страны, которые войдут в твою 'общую мобильность'.",
            # --- ИЗМЕНЕНИЕ ЗДЕСЬ: передаем конкретный callback ---
            reply_markup=kb.get_region_selection_keyboard(
                all_countries, [], finish_callback="finish_general_selection"
            )
        )
    else: # skip_general_mobility
        await state.set_state(SubscriptionFlow.waiting_for_action)
        await state.update_data(pending_subscriptions=[])
        await callback.message.edit_text(
            "Хорошо. Теперь напиши исполнителя/событие для отслеживания или импортируй их.",
            reply_markup=kb.get_add_sub_action_keyboard()
        )

@router.callback_query(SubscriptionFlow.waiting_for_action, F.data == "setup_general_mobility")
async def handle_setup_general_mobility_again(callback: CallbackQuery, state: FSMContext):
    """
    Этот хэндлер срабатывает, когда пользователь нажимает 'Настроить общую мобильность'
    уже после прохождения первого онбординга.
    """
    await state.set_state(SubscriptionFlow.selecting_general_regions)
    await state.update_data(selected_regions=[])
    all_countries = await db.get_countries()
    await callback.message.edit_text(
        "Отлично! Выбери страны, которые войдут в твою 'общую мобильность'.",
        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        reply_markup=kb.get_region_selection_keyboard(
            all_countries, [], finish_callback="finish_general_selection"
        )
    )
    await callback.answer()

@router.callback_query(SubscriptionFlow.selecting_general_regions, F.data.startswith("toggle_region:"))
async def cq_toggle_region_for_general(callback: CallbackQuery, state: FSMContext):
    region_name = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_regions", [])
    if region_name in selected:
        selected.remove(region_name)
    else:
        selected.append(region_name)
    await state.update_data(selected_regions=selected)
    all_countries = await db.get_countries()
    # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_region_selection_keyboard(all_countries, selected, finish_callback="finish_general_selection")
    )

@router.callback_query(SubscriptionFlow.selecting_general_regions, F.data == "finish_general_selection")
async def cq_finish_general_selection(callback: CallbackQuery, state: FSMContext):
    """Завершение настройки общей мобильности."""
    data = await state.get_data()
    regions = data.get("selected_regions", [])

    if not regions:
        await callback.answer("Нужно выбрать хотя бы один регион!", show_alert=True)
        return

    await db.set_general_mobility(callback.from_user.id, regions)
    await callback.answer("✅ Общие настройки мобильности сохранены!", show_alert=True)
    
    await state.set_state(SubscriptionFlow.waiting_for_action)
    await state.update_data(pending_subscriptions=[])
    await callback.message.edit_text(
        "Отлично! Теперь напиши исполнителя/событие или импортируй их.",
        reply_markup=kb.get_add_sub_action_keyboard()
    )

@router.callback_query(SubscriptionFlow.waiting_for_action, F.data == "write_artist")
async def handle_write_artist(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.waiting_for_artist_name)
    await callback.message.edit_text("Введите имя артиста или название группы:")
    await callback.answer()

@router.callback_query(SubscriptionFlow.waiting_for_action, F.data == "import_artists")
async def handle_import_artists(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Функция импорта находится в разработке.", show_alert=True)

@router.message(SubscriptionFlow.waiting_for_artist_name, F.text)
async def process_artist_search(message: Message, state: FSMContext):
    """Поиск артиста по имени."""
    found_artists = await db.find_artists_fuzzy(message.text)
    if not found_artists:
        await message.answer("По твоему запросу никого не найдено. Попробуй еще раз.")
    else:
        await message.answer("Вот кого я нашел. Выбери нужного артиста:",
                             reply_markup=kb.found_artists_keyboard(found_artists))

@router.callback_query(F.data == "cancel_artist_search")
async def cq_cancel_artist_search(callback: CallbackQuery, state: FSMContext):
    """Отмена поиска артиста и возврат в меню подписок."""
    await state.clear()
    await callback.message.delete()
    await show_subscriptions_menu(callback.message)

@router.callback_query(F.data.startswith("subscribe_to_artist:"))
async def cq_subscribe_to_artist(callback: CallbackQuery, state: FSMContext):
    artist_name = callback.data.split(":", 1)[1]
    await state.update_data(current_artist=artist_name)
    general_mobility = await db.get_general_mobility(callback.from_user.id)
    if general_mobility:
        await state.set_state(SubscriptionFlow.choosing_mobility_type)
        await callback.message.edit_text(
            f"Артист: {hbold(artist_name)}. Хотите добавить страны для отслеживания конкретно для этой подписки или использовать общие настройки?",
            reply_markup=kb.get_mobility_type_choice_keyboard(),
            parse_mode="HTML"
        )
    else:
        await state.set_state(SubscriptionFlow.selecting_custom_regions)
        await state.update_data(selected_regions=[])
        all_countries = await db.get_countries()
        await callback.message.edit_text(
            f"Артист: {hbold(artist_name)}. Укажите страны для отслеживания.",
            # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
            reply_markup=kb.get_region_selection_keyboard(all_countries, [], finish_callback="finish_custom_selection"),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(SubscriptionFlow.choosing_mobility_type, F.data.in_(['use_general_mobility', 'setup_custom_mobility']))
async def handle_mobility_type_choice(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    artist_name = data.get('current_artist')
    pending_subs = data.get('pending_subscriptions', [])
    if callback.data == 'use_general_mobility':
        regions = await db.get_general_mobility(callback.from_user.id)
        pending_subs.append({"item_name": artist_name, "category": "music", "regions": regions})
        await state.update_data(pending_subscriptions=pending_subs)
        await callback.answer(f"Артист {artist_name} добавлен с общими настройками.", show_alert=True)
        await show_add_more_or_finish(callback.message, state)
    else:
        await state.set_state(SubscriptionFlow.selecting_custom_regions)
        await state.update_data(selected_regions=[])
        all_countries = await db.get_countries()
        await callback.message.edit_text(
            f"Артист: {hbold(artist_name)}. Укажите страны для отслеживания.",
            # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
            reply_markup=kb.get_region_selection_keyboard(all_countries, [], finish_callback="finish_custom_selection"),
            parse_mode="HTML"
        )

@router.callback_query(SubscriptionFlow.selecting_custom_regions, F.data.startswith("toggle_region:"))
async def cq_toggle_region_for_custom(callback: CallbackQuery, state: FSMContext):
    region_name = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_regions", [])
    if region_name in selected:
        selected.remove(region_name)
    else:
        selected.append(region_name)
    await state.update_data(selected_regions=selected)
    all_countries = await db.get_countries()
    # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_region_selection_keyboard(all_countries, selected, finish_callback="finish_custom_selection")
    )

@router.callback_query(SubscriptionFlow.selecting_custom_regions, F.data == "finish_custom_selection")
async def cq_finish_custom_selection(callback: CallbackQuery, state: FSMContext):
    """Завершение настройки кастомных регионов для подписки."""
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    artist_name = data.get('current_artist')
    pending_subs = data.get('pending_subscriptions', [])

    if not regions:
        await callback.answer("Нужно выбрать хотя бы один регион!", show_alert=True)
        return
    
    pending_subs.append({"item_name": artist_name, "category": "music", "regions": regions})
    await state.update_data(pending_subscriptions=pending_subs)
    await callback.answer(f"Артист {artist_name} добавлен с кастомными настройками.", show_alert=True)

    await show_add_more_or_finish(callback.message, state)

async def show_add_more_or_finish(message: Message, state: FSMContext):
    """Показывает клавиатуру 'Добавить еще' / 'Готово'."""
    data = await state.get_data()
    pending_subs = data.get('pending_subscriptions', [])
    text = "Подписка добавлена в очередь на сохранение.\n"
    if pending_subs:
        text += "\n<b>Очередь на добавление:</b>\n"
        for sub in pending_subs:
            text += f"▫️ {hbold(sub['item_name'])}\n"
    
    await state.set_state(SubscriptionFlow.waiting_for_action)
    await message.edit_text(text, reply_markup=kb.get_add_more_or_finish_keyboard(), parse_mode="HTML")

@router.callback_query(SubscriptionFlow.waiting_for_action, F.data == "finish_adding_subscriptions")
async def finish_adding_subscriptions(callback: CallbackQuery, state: FSMContext):
    """Завершает сессию, сохраняет все подписки и показывает результат."""
    data = await state.get_data()
    pending_subs = data.get('pending_subscriptions', [])

    if not pending_subs:
        await callback.answer("Вы ничего не добавили в очередь.", show_alert=True)
        return

    await db.add_subscriptions_bulk(callback.from_user.id, pending_subs)
    await state.clear()

    final_text = "✅ Ваши подписки успешно сохранены:\n"
    artist_names = []
    all_regions = set()
    for sub in pending_subs:
        final_text += f"▫️ {hbold(sub['item_name'])}\n"
        artist_names.append(sub['item_name'])
        for region in sub['regions']:
            all_regions.add(region)

    final_text += "\nИщу для вас актуальные события..."
    await callback.message.edit_text(final_text, parse_mode="HTML")

    found_events = await db.get_events_for_artists(artist_names, list(all_regions))
    if found_events:
        events_text = await format_events_for_response(found_events)
        await callback.message.answer(
            "🔥 Вот что я нашел по вашим новым подпискам:",
            disable_web_page_preview=True
        )
        await callback.message.answer(events_text, parse_mode="HTML", disable_web_page_preview=True)
    else:
        await callback.message.answer("😔 Пока что для ваших новых подписок актуальных событий не найдено.")
    
    await callback.message.answer("Вы всегда можете изменить настройки каждой подписки в профиле.")


@router.callback_query(F.data.startswith("unsubscribe:"))
async def cq_unsubscribe_item(callback: CallbackQuery, state: FSMContext):
    """Удаление подписки из меню."""
    item_name = callback.data.split(":", 1)[1]
    await db.remove_subscription(callback.from_user.id, item_name)
    await callback.answer(f"❌ Вы отписались от {item_name}.")
    await show_subscriptions_menu(callback)