# app/handlers/subscriptions.py

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.markdown import hbold
from sqlalchemy import select

from ..database.requests import requests as db
from app import keyboards as kb
from .common import format_events_for_response
from .favorities import show_favorites_list 
from ..lexicon import Lexicon


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
        await state.update_data(pending_favorites=[])

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

# @router.callback_query(F.data == "show_my_subscriptions_from_profile")
# async def cq_show_my_subscriptions_from_profile(callback: CallbackQuery, state: FSMContext):
#     """Точка входа в раздел 'Мои подписки' из меню профиля."""
#     await state.clear()
#     await callback.message.delete()
#     await show_subscriptions_menu(callback.message)
#     await callback.answer()

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
        await state.update_data(pending_favorites=[])
        await callback.message.edit_text(
            "Напиши исполнителя/событие для отслеживания. Также я могу импортировать их.",
            reply_markup=kb.get_add_sub_action_keyboard()
        )
    await callback.answer()

@router.callback_query(F.data == "cancel_artist_search")
async def cq_cancel_artist_search(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.waiting_for_action)
    
    lexicon = Lexicon(callback.from_user.language_code)
    
    # Показываем то же сообщение и клавиатуру, что и в начале флоу
    await callback.message.edit_text(
        "Напиши исполнителя/событие для отслеживания. Также я могу импортировать их.",
        reply_markup=kb.get_add_sub_action_keyboard(show_setup_mobility_button=False) # Предполагаем, что мобильность уже настроена
    )
    await callback.answer("Отменено.")

@router.callback_query(SubscriptionFlow.general_mobility_onboarding, F.data.in_(['setup_general_mobility', 'skip_general_mobility']))
async def handle_general_onboarding_choice(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора в онбординге общей мобильности."""
    await db.set_general_geo_onboarding_completed(callback.from_user.id)

    if callback.data == 'setup_general_mobility':
        await state.set_state(SubscriptionFlow.selecting_general_regions)
        await state.update_data(selected_regions=[])
        all_countries = await db.get_countries()
        
        # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
        # Кнопка "Назад" будет просто отменять весь процесс добавления
        await callback.message.edit_text(
            "Отлично! Выбери страны, которые войдут в твою 'общую мобильность'.",
            reply_markup=kb.get_region_selection_keyboard(
                all_countries, [], 
                finish_callback="finish_general_selection",
                # `cancel_add_to_fav` - это callback, который мы используем для отмены
                back_callback="cancel_add_to_fav" 
            )
        )
    else: # skip_general_mobility
        await state.set_state(SubscriptionFlow.waiting_for_action)
        await state.update_data(pending_favorites=[])
        await callback.message.edit_text(
            "Хорошо. Теперь напиши исполнителя/событие для отслеживания или импортируй их.",
            reply_markup=kb.get_add_sub_action_keyboard()
        )

@router.callback_query(F.data == "cancel_add_to_fav")
async def cq_cancel_add_process(callback: CallbackQuery, state: FSMContext):
    print('here')
    """Отменяет процесс добавления и возвращает в главное меню."""
    await state.clear()
    lexicon = Lexicon(callback.from_user.language_code)
    await callback.message.delete()
    # Здесь можно либо показать главное меню, либо меню "Избранное"
    # Давайте вернем в главное меню, это универсальнее
    await callback.message.answer(
        lexicon.get('main_menu_greeting').format(first_name=hbold(callback.from_user.first_name)),
        reply_markup=kb.get_main_menu_keyboard(lexicon),
        parse_mode="HTML"
    )
    await callback.answer("Отменено.")

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
            all_countries, [], finish_callback="finish_general_selection", back_callback="cancel_add_to_fav"
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
        reply_markup=kb.get_region_selection_keyboard(all_countries, selected, finish_callback="finish_general_selection",  back_callback="cancel_add_to_fav" )
    )

@router.callback_query(SubscriptionFlow.waiting_for_action, F.data == "finish_adding_subscriptions")
async def finish_adding_subscriptions(callback: CallbackQuery, state: FSMContext):
    """Завершает сессию и сохраняет все в ИЗБРАННОЕ."""
    data = await state.get_data()
    pending_items = data.get('pending_favorites', [])

    if not pending_items:
        await callback.answer("Вы ничего не добавили в очередь.", show_alert=True)
        return

    added_artist_names = []
    async with db.async_session() as session:
        for item_data in pending_items:
            artist_name = item_data['item_name']
            regions_to_save = item_data['regions']
            artist_obj_stmt = select(db.Artist).where(db.Artist.name == artist_name)
            artist = (await session.execute(artist_obj_stmt)).scalar_one_or_none()
            if artist:
                # Вызываем функцию добавления в избранное
                await db.add_artist_to_favorites(session, callback.from_user.id, artist.artist_id, regions_to_save)
                added_artist_names.append(artist.name)
        await session.commit()

    await state.clear()

    lexicon = Lexicon(callback.from_user.language_code)
    if added_artist_names:
        final_text = lexicon.get('favorites_added_final').format(count=len(added_artist_names))
        await callback.message.edit_text(final_text, parse_mode="HTML")
    else:
        await callback.message.edit_text("Не удалось добавить выбранных артистов.")
    await callback.answer()

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

@router.callback_query(F.data.startswith("subscribe_to_artist:"))
async def cq_subscribe_to_artist(callback: CallbackQuery, state: FSMContext):
    artist_id = int(callback.data.split(":", 1)[1])
    
    # Нам нужно получить имя артиста для сообщений пользователю
    async with db.async_session() as session:
        artist = await session.get(db.Artist, artist_id)
    
    if not artist:
        await callback.answer("Ошибка: артист не найден.", show_alert=True)
        return

    # Сохраняем в state и ID, и имя
    await state.update_data(current_artist_id=artist.artist_id, current_artist=artist.name)
    
    general_mobility = await db.get_general_mobility(callback.from_user.id)
    if general_mobility:
        await state.set_state(SubscriptionFlow.choosing_mobility_type)
        await callback.message.edit_text(
            f"Артист: {hbold(artist.name)}. Хотите добавить страны для отслеживания конкретно для этой подписки или использовать общие настройки?",
            reply_markup=kb.get_mobility_type_choice_keyboard(),
            parse_mode="HTML"
        )
    else:
        await state.set_state(SubscriptionFlow.selecting_custom_regions)
        await state.update_data(selected_regions=[])
        all_countries = await db.get_countries()
        await callback.message.edit_text(
            f"Артист: {hbold(artist.name)}. Укажите страны для отслеживания.",
            reply_markup=kb.get_region_selection_keyboard(
                all_countries, [], 
                finish_callback="finish_custom_selection",
                back_callback="cancel_artist_search"
            ),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(SubscriptionFlow.choosing_mobility_type, F.data.in_(['use_general_mobility', 'setup_custom_mobility']))
async def handle_mobility_type_choice(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    artist_name = data.get('current_artist')
    pending_subs = data.get('pending_favorites', [])
    if callback.data == 'use_general_mobility':
        regions = await db.get_general_mobility(callback.from_user.id)
        pending_subs.append({"item_name": artist_name, "category": "music", "regions": regions})
        await state.update_data(pending_favorites=pending_subs)
        await callback.answer(f"Артист {artist_name} добавлен с общими настройками.", show_alert=True)
        await show_add_more_or_finish(callback.message, state)
    else:
        await state.set_state(SubscriptionFlow.selecting_custom_regions)
        await state.update_data(selected_regions=[])
        all_countries = await db.get_countries()
        await callback.message.edit_text(
            f"Артист: {hbold(artist_name)}. Укажите страны для отслеживания.",
            # --- ИСПРАВЛЕНИЕ ЗДЕСЬ ---
            reply_markup=kb.get_region_selection_keyboard(all_countries, [], finish_callback="finish_custom_selection", back_callback=f"subscribe_to_artist:{artist_name}"),
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
        reply_markup=kb.get_region_selection_keyboard(all_countries, selected, finish_callback="finish_custom_selection", back_callback=f"subscribe_to_artist:{data.get('current_artist')}")
    )

@router.callback_query(SubscriptionFlow.selecting_custom_regions, F.data == "finish_custom_selection")
async def cq_finish_custom_selection(callback: CallbackQuery, state: FSMContext):
    """Завершение настройки кастомных регионов для подписки."""
    data = await state.get_data()
    regions = data.get("selected_regions", [])
    artist_name = data.get('current_artist')
    pending_subs = data.get('pending_favorites', [])

    if not regions:
        await callback.answer("Нужно выбрать хотя бы один регион!", show_alert=True)
        return
    
    pending_subs.append({"item_name": artist_name, "category": "music", "regions": regions})
    await state.update_data(pending_favorites=pending_subs)
    await callback.answer(f"Артист {artist_name} добавлен с кастомными настройками.", show_alert=True)

    await show_add_more_or_finish(callback.message, state)

async def show_add_more_or_finish(message: Message, state: FSMContext):
    """Показывает клавиатуру 'Добавить еще' / 'Готово'."""
    data = await state.get_data()
    pending_subs = data.get('pending_favorites', [])
    text = "Подписка добавлена в очередь на сохранение.\n"
    if pending_subs:
        text += "\n<b>Очередь на добавление:</b>\n"
        for sub in pending_subs:
            text += f"▫️ {hbold(sub['item_name'])}\n"
    
    await state.set_state(SubscriptionFlow.waiting_for_action)
    await message.edit_text(text, reply_markup=kb.get_add_more_or_finish_keyboard(), parse_mode="HTML")

@router.callback_query(SubscriptionFlow.selecting_general_regions, F.data == "finish_general_selection")
async def cq_finish_general_selection(callback: CallbackQuery, state: FSMContext):
    """Завершение настройки общей мобильности."""
    data = await state.get_data()
    regions = data.get("selected_regions", [])

    # if not regions: # Можно раскомментировать, если нужно
    #     await callback.answer("Нужно выбрать хотя бы один регион!", show_alert=True)
    #     return

    await db.set_general_mobility(callback.from_user.id, regions)
    await callback.answer("✅ Общие настройки мобильности сохранены!", show_alert=True)
    
    # Возвращаемся к выбору действия
    await state.set_state(SubscriptionFlow.waiting_for_action)
    await callback.message.edit_text(
        "Отлично! Теперь напиши исполнителя/событие или импортируй их.",
        reply_markup=kb.get_add_sub_action_keyboard()
    )


@router.callback_query(F.data.startswith("unsubscribe:"))
async def cq_unsubscribe_item(callback: CallbackQuery, state: FSMContext):
    """Удаление подписки из меню."""
    item_name = callback.data.split(":", 1)[1]
    await db.remove_subscription(callback.from_user.id, item_name)
    await callback.answer(f"❌ Вы отписались от {item_name}.")
    await show_favorites_list(callback)