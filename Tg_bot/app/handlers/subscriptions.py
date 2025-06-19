# app/handlers/subscriptions.py

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from ..database import requests as db
from ..database.models import async_session
from .. import keyboards as kb
from ..playlist_parser import parse_playlist_url

router = Router()


class SubscriptionFlow(StatesGroup):
    waiting_for_artist_name = State()
    choosing_mobility_option = State()
    choosing_template = State()
    selecting_custom_regions = State()
    creating_template_waiting_for_name = State()
    creating_template_selecting_regions = State()
    waiting_for_playlist_url = State()
    selecting_from_playlist = State()
    processing_imported_artist = State()


async def show_subscriptions(message: Message | CallbackQuery, force_new_message: bool = False):
    user_id = message.from_user.id
    subscriptions = await db.get_user_subscriptions(user_id)
    text = "Твои подписки:\nНажми на подписку, чтобы удалить ее." if subscriptions else "У тебя пока нет подписок."

    markup = kb.manage_subscriptions_keyboard(subscriptions)

    chat_id = message.chat.id if isinstance(message, Message) else message.message.chat.id

    if isinstance(message, CallbackQuery) and not force_new_message:
        try:
            # Пытаемся отредактировать сообщение, из которого пришел колбэк
            await message.message.edit_text(text, reply_markup=markup)
            return
        except Exception:
            # Если не вышло (например, текст тот же), просто отвечаем на колбэк и отправляем новое сообщение
            await message.answer()
            await message.bot.send_message(chat_id, text, reply_markup=markup)
    else:
        # Если это было сообщение, а не колбэк, просто отправляем новое
        await message.bot.send_message(chat_id, text, reply_markup=markup)


@router.message(F.text.in_(['⭐ Мои подписки', '⭐ My Subscriptions', '⭐ Мае падпіскі']))
async def menu_my_subscriptions(message: Message, state: FSMContext):
    await state.clear()

    async with async_session() as session:
        await db.get_or_create_user(session, message.from_user.id, message.from_user.username,
                                    message.from_user.language_code)

    onboarding_done = await db.check_mobility_onboarding_status(message.from_user.id)
    if not onboarding_done:
        await message.answer(
            "Похоже, ты здесь впервые! Давай настроим твою 'мобильность' - страны, куда ты готов поехать ради событий. "
            "Ты сможешь создать несколько шаблонов (например, 'Поездки по Европе' или 'Только соседи').",
            reply_markup=kb.get_mobility_onboarding_keyboard()
        )
    else:
        await show_subscriptions(message)


# --- ИСПРАВЛЕНИЕ: ДОБАВЛЕН НЕДОСТАЮЩИЙ ХЕНДЛЕР ---
@router.callback_query(F.data == "open_subscriptions")
async def cq_open_subscriptions(callback: CallbackQuery, state: FSMContext):
    """
    Этот хендлер ловит нажатие на кнопку 'Мои подписки' из меню профиля.
    """
    await state.clear()

    async with async_session() as session:
        await db.get_or_create_user(session, callback.from_user.id, callback.from_user.username,
                                    callback.from_user.language_code)

    onboarding_done = await db.check_mobility_onboarding_status(callback.from_user.id)
    # Удаляем предыдущее сообщение (меню профиля)
    await callback.message.delete()

    if not onboarding_done:
        await callback.message.answer(
            "Похоже, ты здесь впервые! Давай настроим твою 'мобильность'...",
            reply_markup=kb.get_mobility_onboarding_keyboard()
        )
    else:
        # Вызываем show_subscriptions с force_new_message=True, чтобы он гарантированно отправил новое сообщение
        await show_subscriptions(callback, force_new_message=True)

    await callback.answer()


@router.callback_query(F.data == "skip_mobility_setup")
async def cq_skip_mobility_setup(callback: CallbackQuery, state: FSMContext):
    await db.set_mobility_onboarding_completed(callback.from_user.id)
    await callback.message.delete()
    await show_subscriptions(callback, force_new_message=True)


@router.callback_query(F.data == "start_mobility_setup")
async def cq_start_mobility_setup(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.creating_template_waiting_for_name)
    await callback.message.edit_text(
        "Отлично! Давай создадим твой первый шаблон. Как его назовем? (например, 'Основной')")


@router.callback_query(F.data == "manage_mobility_templates")
async def cq_manage_templates(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.creating_template_waiting_for_name)
    await callback.message.edit_text("Давай создадим новый шаблон. Придумай для него название:")


@router.message(SubscriptionFlow.creating_template_waiting_for_name, F.text)
async def process_template_name(message: Message, state: FSMContext):
    await state.update_data(template_name=message.text)
    await state.set_state(SubscriptionFlow.creating_template_selecting_regions)
    await state.update_data(selected_regions=[])

    all_countries = await db.get_countries()
    await message.answer(
        f"Шаблон '{message.text}'. Теперь выбери страны, которые в него войдут:",
        reply_markup=kb.get_region_selection_keyboard(all_countries, [], for_template=True)
    )


@router.callback_query(SubscriptionFlow.creating_template_selecting_regions, F.data.startswith("toggle_region:"))
async def cq_toggle_region_for_template(callback: CallbackQuery, state: FSMContext):
    region_name = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_regions", [])
    if region_name in selected:
        selected.remove(region_name)
    else:
        selected.append(region_name)
    await state.update_data(selected_regions=selected)

    all_countries = await db.get_countries()
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_region_selection_keyboard(all_countries, selected, for_template=True)
    )


@router.callback_query(SubscriptionFlow.creating_template_selecting_regions, F.data == "finish_template_creation")
async def cq_finish_template_creation(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    template_name = data.get("template_name")
    regions = data.get("selected_regions", [])

    if not regions:
        await callback.answer("Нужно выбрать хотя бы один регион!", show_alert=True)
        return

    await db.create_mobility_template(callback.from_user.id, template_name, regions)
    await db.set_mobility_onboarding_completed(callback.from_user.id)
    await state.clear()

    await callback.message.edit_text(f"✅ Шаблон '{template_name}' успешно создан!")
    await show_subscriptions(callback, force_new_message=True)


@router.callback_query(F.data == "add_subscription_manual")
async def cq_add_subscription_manual(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.waiting_for_artist_name)
    await callback.message.edit_text("Введите имя артиста или название группы:")
    await callback.answer()


@router.message(SubscriptionFlow.waiting_for_artist_name, F.text)
async def process_artist_search(message: Message, state: FSMContext):
    found_artists = await db.find_artists_fuzzy(message.text)
    if not found_artists:
        await message.answer("По твоему запросу никого не найдено. Попробуй еще раз.",
                             reply_markup=kb.found_artists_keyboard([]))
    else:
        await message.answer("Вот кого я нашел. Выбери нужного артиста:",
                             reply_markup=kb.found_artists_keyboard(found_artists))


@router.callback_query(F.data.startswith("subscribe_to_artist:"))
async def cq_subscribe_to_artist(callback: CallbackQuery, state: FSMContext):
    artist_name = callback.data.split(":", 1)[1]
    await state.update_data(artist_to_subscribe=artist_name)
    await process_mobility_choice(callback, state)  # Передаем callback, а не message


async def process_mobility_choice(callback_or_message: Message | CallbackQuery, state: FSMContext):
    message = callback_or_message if isinstance(callback_or_message, Message) else callback_or_message.message
    user_id = callback_or_message.from_user.id

    templates = await db.get_user_mobility_templates(user_id)
    data = await state.get_data()
    artist_name = data.get("artist_to_subscribe")

    if not templates:
        await state.set_state(SubscriptionFlow.selecting_custom_regions)
        await state.update_data(selected_regions=[])
        all_countries = await db.get_countries()
        await message.edit_text(
            f"Артист: {artist_name}.\nУ тебя пока нет шаблонов мобильности. Давай настроим регионы для этой подписки вручную.",
            reply_markup=kb.get_region_selection_keyboard(all_countries, [])
        )
    else:
        await state.set_state(SubscriptionFlow.choosing_mobility_option)
        await message.edit_text(
            f"Артист: {artist_name}.\nКак настроим регионы для уведомлений?",
            reply_markup=kb.get_mobility_choice_keyboard(templates)
        )


@router.callback_query(SubscriptionFlow.choosing_mobility_option, F.data == "choose_template")
async def cq_choose_template(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.choosing_template)
    templates = await db.get_user_mobility_templates(callback.from_user.id)
    await callback.message.edit_text(
        "Выбери один из своих шаблонов:",
        reply_markup=kb.get_template_selection_keyboard(templates)
    )


@router.callback_query(SubscriptionFlow.choosing_mobility_option, F.data == "setup_custom_regions")
async def cq_setup_custom_regions(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.selecting_custom_regions)
    await state.update_data(selected_regions=[])
    all_countries = await db.get_countries()
    await callback.message.edit_text(
        "Выбери страны, для которых будет действовать эта подписка:",
        reply_markup=kb.get_region_selection_keyboard(all_countries, [])
    )


@router.callback_query(SubscriptionFlow.choosing_mobility_option, F.data == "back_to_mobility_choice")
async def cq_back_to_mobility_choice(callback: CallbackQuery, state: FSMContext):
    await process_mobility_choice(callback, state)


@router.callback_query(SubscriptionFlow.choosing_template, F.data.startswith("select_template:"))
async def cq_select_template_for_sub(callback: CallbackQuery, state: FSMContext):
    template_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    artist_name = data.get("artist_to_subscribe")

    await db.add_subscription(
        user_id=callback.from_user.id, item_name=artist_name,
        category='music', template_id=template_id
    )

    await callback.message.edit_text(f"✅ Подписка на '{artist_name}' с использованием шаблона оформлена!")
    await process_next_imported_artist(callback, state)


@router.callback_query(SubscriptionFlow.selecting_custom_regions, F.data.startswith("toggle_region:"))
async def cq_toggle_region_for_sub(callback: CallbackQuery, state: FSMContext):
    region_name = callback.data.split(":")[1]
    data = await state.get_data()
    selected = data.get("selected_regions", [])
    if region_name in selected:
        selected.remove(region_name)
    else:
        selected.append(region_name)
    await state.update_data(selected_regions=selected)

    all_countries = await db.get_countries()
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_region_selection_keyboard(all_countries, selected)
    )


@router.callback_query(SubscriptionFlow.selecting_custom_regions, F.data == "finish_custom_region_selection")
async def cq_finish_custom_regions(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    artist_name = data.get("artist_to_subscribe")
    regions = data.get("selected_regions", [])

    if not regions:
        await callback.answer("Нужно выбрать хотя бы один регион!", show_alert=True)
        return

    await db.add_subscription(
        user_id=callback.from_user.id, item_name=artist_name,
        category='music', custom_regions=regions
    )

    await callback.message.edit_text(f"✅ Подписка на '{artist_name}' с кастомными регионами оформлена!")
    await process_next_imported_artist(callback, state)


@router.callback_query(F.data == "import_playlist")
async def cq_import_playlist(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SubscriptionFlow.waiting_for_playlist_url)
    await callback.message.edit_text(
        "Отправь мне ссылку на публичный плейлист (YouTube Music, Spotify, Яндекс.Музыка, VK). "
        "Я извлеку оттуда исполнителей, и ты сможешь подписаться на них."
    )
    await callback.answer()


@router.message(SubscriptionFlow.waiting_for_playlist_url, F.text)
async def process_playlist_url(message: Message, state: FSMContext):
    if not message.text.startswith('http'):
        await message.reply("Это не похоже на ссылку. Попробуй еще раз.")
        return

    msg = await message.reply("Принял ссылку. Начинаю обработку...")

    found_artists_lower = await parse_playlist_url(message.text)
    if found_artists_lower is None or not found_artists_lower:
        await msg.edit_text(
            "Не удалось обработать ссылку или найти артистов. Убедись, что плейлист публичный и ссылка верна.")
        await state.clear()
        return

    correctly_cased_artists = await db.get_artists_by_lowercase_names(found_artists_lower)
    sorted_artists = sorted(list(set(correctly_cased_artists)))

    await state.set_state(SubscriptionFlow.selecting_from_playlist)
    await state.update_data(found_artists=sorted_artists, selected_artists_for_import=set())
    await msg.edit_text(
        "Я нашел этих артистов в плейлисте. Выбери, на кого хочешь подписаться:",
        reply_markup=kb.get_paginated_artists_keyboard(sorted_artists, set())
    )


@router.callback_query(SubscriptionFlow.selecting_from_playlist, F.data.startswith("toggle_artist_subscribe:"))
async def cq_toggle_artist_subscribe(callback: CallbackQuery, state: FSMContext):
    artist_name = callback.data.split(":", 1)[1]
    data = await state.get_data()
    found = data.get("found_artists", [])
    selected = data.get("selected_artists_for_import", set())
    if artist_name in selected:
        selected.remove(artist_name)
    else:
        selected.add(artist_name)
    await state.update_data(selected_artists_for_import=selected)

    current_page = 0
    if found:
        try:
            current_page = found.index(artist_name) // 5
        except ValueError:
            pass

    await callback.message.edit_reply_markup(
        reply_markup=kb.get_paginated_artists_keyboard(found, selected, current_page)
    )


@router.callback_query(SubscriptionFlow.selecting_from_playlist, F.data.startswith("paginate_artists:"))
async def cq_paginate_artists(callback: CallbackQuery, state: FSMContext):
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    await callback.message.edit_reply_markup(
        reply_markup=kb.get_paginated_artists_keyboard(
            data.get("found_artists", []),
            data.get("selected_artists_for_import", set()),
            page
        )
    )


@router.callback_query(SubscriptionFlow.selecting_from_playlist, F.data == "finish_artist_selection")
async def cq_finish_artist_selection(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_artists = list(data.get("selected_artists_for_import", set()))

    if not selected_artists:
        await callback.answer("Ты никого не выбрал.", show_alert=True)
        return

    await state.update_data(imported_artists_queue=selected_artists)
    await callback.message.delete()
    await process_next_imported_artist(callback, state)


async def process_next_imported_artist(callback_or_message: Message | CallbackQuery, state: FSMContext):
    data = await state.get_data()
    artist_queue = data.get("imported_artists_queue", [])

    if not artist_queue:
        await state.clear()
        message = callback_or_message if isinstance(callback_or_message, Message) else callback_or_message.message
        await message.answer("✅ Все выбранные подписки успешно оформлены!")
        await show_subscriptions(callback_or_message, force_new_message=True)
        return

    current_artist = artist_queue.pop(0)
    await state.update_data(imported_artists_queue=artist_queue)
    await state.update_data(artist_to_subscribe=current_artist)

    await process_mobility_choice(callback_or_message, state)


@router.callback_query(F.data.startswith("unsubscribe:"))
async def cq_unsubscribe_item(callback: CallbackQuery):
    item_name = callback.data.split(":", 1)[1]
    await db.remove_subscription(callback.from_user.id, item_name)
    await callback.answer(f"❌ Ты отписался от {item_name}.")
    await show_subscriptions(callback)


@router.callback_query(F.data == "cancel_subscription")
async def cq_cancel_subscription(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_subscriptions(callback)